import os
import hashlib
import json
import mimetypes
from typing import List, Optional, Dict, Any, BinaryIO
from datetime import datetime, timedelta
from uuid import uuid4
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func
from fastapi import UploadFile, HTTPException, status
from supabase import create_client, Client

from app.models.data_integration import (
    DataFile, FileMetadata, FileAccessLog, FileShare, DataIntegrationJob,
    FileType, FileStatus, ProcessingStatus
)
from app.schemas.data_integration import (
    FileUploadRequest, FileUpdateRequest, FileShareRequest, MetadataUpdateRequest,
    DataFileResponse, FileValidationResult, ProcessingSummary,
    FileUploadResponse, FileUploadStatusResponse
)


class DataIntegrationService:
    def __init__(self):
        # Initialize Supabase client
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_ANON_KEY")
        
        if not supabase_url or not supabase_key:
            raise ValueError("Supabase URL and ANON_KEY must be set in environment variables")
        
        self.supabase: Client = create_client(supabase_url, supabase_key)
        self.storage_bucket = os.getenv("SUPABASE_STORAGE_BUCKET", "data-files")
        
        # File validation settings
        self.max_file_size = int(os.getenv("MAX_FILE_SIZE", "1073741824"))  # 1GB default
        self.allowed_mime_types = {
            "seismic_data": ["application/octet-stream", "text/plain", "application/x-segy"],
            "well_log": ["text/csv", "application/json", "text/plain"],
            "core_sample": ["image/jpeg", "image/png", "image/tiff", "application/pdf"],
            "production_data": ["text/csv", "application/json", "application/vnd.ms-excel"],
            "reservoir_model": ["application/octet-stream", "text/plain"],
            "geological_map": ["image/jpeg", "image/png", "image/tiff", "application/pdf"],
            "report": ["application/pdf", "application/msword", "text/plain"],
            "image": ["image/jpeg", "image/png", "image/tiff", "image/bmp"],
            "document": ["application/pdf", "application/msword", "text/plain"],
            "other": ["*/*"]
        }

    async def validate_file(self, file: UploadFile, file_type: str) -> FileValidationResult:
        """Validate uploaded file against predefined criteria"""
        errors = []
        warnings = []
        
        # Check file size
        file.file.seek(0, 2)  # Seek to end
        file_size = file.file.tell()
        file.file.seek(0)  # Reset to beginning
        
        if file_size > self.max_file_size:
            errors.append(f"File size ({file_size} bytes) exceeds maximum allowed size ({self.max_file_size} bytes)")
        
        if file_size == 0:
            errors.append("File is empty")
        
        # Check MIME type
        mime_type, _ = mimetypes.guess_type(file.filename)
        if not mime_type:
            mime_type = file.content_type or "application/octet-stream"
        
        allowed_types = self.allowed_mime_types.get(file_type, ["*/*"])
        if "*/*" not in allowed_types and mime_type not in allowed_types:
            errors.append(f"File type '{mime_type}' not allowed for category '{file_type}'. Allowed types: {allowed_types}")
        
        # Check filename
        if not file.filename:
            errors.append("Filename is required")
        elif len(file.filename) > 255:
            errors.append("Filename too long (max 255 characters)")
        
        # Additional validation based on file type
        if file_type == "seismic_data" and file_size < 1000:
            warnings.append("Seismic data file seems unusually small")
        
        return FileValidationResult(
            is_valid=len(errors) == 0,
            file_size=file_size,
            mime_type=mime_type,
            errors=errors,
            warnings=warnings
        )

    def _calculate_file_hash(self, file_content: bytes) -> str:
        """Calculate SHA-256 hash of file content"""
        return hashlib.sha256(file_content).hexdigest()

    async def initiate_file_upload(
        self, 
        file: UploadFile, 
        upload_request: FileUploadRequest,
        user_id: str,
        db: Session
    ) -> FileUploadResponse:
        """Initiate file upload process"""
        
        # Validate file
        validation_result = await self.validate_file(file, upload_request.file_type.value)
        if not validation_result.is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File validation failed: {', '.join(validation_result.errors)}"
            )
        
        # Generate unique file ID and path
        file_id = str(uuid4())
        file_extension = os.path.splitext(file.filename)[1] if file.filename else ""
        storage_path = f"{upload_request.file_type.value}/{datetime.now().strftime('%Y/%m/%d')}/{file_id}{file_extension}"
        
        # Read file content and calculate hash
        file_content = await file.read()
        file_hash = self._calculate_file_hash(file_content)
        await file.seek(0)  # Reset file pointer
        
        # Check for duplicate files
        existing_file = db.query(DataFile).filter(DataFile.file_hash == file_hash).first()
        if existing_file:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"File already exists with ID: {existing_file.id}"
            )
        
        # Create database record
        db_file = DataFile(
            id=file_id,
            original_filename=file.filename,
            file_path=storage_path,
            file_size=validation_result.file_size,
            file_type=FileType(upload_request.file_type.value),
            mime_type=validation_result.mime_type,
            file_hash=file_hash,
            uploaded_by=user_id,
            status=FileStatus.UPLOADING,
            description=upload_request.description,
            tags=json.dumps(upload_request.tags) if upload_request.tags else None,
            location=upload_request.location,
            acquisition_date=upload_request.acquisition_date,
            is_public=upload_request.is_public
        )
        
        db.add(db_file)
        db.commit()
        db.refresh(db_file)
        
        try:
            # Upload to Supabase Storage
            upload_response = self.supabase.storage.from_(self.storage_bucket).upload(
                path=storage_path,
                file=file_content,
                file_options={"content-type": validation_result.mime_type}
            )
            
            if upload_response.get("error"):
                raise Exception(f"Supabase upload failed: {upload_response['error']}")
            
            # Update file status to completed
            db_file.status = FileStatus.COMPLETED
            db.commit()
            
            # Log upload action
            self._log_file_access(db, file_id, user_id, "upload")
            
            # Start background processing
            await self._start_file_processing(db, file_id)
            
            return FileUploadResponse(
                message="File uploaded successfully",
                file_id=file_id,
                upload_url=f"/{self.storage_bucket}/{storage_path}",
                fields={"file_id": file_id, "status": "completed"}
            )
            
        except Exception as e:
            # Update file status to failed
            db_file.status = FileStatus.FAILED
            db_file.processing_error = str(e)
            db.commit()
            
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"File upload failed: {str(e)}"
            )

    async def _start_file_processing(self, db: Session, file_id: str):
        """Start background file processing jobs"""
        
        # Create metadata extraction job
        metadata_job = DataIntegrationJob(
            id=str(uuid4()),
            file_id=file_id,
            job_type="metadata_extraction",
            status=ProcessingStatus.PENDING
        )
        
        # Create format validation job
        validation_job = DataIntegrationJob(
            id=str(uuid4()),
            file_id=file_id,
            job_type="format_validation",
            status=ProcessingStatus.PENDING
        )
        
        db.add_all([metadata_job, validation_job])
        db.commit()
        
        # Update file processing status
        db_file = db.query(DataFile).filter(DataFile.id == file_id).first()
        if db_file:
            db_file.processing_status = ProcessingStatus.PENDING
            db_file.processing_started_at = datetime.utcnow()
            db.commit()

    def get_file_upload_status(self, file_id: str, db: Session) -> FileUploadStatusResponse:
        """Get upload and processing status of a file"""
        
        db_file = db.query(DataFile).filter(DataFile.id == file_id).first()
        if not db_file:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )
        
        # Calculate progress based on processing jobs
        jobs = db.query(DataIntegrationJob).filter(DataIntegrationJob.file_id == file_id).all()
        
        if not jobs:
            progress = 0.0
        else:
            completed_jobs = sum(1 for job in jobs if job.status == ProcessingStatus.COMPLETED)
            progress = (completed_jobs / len(jobs)) * 100
        
        message = None
        if db_file.status == FileStatus.FAILED:
            message = db_file.processing_error
        elif db_file.processing_status == ProcessingStatus.IN_PROGRESS:
            message = "Processing file..."
        elif db_file.processing_status == ProcessingStatus.COMPLETED:
            message = "Processing completed successfully"
        
        return FileUploadStatusResponse(
            file_id=file_id,
            status=db_file.status,
            processing_status=db_file.processing_status,
            progress=progress,
            message=message
        )

    def get_files(
        self, 
        db: Session, 
        user_id: str,
        file_type: Optional[str] = None,
        status: Optional[str] = None,
        is_public: Optional[bool] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """Get list of files with filtering and pagination"""
        
        query = db.query(DataFile)
        
        # Filter by user access (own files or public files or shared files)
        query = query.filter(
            or_(
                DataFile.uploaded_by == user_id,
                DataFile.is_public == True,
                DataFile.id.in_(
                    db.query(FileShare.file_id).filter(
                        and_(FileShare.shared_with == user_id, FileShare.is_active == True)
                    )
                )
            )
        )
        
        # Apply filters
        if file_type:
            query = query.filter(DataFile.file_type == FileType(file_type))
        
        if status:
            query = query.filter(DataFile.status == FileStatus(status))
        
        if is_public is not None:
            query = query.filter(DataFile.is_public == is_public)
        
        if search:
            search_filter = or_(
                DataFile.original_filename.ilike(f"%{search}%"),
                DataFile.description.ilike(f"%{search}%"),
                DataFile.tags.ilike(f"%{search}%")
            )
            query = query.filter(search_filter)
        
        # Count total records
        total = query.count()
        
        # Apply pagination
        offset = (page - 1) * page_size
        files = query.order_by(desc(DataFile.created_at)).offset(offset).limit(page_size).all()
        
        # Convert to response format
        file_responses = []
        for file in files:
            tags = json.loads(file.tags) if file.tags else []
            file_response = DataFileResponse(
                id=file.id,
                original_filename=file.original_filename,
                file_path=file.file_path,
                file_size=file.file_size,
                file_type=file.file_type,
                mime_type=file.mime_type,
                file_hash=file.file_hash,
                uploaded_by=file.uploaded_by,
                upload_timestamp=file.upload_timestamp,
                status=file.status,
                processing_status=file.processing_status,
                processing_started_at=file.processing_started_at,
                processing_completed_at=file.processing_completed_at,
                processing_error=file.processing_error,
                description=file.description,
                tags=tags,
                location=file.location,
                acquisition_date=file.acquisition_date,
                is_public=file.is_public,
                is_archived=file.is_archived,
                created_at=file.created_at,
                updated_at=file.updated_at
            )
            file_responses.append(file_response)
        
        return {
            "files": file_responses,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size
        }

    def get_file_download_url(self, file_id: str, user_id: str, db: Session) -> str:
        """Generate signed URL for file download"""
        
        # Check file access permissions
        db_file = self._check_file_access(db, file_id, user_id, "read")
        
        try:
            # Generate signed URL from Supabase Storage
            signed_url = self.supabase.storage.from_(self.storage_bucket).create_signed_url(
                path=db_file.file_path,
                expires_in=3600  # 1 hour
            )
            
            if signed_url.get("error"):
                raise Exception(f"Failed to generate download URL: {signed_url['error']}")
            
            # Log download action
            self._log_file_access(db, file_id, user_id, "download")
            
            return signed_url["signedURL"]
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate download URL: {str(e)}"
            )

    def _check_file_access(self, db: Session, file_id: str, user_id: str, permission: str = "read") -> DataFile:
        """Check if user has access to file"""
        
        db_file = db.query(DataFile).filter(DataFile.id == file_id).first()
        if not db_file:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )
        
        # Check access permissions
        has_access = (
            db_file.uploaded_by == user_id or  # Owner
            db_file.is_public or  # Public file
            db.query(FileShare).filter(
                and_(
                    FileShare.file_id == file_id,
                    FileShare.shared_with == user_id,
                    FileShare.is_active == True
                )
            ).first() is not None  # Shared file
        )
        
        if not has_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        return db_file

    def _log_file_access(self, db: Session, file_id: str, user_id: str, action: str, 
                        ip_address: str = None, user_agent: str = None):
        """Log file access activity"""
        
        access_log = FileAccessLog(
            id=str(uuid4()),
            file_id=file_id,
            user_id=user_id,
            action=action,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        db.add(access_log)
        db.commit()

    def update_file(self, file_id: str, update_request: FileUpdateRequest, 
                   user_id: str, db: Session) -> DataFileResponse:
        """Update file metadata"""
        
        db_file = self._check_file_access(db, file_id, user_id, "write")
        
        # Update fields
        if update_request.description is not None:
            db_file.description = update_request.description
        
        if update_request.tags is not None:
            db_file.tags = json.dumps(update_request.tags)
        
        if update_request.location is not None:
            db_file.location = update_request.location
        
        if update_request.acquisition_date is not None:
            db_file.acquisition_date = update_request.acquisition_date
        
        if update_request.is_public is not None:
            db_file.is_public = update_request.is_public
        
        if update_request.is_archived is not None:
            db_file.is_archived = update_request.is_archived
        
        db.commit()
        db.refresh(db_file)
        
        # Log update action
        self._log_file_access(db, file_id, user_id, "update")
        
        # Convert to response
        tags = json.loads(db_file.tags) if db_file.tags else []
        return DataFileResponse(
            id=db_file.id,
            original_filename=db_file.original_filename,
            file_path=db_file.file_path,
            file_size=db_file.file_size,
            file_type=db_file.file_type,
            mime_type=db_file.mime_type,
            file_hash=db_file.file_hash,
            uploaded_by=db_file.uploaded_by,
            upload_timestamp=db_file.upload_timestamp,
            status=db_file.status,
            processing_status=db_file.processing_status,
            processing_started_at=db_file.processing_started_at,
            processing_completed_at=db_file.processing_completed_at,
            processing_error=db_file.processing_error,
            description=db_file.description,
            tags=tags,
            location=db_file.location,
            acquisition_date=db_file.acquisition_date,
            is_public=db_file.is_public,
            is_archived=db_file.is_archived,
            created_at=db_file.created_at,
            updated_at=db_file.updated_at
        )

    def delete_file(self, file_id: str, user_id: str, db: Session) -> Dict[str, str]:
        """Delete a file"""
        
        db_file = self._check_file_access(db, file_id, user_id, "admin")
        
        # Only owner can delete
        if db_file.uploaded_by != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only file owner can delete files"
            )
        
        try:
            # Delete from Supabase Storage
            delete_response = self.supabase.storage.from_(self.storage_bucket).remove([db_file.file_path])
            
            if delete_response.get("error"):
                raise Exception(f"Failed to delete from storage: {delete_response['error']}")
            
            # Delete related records from database
            db.query(FileMetadata).filter(FileMetadata.file_id == file_id).delete()
            db.query(FileAccessLog).filter(FileAccessLog.file_id == file_id).delete()
            db.query(FileShare).filter(FileShare.file_id == file_id).delete()
            db.query(DataIntegrationJob).filter(DataIntegrationJob.file_id == file_id).delete()
            db.query(DataFile).filter(DataFile.id == file_id).delete()
            
            db.commit()
            
            return {"message": "File deleted successfully"}
            
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete file: {str(e)}"
            )

    def get_processing_summary(self, user_id: str, db: Session) -> ProcessingSummary:
        """Get processing summary for user's files"""
        
        # Get user's files
        user_files = db.query(DataFile).filter(DataFile.uploaded_by == user_id)
        
        total_files = user_files.count()
        successful_uploads = user_files.filter(DataFile.status == FileStatus.COMPLETED).count()
        failed_uploads = user_files.filter(DataFile.status == FileStatus.FAILED).count()
        files_in_processing = user_files.filter(
            DataFile.processing_status.in_([ProcessingStatus.PENDING, ProcessingStatus.IN_PROGRESS])
        ).count()
        
        # Get recent activity
        recent_logs = db.query(FileAccessLog).filter(
            FileAccessLog.user_id == user_id
        ).order_by(desc(FileAccessLog.timestamp)).limit(10).all()
        
        return ProcessingSummary(
            total_files=total_files,
            successful_uploads=successful_uploads,
            failed_uploads=failed_uploads,
            files_in_processing=files_in_processing,
            recent_activity=[
                {
                    "id": log.id,
                    "file_id": log.file_id,
                    "user_id": log.user_id,
                    "action": log.action,
                    "ip_address": log.ip_address,
                    "user_agent": log.user_agent,
                    "timestamp": log.timestamp
                } for log in recent_logs
            ]
        )


# Create singleton instance
data_integration_service = DataIntegrationService()
