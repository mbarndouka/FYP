"""
Background Processing Script for Data Integration

This script handles background processing jobs for uploaded files,
including metadata extraction, format validation, and other processing tasks.
"""

import asyncio
import os
import sys
import json
import mimetypes
from datetime import datetime
from typing import Dict, Any
import hashlib
from pathlib import Path

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy.orm import Session
from app.database.config import SessionLocal
from app.models.data_integration import DataFile, FileMetadata, DataIntegrationJob, ProcessingStatus
from supabase import create_client, Client


class FileProcessor:
    def __init__(self):
        # Initialize Supabase client
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_ANON_KEY")
        
        if not supabase_url or supabase_key:
            raise ValueError("Supabase URL and ANON_KEY must be set in environment variables")
        
        self.supabase: Client = create_client(supabase_url, supabase_key)
        self.storage_bucket = os.getenv("SUPABASE_STORAGE_BUCKET", "data-files")

    async def process_pending_jobs(self):
        """Process all pending jobs in the queue"""
        
        db = SessionLocal()
        try:
            # Get all pending jobs
            pending_jobs = db.query(DataIntegrationJob).filter(
                DataIntegrationJob.status == ProcessingStatus.PENDING
            ).all()
            
            print(f"Found {len(pending_jobs)} pending jobs to process")
            
            for job in pending_jobs:
                try:
                    await self.process_job(db, job)
                except Exception as e:
                    print(f"Error processing job {job.id}: {str(e)}")
                    job.status = ProcessingStatus.FAILED
                    job.error_message = str(e)
                    job.completed_at = datetime.utcnow()
                    db.commit()
        
        finally:
            db.close()

    async def process_job(self, db: Session, job: DataIntegrationJob):
        """Process a single job"""
        
        print(f"Processing job {job.id} of type {job.job_type} for file {job.file_id}")
        
        # Update job status to in_progress
        job.status = ProcessingStatus.IN_PROGRESS
        job.started_at = datetime.utcnow()
        db.commit()
        
        # Get the associated file
        db_file = db.query(DataFile).filter(DataFile.id == job.file_id).first()
        if not db_file:
            raise Exception(f"File {job.file_id} not found")
        
        # Process based on job type
        if job.job_type == "metadata_extraction":
            await self.extract_metadata(db, job, db_file)
        elif job.job_type == "format_validation":
            await self.validate_format(db, job, db_file)
        else:
            raise Exception(f"Unknown job type: {job.job_type}")
        
        # Update job status to completed
        job.status = ProcessingStatus.COMPLETED
        job.completed_at = datetime.utcnow()
        db.commit()
        
        print(f"Completed job {job.id}")

    async def extract_metadata(self, db: Session, job: DataIntegrationJob, db_file: DataFile):
        """Extract metadata from the uploaded file"""
        
        try:
            # Download file content from Supabase Storage (for small files)
            # For large files, you might want to stream or process in chunks
            file_response = self.supabase.storage.from_(self.storage_bucket).download(db_file.file_path)
            
            if not file_response:
                raise Exception("Failed to download file for metadata extraction")
            
            # Initialize metadata dictionary
            metadata = {}
            
            # Extract basic metadata based on file type
            if db_file.file_type.value == "image":
                metadata.update(await self.extract_image_metadata(file_response))
            elif db_file.file_type.value == "seismic_data":
                metadata.update(await self.extract_seismic_metadata(file_response))
            elif db_file.file_type.value == "well_log":
                metadata.update(await self.extract_well_log_metadata(file_response))
            # Add more file type specific metadata extraction here
            
            # Create or update file metadata record
            existing_metadata = db.query(FileMetadata).filter(
                FileMetadata.file_id == db_file.id
            ).first()
            
            if existing_metadata:
                # Update existing metadata
                existing_metadata.custom_metadata = json.dumps(metadata)
                existing_metadata.updated_at = datetime.utcnow()
            else:
                # Create new metadata record
                file_metadata = FileMetadata(
                    id=f"meta_{db_file.id}",
                    file_id=db_file.id,
                    custom_metadata=json.dumps(metadata)
                )
                db.add(file_metadata)
            
            # Store job result
            job.result = json.dumps({
                "extracted_fields": list(metadata.keys()),
                "metadata_size": len(json.dumps(metadata)),
                "success": True
            })
            
            db.commit()
            
        except Exception as e:
            raise Exception(f"Metadata extraction failed: {str(e)}")

    async def extract_image_metadata(self, file_content: bytes) -> Dict[str, Any]:
        """Extract metadata from image files"""
        
        metadata = {}
        
        try:
            # Try to use PIL to extract image metadata
            from PIL import Image
            import io
            
            with Image.open(io.BytesIO(file_content)) as img:
                metadata["width"] = img.width
                metadata["height"] = img.height
                metadata["format"] = img.format
                metadata["mode"] = img.mode
                
                # Extract EXIF data if available
                if hasattr(img, '_getexif') and img._getexif():
                    exif_data = img._getexif()
                    metadata["exif"] = {str(k): str(v) for k, v in exif_data.items()}
                
        except Exception as e:
            metadata["extraction_error"] = str(e)
        
        return metadata

    async def extract_seismic_metadata(self, file_content: bytes) -> Dict[str, Any]:
        """Extract metadata from seismic data files"""
        
        metadata = {}
        
        try:
            # Basic file analysis
            metadata["file_size"] = len(file_content)
            metadata["file_hash"] = hashlib.sha256(file_content).hexdigest()
            
            # Try to detect if it's a SEGY file by checking header
            if len(file_content) >= 3200:  # SEGY files have at least 3200 byte header
                # Check for SEGY format indicators
                header = file_content[:3200]
                if b'SEGY' in header or b'SEG-Y' in header:
                    metadata["format"] = "SEGY"
                    metadata["header_size"] = 3200
                
            # Add more seismic-specific metadata extraction here
            
        except Exception as e:
            metadata["extraction_error"] = str(e)
        
        return metadata

    async def extract_well_log_metadata(self, file_content: bytes) -> Dict[str, Any]:
        """Extract metadata from well log files"""
        
        metadata = {}
        
        try:
            # Try to decode as text and analyze
            text_content = file_content.decode('utf-8', errors='ignore')
            
            metadata["line_count"] = text_content.count('\n')
            metadata["character_count"] = len(text_content)
            
            # Try to detect CSV structure
            if ',' in text_content:
                lines = text_content.split('\n')
                if lines:
                    first_line = lines[0]
                    metadata["csv_columns"] = len(first_line.split(','))
                    metadata["headers"] = first_line.split(',')[:10]  # First 10 headers
            
            # Try to detect JSON structure
            try:
                json_data = json.loads(text_content)
                if isinstance(json_data, dict):
                    metadata["json_keys"] = list(json_data.keys())[:20]  # First 20 keys
                elif isinstance(json_data, list) and json_data:
                    metadata["json_array_length"] = len(json_data)
                    if isinstance(json_data[0], dict):
                        metadata["json_object_keys"] = list(json_data[0].keys())[:20]
            except json.JSONDecodeError:
                pass
            
        except Exception as e:
            metadata["extraction_error"] = str(e)
        
        return metadata

    async def validate_format(self, db: Session, job: DataIntegrationJob, db_file: DataFile):
        """Validate file format and integrity"""
        
        try:
            # Download file for validation
            file_response = self.supabase.storage.from_(self.storage_bucket).download(db_file.file_path)
            
            if not file_response:
                raise Exception("Failed to download file for format validation")
            
            validation_results = {}
            
            # Verify file hash
            calculated_hash = hashlib.sha256(file_response).hexdigest()
            validation_results["hash_verified"] = calculated_hash == db_file.file_hash
            
            # Verify MIME type
            guessed_mime, _ = mimetypes.guess_type(db_file.original_filename)
            validation_results["mime_type_match"] = guessed_mime == db_file.mime_type
            
            # File-specific validation
            if db_file.file_type.value == "image":
                validation_results.update(await self.validate_image_format(file_response))
            elif db_file.file_type.value == "seismic_data":
                validation_results.update(await self.validate_seismic_format(file_response))
            
            # Overall validation status
            validation_results["is_valid"] = all([
                validation_results.get("hash_verified", False),
                validation_results.get("format_valid", True)
            ])
            
            # Store job result
            job.result = json.dumps(validation_results)
            
            # Update file status based on validation
            if not validation_results["is_valid"]:
                db_file.status = "quarantined"
                db_file.processing_error = "File failed format validation"
            
            db.commit()
            
        except Exception as e:
            raise Exception(f"Format validation failed: {str(e)}")

    async def validate_image_format(self, file_content: bytes) -> Dict[str, Any]:
        """Validate image file format"""
        
        validation = {"format_valid": False}
        
        try:
            from PIL import Image
            import io
            
            with Image.open(io.BytesIO(file_content)) as img:
                validation["format_valid"] = True
                validation["image_format"] = img.format
                validation["image_size"] = f"{img.width}x{img.height}"
                
        except Exception as e:
            validation["validation_error"] = str(e)
        
        return validation

    async def validate_seismic_format(self, file_content: bytes) -> Dict[str, Any]:
        """Validate seismic data file format"""
        
        validation = {"format_valid": True}  # Default to valid for unknown formats
        
        try:
            # Basic SEGY validation
            if len(file_content) >= 3200:
                header = file_content[:3200]
                if b'SEGY' in header or b'SEG-Y' in header:
                    validation["segy_format"] = True
                    validation["header_present"] = True
                else:
                    validation["segy_format"] = False
            else:
                validation["format_valid"] = False
                validation["error"] = "File too small to be valid seismic data"
                
        except Exception as e:
            validation["validation_error"] = str(e)
        
        return validation


async def main():
    """Main function to run the file processor"""
    
    print("Starting file processor...")
    
    processor = FileProcessor()
    
    # Process pending jobs once
    await processor.process_pending_jobs()
    
    print("File processing completed.")


if __name__ == "__main__":
    # Run the file processor
    asyncio.run(main())
