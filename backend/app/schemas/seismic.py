from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class ProcessingStatus(str, Enum):
    RAW = "raw"
    PROCESSED = "processed"
    ANALYZED = "analyzed"

class AnalysisStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class InterpretationType(str, Enum):
    HORIZON = "horizon"
    FAULT = "fault"
    SALT_BODY = "salt_body"
    CHANNEL = "channel"
    REEF = "reef"

class AnalysisType(str, Enum):
    NOISE_REDUCTION = "noise_reduction"
    MIGRATION = "migration"
    ATTRIBUTE_ANALYSIS = "attribute_analysis"
    AMPLITUDE_ANALYSIS = "amplitude_analysis"
    FREQUENCY_ANALYSIS = "frequency_analysis"
    COHERENCE_ANALYSIS = "coherence_analysis"

# Base schemas
class SeismicDatasetBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    file_format: str = Field(..., min_length=1, max_length=50)
    acquisition_date: Optional[datetime] = None
    
    # Spatial coordinates
    min_inline: Optional[int] = None
    max_inline: Optional[int] = None
    min_crossline: Optional[int] = None
    max_crossline: Optional[int] = None
    min_time: Optional[float] = None
    max_time: Optional[float] = None
    
    # Metadata
    sample_rate: Optional[float] = None
    trace_count: Optional[int] = None
    inline_increment: Optional[int] = 1
    crossline_increment: Optional[int] = 1
    crs: Optional[str] = None

class SeismicDatasetCreate(SeismicDatasetBase):
    pass

class SeismicDatasetUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    processing_status: Optional[ProcessingStatus] = None
    
    # Spatial coordinates
    min_inline: Optional[int] = None
    max_inline: Optional[int] = None
    min_crossline: Optional[int] = None
    max_crossline: Optional[int] = None
    min_time: Optional[float] = None
    max_time: Optional[float] = None
    
    # Metadata
    sample_rate: Optional[float] = None
    trace_count: Optional[int] = None
    inline_increment: Optional[int] = None
    crossline_increment: Optional[int] = None
    crs: Optional[str] = None

class SeismicDataset(SeismicDatasetBase):
    id: int
    file_path: str
    file_size: Optional[int] = None
    processing_status: ProcessingStatus
    uploaded_by: int
    uploaded_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# Interpretation schemas
class SeismicInterpretationBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    interpretation_type: InterpretationType
    geometry_data: Optional[Dict[str, Any]] = None
    color: Optional[str] = Field("#FF0000", regex=r"^#[0-9A-Fa-f]{6}$")
    opacity: Optional[float] = Field(1.0, ge=0.0, le=1.0)
    thickness: Optional[float] = Field(1.0, gt=0.0)
    confidence_level: Optional[float] = Field(0.5, ge=0.0, le=1.0)
    quality_score: Optional[float] = None

class SeismicInterpretationCreate(SeismicInterpretationBase):
    dataset_id: int

class SeismicInterpretationUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    interpretation_type: Optional[InterpretationType] = None
    geometry_data: Optional[Dict[str, Any]] = None
    color: Optional[str] = Field(None, regex=r"^#[0-9A-Fa-f]{6}$")
    opacity: Optional[float] = Field(None, ge=0.0, le=1.0)
    thickness: Optional[float] = Field(None, gt=0.0)
    confidence_level: Optional[float] = Field(None, ge=0.0, le=1.0)
    quality_score: Optional[float] = None
    is_active: Optional[bool] = None

class SeismicInterpretation(SeismicInterpretationBase):
    id: int
    dataset_id: int
    interpreter_id: int
    created_at: datetime
    updated_at: datetime
    is_active: bool
    
    class Config:
        from_attributes = True

# Analysis schemas
class SeismicAnalysisBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    analysis_type: AnalysisType
    parameters: Optional[Dict[str, Any]] = None

class SeismicAnalysisCreate(SeismicAnalysisBase):
    dataset_id: int

class SeismicAnalysisUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    status: Optional[AnalysisStatus] = None
    progress: Optional[float] = Field(None, ge=0.0, le=100.0)
    error_message: Optional[str] = None

class SeismicAnalysis(SeismicAnalysisBase):
    id: int
    dataset_id: int
    result_file_path: Optional[str] = None
    result_metadata: Optional[Dict[str, Any]] = None
    algorithm_version: Optional[str] = None
    processing_time: Optional[float] = None
    cpu_usage: Optional[float] = None
    memory_usage: Optional[float] = None
    status: AnalysisStatus
    progress: float
    error_message: Optional[str] = None
    analyst_id: int
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

# Session schemas
class SeismicSessionBase(BaseModel):
    session_name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    datasets: Optional[List[int]] = []
    viewport_settings: Optional[Dict[str, Any]] = None
    display_settings: Optional[Dict[str, Any]] = None
    is_shared: Optional[bool] = False
    shared_with: Optional[List[int]] = []

class SeismicSessionCreate(SeismicSessionBase):
    pass

class SeismicSessionUpdate(BaseModel):
    session_name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    datasets: Optional[List[int]] = None
    viewport_settings: Optional[Dict[str, Any]] = None
    display_settings: Optional[Dict[str, Any]] = None
    is_shared: Optional[bool] = None
    shared_with: Optional[List[int]] = None

class SeismicSession(SeismicSessionBase):
    id: int
    user_id: int
    created_at: datetime
    last_accessed: datetime
    
    class Config:
        from_attributes = True

# Upload schemas
class SeismicUploadResponse(BaseModel):
    dataset_id: int
    message: str
    file_info: Dict[str, Any]

# Processing schemas
class ProcessingParameters(BaseModel):
    # Noise reduction parameters
    filter_type: Optional[str] = None
    cutoff_frequency: Optional[float] = None
    filter_order: Optional[int] = None
    
    # Migration parameters
    migration_type: Optional[str] = None  # time, depth, kirchhoff, rtm
    velocity_model: Optional[str] = None
    aperture: Optional[float] = None
    
    # Attribute parameters
    attribute_type: Optional[str] = None
    window_size: Optional[int] = None
    overlap: Optional[float] = None

class VisualizationSettings(BaseModel):
    color_map: Optional[str] = "seismic"
    amplitude_range: Optional[List[float]] = None
    transparency: Optional[float] = Field(1.0, ge=0.0, le=1.0)
    slice_position: Optional[Dict[str, float]] = None
    view_mode: Optional[str] = "3d"  # 2d, 3d, slice
    lighting: Optional[Dict[str, Any]] = None

class InterpretationPoint(BaseModel):
    x: float
    y: float
    z: float
    inline: Optional[int] = None
    crossline: Optional[int] = None
    time: Optional[float] = None

class InterpretationGeometry(BaseModel):
    points: List[InterpretationPoint]
    lines: Optional[List[List[int]]] = None  # indices into points array
    surfaces: Optional[List[Dict[str, Any]]] = None
