from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class ReservoirDataType(str, Enum):
    HISTORICAL = "historical"
    REAL_TIME = "real_time"
    SYNTHETIC = "synthetic"


class SimulationStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ForecastStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class WarningLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# Base schemas for creation
class ReservoirDataCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    data_type: ReservoirDataType
    metadata: Optional[Dict[str, Any]] = None
    location_data: Optional[Dict[str, Any]] = None
    time_range_start: Optional[datetime] = None
    time_range_end: Optional[datetime] = None


class ReservoirSimulationCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    reservoir_data_id: str
    simulation_parameters: Dict[str, Any]
    extraction_scenario: str = Field(..., min_length=1, max_length=255)


class ReservoirForecastCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    simulation_id: str
    model_type: str
    model_parameters: Optional[Dict[str, Any]] = None
    forecast_horizon_days: int = Field(..., gt=0)


class ReservoirWarningCreate(BaseModel):
    forecast_id: str
    warning_type: str
    severity_level: WarningLevel
    title: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1)
    trigger_conditions: Dict[str, Any]
    recommended_actions: Optional[Dict[str, Any]] = None
    predicted_occurrence_date: Optional[datetime] = None
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0)


class PredictionSessionCreate(BaseModel):
    session_name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    data_sources: List[str]  # List of reservoir data IDs
    analysis_parameters: Dict[str, Any]
    preprocessing_steps: Optional[Dict[str, Any]] = None
    ml_pipeline_config: Dict[str, Any]
    feature_engineering_steps: Optional[Dict[str, Any]] = None
    model_selection_criteria: Optional[Dict[str, Any]] = None


# Update schemas
class ReservoirDataUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    location_data: Optional[Dict[str, Any]] = None
    time_range_start: Optional[datetime] = None
    time_range_end: Optional[datetime] = None
    is_processed: Optional[bool] = None


class ReservoirSimulationUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    simulation_parameters: Optional[Dict[str, Any]] = None
    extraction_scenario: Optional[str] = Field(None, min_length=1, max_length=255)
    status: Optional[SimulationStatus] = None
    error_message: Optional[str] = None
    results_summary: Optional[Dict[str, Any]] = None
    visualization_data: Optional[Dict[str, Any]] = None


class ReservoirForecastUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    status: Optional[ForecastStatus] = None
    model_parameters: Optional[Dict[str, Any]] = None
    training_data_info: Optional[Dict[str, Any]] = None
    model_accuracy_metrics: Optional[Dict[str, Any]] = None
    forecast_data: Optional[Dict[str, Any]] = None
    confidence_intervals: Optional[Dict[str, Any]] = None
    predicted_production_rate: Optional[float] = None
    predicted_reservoir_pressure: Optional[float] = None
    estimated_recovery_factor: Optional[float] = None


class ReservoirWarningUpdate(BaseModel):
    severity_level: Optional[WarningLevel] = None
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, min_length=1)
    trigger_conditions: Optional[Dict[str, Any]] = None
    recommended_actions: Optional[Dict[str, Any]] = None
    predicted_occurrence_date: Optional[datetime] = None
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    is_acknowledged: Optional[bool] = None


# Response schemas
class ReservoirDataResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    data_type: ReservoirDataType
    file_path: str
    file_size: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None
    location_data: Optional[Dict[str, Any]] = None
    time_range_start: Optional[datetime] = None
    time_range_end: Optional[datetime] = None
    uploaded_by: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    is_processed: bool

    class Config:
        from_attributes = True


class ReservoirSimulationResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    reservoir_data_id: str
    simulation_parameters: Dict[str, Any]
    extraction_scenario: str
    status: SimulationStatus
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    results_path: Optional[str] = None
    results_summary: Optional[Dict[str, Any]] = None
    visualization_data: Optional[Dict[str, Any]] = None
    created_by: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ReservoirForecastResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    simulation_id: str
    model_type: str
    model_parameters: Optional[Dict[str, Any]] = None
    training_data_info: Optional[Dict[str, Any]] = None
    model_accuracy_metrics: Optional[Dict[str, Any]] = None
    forecast_data: Dict[str, Any]
    confidence_intervals: Optional[Dict[str, Any]] = None
    forecast_horizon_days: int
    predicted_production_rate: Optional[float] = None
    predicted_reservoir_pressure: Optional[float] = None
    estimated_recovery_factor: Optional[float] = None
    status: ForecastStatus
    generated_at: datetime
    published_at: Optional[datetime] = None
    created_by: str

    class Config:
        from_attributes = True


class ReservoirWarningResponse(BaseModel):
    id: str
    forecast_id: str
    warning_type: str
    severity_level: WarningLevel
    title: str
    description: str
    trigger_conditions: Dict[str, Any]
    recommended_actions: Optional[Dict[str, Any]] = None
    predicted_occurrence_date: Optional[datetime] = None
    confidence_score: Optional[float] = None
    is_acknowledged: bool
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PredictionSessionResponse(BaseModel):
    id: str
    session_name: str
    description: Optional[str] = None
    data_sources: List[str]
    analysis_parameters: Dict[str, Any]
    preprocessing_steps: Optional[Dict[str, Any]] = None
    ml_pipeline_config: Dict[str, Any]
    feature_engineering_steps: Optional[Dict[str, Any]] = None
    model_selection_criteria: Optional[Dict[str, Any]] = None
    session_results: Optional[Dict[str, Any]] = None
    generated_forecasts: Optional[List[str]] = None
    generated_warnings: Optional[List[str]] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    created_by: str
    shared_with_users: Optional[List[str]] = None

    class Config:
        from_attributes = True


# Special request schemas for complex operations
class PredictiveAnalysisRequest(BaseModel):
    """Schema for running predictive analysis as per the flow"""
    session_name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    data_source_ids: List[str] = Field(..., min_items=1)
    preprocessing_config: Optional[Dict[str, Any]] = None
    ml_algorithms: List[str] = Field(default=["lstm", "random_forest", "neural_network"])
    forecast_horizon_days: int = Field(default=365, gt=0, le=3650)  # Max 10 years
    warning_thresholds: Optional[Dict[str, Any]] = None
    notification_users: Optional[List[str]] = None


class SimulationComparisonRequest(BaseModel):
    """Schema for comparing different extraction scenarios"""
    simulation_ids: List[str] = Field(..., min_items=2)
    comparison_metrics: List[str] = Field(default=["production_rate", "recovery_factor", "reservoir_pressure"])
    visualization_type: str = Field(default="side_by_side")


class WarningAcknowledgmentRequest(BaseModel):
    """Schema for acknowledging warnings"""
    warning_ids: List[str] = Field(..., min_items=1)
    acknowledgment_note: Optional[str] = None


# List response schemas
class ReservoirDataList(BaseModel):
    items: List[ReservoirDataResponse]
    total: int
    page: int
    page_size: int


class ReservoirSimulationList(BaseModel):
    items: List[ReservoirSimulationResponse]
    total: int
    page: int
    page_size: int


class ReservoirForecastList(BaseModel):
    items: List[ReservoirForecastResponse]
    total: int
    page: int
    page_size: int


class ReservoirWarningList(BaseModel):
    items: List[ReservoirWarningResponse]
    total: int
    page: int
    page_size: int


class PredictionSessionList(BaseModel):
    items: List[PredictionSessionResponse]
    total: int
    page: int
    page_size: int
