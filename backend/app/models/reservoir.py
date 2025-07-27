from sqlalchemy import Column, String, DateTime, Boolean, Enum, func, Text, Float, Integer, JSON, ForeignKey
from sqlalchemy.orm import relationship
from app.database.config import Base
import enum


class ReservoirDataType(enum.Enum):
    HISTORICAL = "historical"
    REAL_TIME = "real_time"
    SYNTHETIC = "synthetic"


class SimulationStatus(enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ForecastStatus(enum.Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class WarningLevel(enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ReservoirData(Base):
    __tablename__ = "reservoir_data"
    
    id = Column(String, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    data_type = Column(Enum(ReservoirDataType), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=True)
    metadata = Column(JSON, nullable=True)  # Store additional properties like porosity, permeability, etc.
    
    # Spatial and temporal information
    location_data = Column(JSON, nullable=True)  # Coordinates, well locations
    time_range_start = Column(DateTime(timezone=True), nullable=True)
    time_range_end = Column(DateTime(timezone=True), nullable=True)
    
    # Upload and ownership information
    uploaded_by = Column(String, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    is_processed = Column(Boolean, default=False)
    
    # Relationships
    uploader = relationship("User", back_populates="reservoir_data")
    simulations = relationship("ReservoirSimulation", back_populates="reservoir_data")
    
    def __repr__(self):
        return f"<ReservoirData(id='{self.id}', name='{self.name}', type='{self.data_type.value}')>"


class ReservoirSimulation(Base):
    __tablename__ = "reservoir_simulations"
    
    id = Column(String, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Simulation configuration
    reservoir_data_id = Column(String, ForeignKey("reservoir_data.id"), nullable=False)
    simulation_parameters = Column(JSON, nullable=False)  # Extraction scenarios, model parameters
    extraction_scenario = Column(String(255), nullable=False)  # Name/type of extraction scenario
    
    # Execution information
    status = Column(Enum(SimulationStatus), nullable=False, default=SimulationStatus.PENDING)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Results
    results_path = Column(String(500), nullable=True)
    results_summary = Column(JSON, nullable=True)  # Key metrics and outcomes
    visualization_data = Column(JSON, nullable=True)  # Data for charts and visualizations
    
    # Ownership and tracking
    created_by = Column(String, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    reservoir_data = relationship("ReservoirData", back_populates="simulations")
    creator = relationship("User", back_populates="reservoir_simulations")
    forecasts = relationship("ReservoirForecast", back_populates="simulation")
    
    def __repr__(self):
        return f"<ReservoirSimulation(id='{self.id}', name='{self.name}', status='{self.status.value}')>"


class ReservoirForecast(Base):
    __tablename__ = "reservoir_forecasts"
    
    id = Column(String, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Forecast source
    simulation_id = Column(String, ForeignKey("reservoir_simulations.id"), nullable=False)
    
    # ML Model information
    model_type = Column(String(100), nullable=False)  # e.g., 'LSTM', 'Random Forest', 'Neural Network'
    model_parameters = Column(JSON, nullable=True)
    training_data_info = Column(JSON, nullable=True)
    model_accuracy_metrics = Column(JSON, nullable=True)
    
    # Forecast data
    forecast_data = Column(JSON, nullable=False)  # Time series predictions
    confidence_intervals = Column(JSON, nullable=True)
    forecast_horizon_days = Column(Integer, nullable=False)
    
    # Performance metrics
    predicted_production_rate = Column(Float, nullable=True)
    predicted_reservoir_pressure = Column(Float, nullable=True)
    estimated_recovery_factor = Column(Float, nullable=True)
    
    # Status and metadata
    status = Column(Enum(ForecastStatus), nullable=False, default=ForecastStatus.DRAFT)
    generated_at = Column(DateTime(timezone=True), server_default=func.now())
    published_at = Column(DateTime(timezone=True), nullable=True)
    
    # Ownership
    created_by = Column(String, ForeignKey("users.id"), nullable=False)
    
    # Relationships
    simulation = relationship("ReservoirSimulation", back_populates="forecasts")
    creator = relationship("User", back_populates="reservoir_forecasts")
    warnings = relationship("ReservoirWarning", back_populates="forecast")
    
    def __repr__(self):
        return f"<ReservoirForecast(id='{self.id}', name='{self.name}', status='{self.status.value}')>"


class ReservoirWarning(Base):
    __tablename__ = "reservoir_warnings"
    
    id = Column(String, primary_key=True, index=True)
    forecast_id = Column(String, ForeignKey("reservoir_forecasts.id"), nullable=False)
    
    # Warning details
    warning_type = Column(String(100), nullable=False)  # e.g., 'pressure_drop', 'production_decline'
    severity_level = Column(Enum(WarningLevel), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    
    # Warning triggers and thresholds
    trigger_conditions = Column(JSON, nullable=False)
    recommended_actions = Column(JSON, nullable=True)
    
    # Temporal information
    predicted_occurrence_date = Column(DateTime(timezone=True), nullable=True)
    confidence_score = Column(Float, nullable=True)  # 0.0 to 1.0
    
    # Status tracking
    is_acknowledged = Column(Boolean, default=False)
    acknowledged_by = Column(String, ForeignKey("users.id"), nullable=True)
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    forecast = relationship("ReservoirForecast", back_populates="warnings")
    acknowledger = relationship("User", back_populates="acknowledged_warnings")
    
    def __repr__(self):
        return f"<ReservoirWarning(id='{self.id}', type='{self.warning_type}', level='{self.severity_level.value}')>"


class PredictionSession(Base):
    __tablename__ = "prediction_sessions"
    
    id = Column(String, primary_key=True, index=True)
    session_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Session data
    data_sources = Column(JSON, nullable=False)  # List of reservoir data IDs used
    analysis_parameters = Column(JSON, nullable=False)
    preprocessing_steps = Column(JSON, nullable=True)
    
    # ML Pipeline information
    ml_pipeline_config = Column(JSON, nullable=False)
    feature_engineering_steps = Column(JSON, nullable=True)
    model_selection_criteria = Column(JSON, nullable=True)
    
    # Session results
    session_results = Column(JSON, nullable=True)
    generated_forecasts = Column(JSON, nullable=True)  # List of forecast IDs
    generated_warnings = Column(JSON, nullable=True)  # List of warning IDs
    
    # Execution tracking
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    
    # Ownership and sharing
    created_by = Column(String, ForeignKey("users.id"), nullable=False)
    shared_with_users = Column(JSON, nullable=True)  # List of user IDs with access
    
    # Relationships
    creator = relationship("User", back_populates="prediction_sessions")
    
    def __repr__(self):
        return f"<PredictionSession(id='{self.id}', name='{self.session_name}')>"


# Add relationships to User model (this would be added to user.py)
# We'll handle this in the user.py file update
