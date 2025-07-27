from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class FileTypeEnum(str, Enum):
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


class FileStatusEnum(str, Enum):
    UPLOADING = "uploading"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    QUARANTINED = "quarantined"


class ProcessingStatusEnum(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


# Request schemas
class FileUploadRequest(BaseModel):
    file_type: FileTypeEnum
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    location: Optional[str] = None
    acquisition_date: Optional[datetime] = None
    is_public: bool = False


class FileUpdateRequest(BaseModel):
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    location: Optional[str] = None
    acquisition_date: Optional[datetime] = None
    is_public: Optional[bool] = None
    is_archived: Optional[bool] = None


class FileShareRequest(BaseModel):
    shared_with: str = Field(..., description="User ID to share the file with")
    permission: str = Field(default="read", regex="^(read|write|admin)$")
    expires_at: Optional[datetime] = None


class MetadataUpdateRequest(BaseModel):
    width: Optional[int] = None
    height: Optional[int] = None
    duration: Optional[float] = None
    sample_rate: Optional[float] = None
    frequency_range: Optional[str] = None
    coordinate_system: Optional[str] = None
    custom_metadata: Optional[Dict[str, Any]] = None


# Response schemas
class FileMetadataResponse(BaseModel):
    id: str
    file_id: str
    width: Optional[int]
    height: Optional[int]
    duration: Optional[float]
    sample_rate: Optional[float]
    frequency_range: Optional[str]
    coordinate_system: Optional[str]
    custom_metadata: Optional[Dict[str, Any]]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class DataFileResponse(BaseModel):
    id: str
    original_filename: str
    file_path: str
    file_size: int
    file_type: FileTypeEnum
    mime_type: Optional[str]
    file_hash: Optional[str]
    uploaded_by: str
    upload_timestamp: datetime
    status: FileStatusEnum
    processing_status: ProcessingStatusEnum
    processing_started_at: Optional[datetime]
    processing_completed_at: Optional[datetime]
    processing_error: Optional[str]
    description: Optional[str]
    tags: Optional[List[str]]
    location: Optional[str]
    acquisition_date: Optional[datetime]
    is_public: bool
    is_archived: bool
    created_at: datetime
    updated_at: Optional[datetime]

    @validator('tags', pre=True)
    def parse_tags(cls, v):
        if isinstance(v, str):
            import json
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return []
        return v or []

    class Config:
        from_attributes = True


class FileAccessLogResponse(BaseModel):
    id: str
    file_id: str
    user_id: str
    action: str
    ip_address: Optional[str]
    user_agent: Optional[str]
    timestamp: datetime

    class Config:
        from_attributes = True


class FileShareResponse(BaseModel):
    id: str
    file_id: str
    shared_by: str
    shared_with: str
    permission: str
    expires_at: Optional[datetime]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class DataIntegrationJobResponse(BaseModel):
    id: str
    file_id: str
    job_type: str
    status: ProcessingStatusEnum
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    config: Optional[Dict[str, Any]]
    result: Optional[Dict[str, Any]]
    error_message: Optional[str]
    created_at: datetime

    @validator('config', 'result', pre=True)
    def parse_json_fields(cls, v):
        if isinstance(v, str):
            import json
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return {}
        return v or {}

    class Config:
        from_attributes = True


# Upload response schemas
class FileUploadResponse(BaseModel):
    message: str
    file_id: str
    upload_url: str
    fields: Dict[str, str]


class FileUploadStatusResponse(BaseModel):
    file_id: str
    status: FileStatusEnum
    processing_status: ProcessingStatusEnum
    progress: Optional[float] = None
    message: Optional[str] = None


class FileListResponse(BaseModel):
    files: List[DataFileResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# Validation schemas
class FileValidationResult(BaseModel):
    is_valid: bool
    file_size: int
    mime_type: str
    errors: List[str] = []
    warnings: List[str] = []


class ProcessingSummary(BaseModel):
    total_files: int
    successful_uploads: int
    failed_uploads: int
    files_in_processing: int
    recent_activity: List[FileAccessLogResponse]
