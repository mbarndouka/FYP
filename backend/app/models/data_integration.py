from sqlalchemy import Column, String, DateTime, Integer, Boolean, Enum, Text, Float, ForeignKey, func
from sqlalchemy.orm import relationship
from app.database.config import Base
import enum
from datetime import datetime


class FileType(enum.Enum):
    SEISMIC_DATA = "seismic_data"
    WELL_LOG = "well_log"
    CORE_SAMPLE = "core_sample"
    PRODUCTION_DATA = "production_data"
    RESERVOIR_MODEL = "reservoir_model"
    GEOLOGICAL_MAP = "geological_map"
    REPORT = "report"
    IMAGE = "image"
    DOCUMENT = "document"
    OTHER = "other"


class FileStatus(enum.Enum):
    UPLOADING = "uploading"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    QUARANTINED = "quarantined"


class ProcessingStatus(enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class DataFile(Base):
    __tablename__ = "data_files"
    
    id = Column(String, primary_key=True, index=True)
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)  # Supabase storage path
    file_size = Column(Integer, nullable=False)  # Size in bytes
    file_type = Column(Enum(FileType), nullable=False)
    mime_type = Column(String(100), nullable=True)
    file_hash = Column(String(64), nullable=True)  # SHA-256 hash for integrity
    
    # Upload information
    uploaded_by = Column(String, ForeignKey("users.id"), nullable=False)
    upload_timestamp = Column(DateTime(timezone=True), server_default=func.now())
    status = Column(Enum(FileStatus), default=FileStatus.UPLOADING)
    
    # Processing information
    processing_status = Column(Enum(ProcessingStatus), default=ProcessingStatus.PENDING)
    processing_started_at = Column(DateTime(timezone=True), nullable=True)
    processing_completed_at = Column(DateTime(timezone=True), nullable=True)
    processing_error = Column(Text, nullable=True)
    
    # Metadata
    description = Column(Text, nullable=True)
    tags = Column(Text, nullable=True)  # JSON string of tags
    location = Column(String(255), nullable=True)  # Geographic location
    acquisition_date = Column(DateTime(timezone=True), nullable=True)
    
    # Access control
    is_public = Column(Boolean, default=False)
    is_archived = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self):
        return f"<DataFile(id='{self.id}', filename='{self.original_filename}', type='{self.file_type.value}')>"


class FileMetadata(Base):
    __tablename__ = "file_metadata"
    
    id = Column(String, primary_key=True, index=True)
    file_id = Column(String, ForeignKey("data_files.id"), nullable=False)
    
    # Extracted metadata fields
    width = Column(Integer, nullable=True)  # For images/maps
    height = Column(Integer, nullable=True)  # For images/maps
    duration = Column(Float, nullable=True)  # For audio/video files
    sample_rate = Column(Float, nullable=True)  # For seismic data
    frequency_range = Column(String(100), nullable=True)  # For seismic data
    coordinate_system = Column(String(100), nullable=True)  # For geographical data
    
    # Custom metadata as JSON
    custom_metadata = Column(Text, nullable=True)  # JSON string
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self):
        return f"<FileMetadata(id='{self.id}', file_id='{self.file_id}')>"


class FileAccessLog(Base):
    __tablename__ = "file_access_logs"
    
    id = Column(String, primary_key=True, index=True)
    file_id = Column(String, ForeignKey("data_files.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    
    action = Column(String(50), nullable=False)  # upload, download, view, delete, etc.
    ip_address = Column(String(45), nullable=True)  # IPv4 or IPv6
    user_agent = Column(String(500), nullable=True)
    
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f"<FileAccessLog(id='{self.id}', file_id='{self.file_id}', action='{self.action}')>"


class FileShare(Base):
    __tablename__ = "file_shares"
    
    id = Column(String, primary_key=True, index=True)
    file_id = Column(String, ForeignKey("data_files.id"), nullable=False)
    shared_by = Column(String, ForeignKey("users.id"), nullable=False)
    shared_with = Column(String, ForeignKey("users.id"), nullable=False)
    
    permission = Column(String(20), default="read")  # read, write, admin
    expires_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f"<FileShare(id='{self.id}', file_id='{self.file_id}', permission='{self.permission}')>"


class DataIntegrationJob(Base):
    __tablename__ = "data_integration_jobs"
    
    id = Column(String, primary_key=True, index=True)
    file_id = Column(String, ForeignKey("data_files.id"), nullable=False)
    job_type = Column(String(50), nullable=False)  # format_conversion, metadata_extraction, validation
    
    status = Column(Enum(ProcessingStatus), default=ProcessingStatus.PENDING)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Job configuration and results
    config = Column(Text, nullable=True)  # JSON string of job configuration
    result = Column(Text, nullable=True)  # JSON string of job results
    error_message = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f"<DataIntegrationJob(id='{self.id}', type='{self.job_type}', status='{self.status.value}')>"
