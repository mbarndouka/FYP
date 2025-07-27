from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from typing import Optional, List
import json

from app.database.config import get_db
from app.auth.dependencies import get_current_user
from app.models.user import User
from app.services.data_integration_service import data_integration_service
from app.schemas.data_integration import (
    FileUploadRequest, FileUpdateRequest, FileShareRequest, MetadataUpdateRequest,
    DataFileResponse, FileUploadResponse, FileUploadStatusResponse,
    FileListResponse, ProcessingSummary, FileTypeEnum
)

router = APIRouter(prefix="/api/data-integration", tags=["Data Integration"])


@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    file_type: FileTypeEnum = Form(...),
    description: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),  # JSON string of tags
    location: Optional[str] = Form(None),
    acquisition_date: Optional[str] = Form(None),  # ISO format string
    is_public: bool = Form(False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload a new data file to the system.
    
    This endpoint implements step 1-6 of the data upload flow:
    1. Field Team selects and uploads files
    2. System validates file format and size
    3. System initiates upload to centralized repository
    4. System processes data and stores it
    5. System confirms successful upload
    6. System displays upload summary
    """
    try:
        # Parse tags if provided
        tags_list = None
        if tags:
            try:
                tags_list = json.loads(tags)
            except json.JSONDecodeError:
                tags_list = [tag.strip() for tag in tags.split(",")]
        
        # Parse acquisition date if provided
        acquisition_datetime = None
        if acquisition_date:
            from datetime import datetime
            acquisition_datetime = datetime.fromisoformat(acquisition_date.replace('Z', '+00:00'))
        
        # Create upload request
        upload_request = FileUploadRequest(
            file_type=file_type,
            description=description,
            tags=tags_list,
            location=location,
            acquisition_date=acquisition_datetime,
            is_public=is_public
        )
        
        # Get client IP and user agent for logging
        client_ip = request.client.host
        user_agent = request.headers.get("user-agent")
        
        # Upload file
        result = await data_integration_service.initiate_file_upload(
            file=file,
            upload_request=upload_request,
            user_id=current_user.id,
            db=db
        )
        
        # Log upload action with client info (this is handled in the service)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upload failed: {str(e)}"
        )


@router.get("/upload/{file_id}/status", response_model=FileUploadStatusResponse)
async def get_upload_status(
    file_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get the upload and processing status of a file.
    
    This endpoint provides real-time status updates during the upload and processing phases.
    """
    return data_integration_service.get_file_upload_status(file_id, db)


@router.get("/files", response_model=FileListResponse)
async def get_files(
    file_type: Optional[str] = None,
    status: Optional[str] = None,
    is_public: Optional[bool] = None,
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get list of files with filtering and pagination.
    
    Returns files that the user has access to (owned, public, or shared).
    """
    if page_size > 100:
        page_size = 100  # Limit page size
    
    result = data_integration_service.get_files(
        db=db,
        user_id=current_user.id,
        file_type=file_type,
        status=status,
        is_public=is_public,
        search=search,
        page=page,
        page_size=page_size
    )
    
    return FileListResponse(**result)


@router.get("/files/{file_id}", response_model=DataFileResponse)
async def get_file_details(
    file_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get detailed information about a specific file."""
    # This will be implemented by checking access and returning file details
    db_file = data_integration_service._check_file_access(db, file_id, current_user.id, "read")
    
    # Convert to response format (similar to the get_files method)
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


@router.get("/files/{file_id}/download")
async def download_file(
    file_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Download a file.
    
    Returns a redirect to the signed URL for file download.
    """
    download_url = data_integration_service.get_file_download_url(
        file_id=file_id,
        user_id=current_user.id,
        db=db
    )
    
    return RedirectResponse(url=download_url)


@router.put("/files/{file_id}", response_model=DataFileResponse)
async def update_file(
    file_id: str,
    update_request: FileUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update file metadata."""
    return data_integration_service.update_file(
        file_id=file_id,
        update_request=update_request,
        user_id=current_user.id,
        db=db
    )


@router.delete("/files/{file_id}")
async def delete_file(
    file_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a file (owner only)."""
    return data_integration_service.delete_file(
        file_id=file_id,
        user_id=current_user.id,
        db=db
    )


@router.post("/files/{file_id}/share")
async def share_file(
    file_id: str,
    share_request: FileShareRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Share a file with another user."""
    # This would be implemented in the service
    # For now, return a placeholder
    return {"message": "File sharing functionality to be implemented"}


@router.get("/summary", response_model=ProcessingSummary)
async def get_processing_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get processing summary for the current user.
    
    Provides an overview of upload statistics and recent activity.
    """
    return data_integration_service.get_processing_summary(
        user_id=current_user.id,
        db=db
    )


@router.get("/file-types")
async def get_supported_file_types():
    """Get list of supported file types and their allowed MIME types."""
    return {
        "file_types": [
            {
                "key": "seismic_data",
                "label": "Seismic Data",
                "description": "Seismic survey data files",
                "allowed_mime_types": ["application/octet-stream", "text/plain", "application/x-segy"]
            },
            {
                "key": "well_log",
                "label": "Well Log",
                "description": "Well logging data",
                "allowed_mime_types": ["text/csv", "application/json", "text/plain"]
            },
            {
                "key": "core_sample",
                "label": "Core Sample",
                "description": "Core sample images and data",
                "allowed_mime_types": ["image/jpeg", "image/png", "image/tiff", "application/pdf"]
            },
            {
                "key": "production_data",
                "label": "Production Data",
                "description": "Oil and gas production data",
                "allowed_mime_types": ["text/csv", "application/json", "application/vnd.ms-excel"]
            },
            {
                "key": "reservoir_model",
                "label": "Reservoir Model",
                "description": "Reservoir simulation models",
                "allowed_mime_types": ["application/octet-stream", "text/plain"]
            },
            {
                "key": "geological_map",
                "label": "Geological Map",
                "description": "Geological survey maps",
                "allowed_mime_types": ["image/jpeg", "image/png", "image/tiff", "application/pdf"]
            },
            {
                "key": "report",
                "label": "Report",
                "description": "Technical reports and documents",
                "allowed_mime_types": ["application/pdf", "application/msword", "text/plain"]
            },
            {
                "key": "image",
                "label": "Image",
                "description": "General image files",
                "allowed_mime_types": ["image/jpeg", "image/png", "image/tiff", "image/bmp"]
            },
            {
                "key": "document",
                "label": "Document",
                "description": "General document files",
                "allowed_mime_types": ["application/pdf", "application/msword", "text/plain"]
            },
            {
                "key": "other",
                "label": "Other",
                "description": "Other file types",
                "allowed_mime_types": ["*/*"]
            }
        ]
    }


@router.post("/validate-file")
async def validate_file(
    file: UploadFile = File(...),
    file_type: FileTypeEnum = Form(...)
):
    """
    Validate a file before upload.
    
    This endpoint can be used to pre-validate files on the client side
    before initiating the actual upload process.
    """
    validation_result = await data_integration_service.validate_file(file, file_type.value)
    
    return {
        "is_valid": validation_result.is_valid,
        "file_size": validation_result.file_size,
        "mime_type": validation_result.mime_type,
        "errors": validation_result.errors,
        "warnings": validation_result.warnings
    }
