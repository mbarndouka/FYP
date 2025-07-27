from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
import uuid
import os
import json
from pathlib import Path
from datetime import datetime

from app.database.config import get_db
from app.auth.dependencies import get_current_user
from app.models.user import User, UserRole
from app.services.reservoir_service import ReservoirService
from app.schemas.reservoir import (
    ReservoirDataCreate, ReservoirDataResponse, ReservoirDataUpdate, ReservoirDataList,
    ReservoirSimulationCreate, ReservoirSimulationResponse, ReservoirSimulationUpdate, ReservoirSimulationList,
    ReservoirForecastResponse, ReservoirForecastUpdate, ReservoirForecastList,
    ReservoirWarningResponse, ReservoirWarningList, WarningAcknowledgmentRequest,
    PredictionSessionCreate, PredictionSessionResponse, PredictionSessionList,
    PredictiveAnalysisRequest, SimulationComparisonRequest,
    ReservoirDataType, SimulationStatus, ForecastStatus, WarningLevel
)
from app.tasks.reservoir_tasks import run_reservoir_simulation, run_predictive_analysis

router = APIRouter(prefix="/reservoir", tags=["reservoir"])

# File upload configuration
UPLOAD_DIR = Path("uploads/reservoir")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {'.csv', '.xlsx', '.xls', '.json', '.txt'}
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB


def validate_user_role(user: User, allowed_roles: List[UserRole]):
    """Validate user has required role"""
    if user.role not in allowed_roles:
        raise HTTPException(
            status_code=403,
            detail=f"Access denied. Required roles: {[role.value for role in allowed_roles]}"
        )


# Reservoir Data Endpoints
@router.post("/data/upload", response_model=ReservoirDataResponse)
async def upload_reservoir_data(
    name: str = Form(...),
    description: Optional[str] = Form(None),
    data_type: ReservoirDataType = Form(...),
    metadata: Optional[str] = Form(None),
    location_data: Optional[str] = Form(None),
    time_range_start: Optional[str] = Form(None),
    time_range_end: Optional[str] = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Upload reservoir data file"""
    validate_user_role(current_user, [UserRole.RESERVOIR_ENGINEER, UserRole.GEOSCIENTIST, UserRole.ADMIN])
    
    # Validate file
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file selected")
    
    file_extension = Path(file.filename).suffix.lower()
    if file_extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400, 
            detail=f"File type not allowed. Supported: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # Check file size
    file_content = await file.read()
    if len(file_content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large")
    
    # Save file
    file_id = str(uuid.uuid4())
    file_path = UPLOAD_DIR / f"{file_id}_{file.filename}"
    
    with open(file_path, "wb") as f:
        f.write(file_content)
    
    # Parse metadata and location data
    try:
        parsed_metadata = json.loads(metadata) if metadata else None
        parsed_location_data = json.loads(location_data) if location_data else None
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON format in metadata or location_data")
    
    # Parse datetime strings
    try:
        parsed_time_start = datetime.fromisoformat(time_range_start) if time_range_start else None
        parsed_time_end = datetime.fromisoformat(time_range_end) if time_range_end else None
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid datetime format")
    
    # Create data record
    data_create = ReservoirDataCreate(
        name=name,
        description=description,
        data_type=data_type,
        metadata=parsed_metadata,
        location_data=parsed_location_data,
        time_range_start=parsed_time_start,
        time_range_end=parsed_time_end
    )
    
    reservoir_service = ReservoirService(db)
    reservoir_data = reservoir_service.create_reservoir_data(
        data_create, 
        current_user.id, 
        str(file_path), 
        len(file_content)
    )
    
    return reservoir_data


@router.get("/data", response_model=ReservoirDataList)
async def get_reservoir_data_list(
    data_type: Optional[ReservoirDataType] = Query(None),
    is_processed: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get list of reservoir data"""
    validate_user_role(current_user, [UserRole.RESERVOIR_ENGINEER, UserRole.GEOSCIENTIST, UserRole.MANAGER, UserRole.ADMIN])
    
    skip = (page - 1) * page_size
    reservoir_service = ReservoirService(db)
    
    # Only show own data unless admin/manager
    user_filter = current_user.id if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER] else None
    
    items, total = reservoir_service.get_reservoir_data_list(
        user_id=user_filter,
        data_type=data_type,
        is_processed=is_processed,
        skip=skip,
        limit=page_size
    )
    
    return ReservoirDataList(items=items, total=total, page=page, page_size=page_size)


@router.get("/data/{data_id}", response_model=ReservoirDataResponse)
async def get_reservoir_data(
    data_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get specific reservoir data"""
    validate_user_role(current_user, [UserRole.RESERVOIR_ENGINEER, UserRole.GEOSCIENTIST, UserRole.MANAGER, UserRole.ADMIN])
    
    reservoir_service = ReservoirService(db)
    data = reservoir_service.get_reservoir_data(data_id)
    
    if not data:
        raise HTTPException(status_code=404, detail="Reservoir data not found")
    
    # Check ownership unless admin/manager
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER] and data.uploaded_by != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return data


@router.put("/data/{data_id}", response_model=ReservoirDataResponse)
async def update_reservoir_data(
    data_id: str,
    data_update: ReservoirDataUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update reservoir data"""
    validate_user_role(current_user, [UserRole.RESERVOIR_ENGINEER, UserRole.GEOSCIENTIST, UserRole.ADMIN])
    
    reservoir_service = ReservoirService(db)
    data = reservoir_service.get_reservoir_data(data_id)
    
    if not data:
        raise HTTPException(status_code=404, detail="Reservoir data not found")
    
    # Check ownership unless admin
    if current_user.role != UserRole.ADMIN and data.uploaded_by != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    updated_data = reservoir_service.update_reservoir_data(data_id, data_update)
    return updated_data


@router.delete("/data/{data_id}")
async def delete_reservoir_data(
    data_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete reservoir data"""
    validate_user_role(current_user, [UserRole.RESERVOIR_ENGINEER, UserRole.ADMIN])
    
    reservoir_service = ReservoirService(db)
    data = reservoir_service.get_reservoir_data(data_id)
    
    if not data:
        raise HTTPException(status_code=404, detail="Reservoir data not found")
    
    # Check ownership unless admin
    if current_user.role != UserRole.ADMIN and data.uploaded_by != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    success = reservoir_service.delete_reservoir_data(data_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete reservoir data")
    
    return {"message": "Reservoir data deleted successfully"}


# Reservoir Simulation Endpoints
@router.post("/simulations", response_model=ReservoirSimulationResponse)
async def create_reservoir_simulation(
    simulation: ReservoirSimulationCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create and start reservoir simulation"""
    validate_user_role(current_user, [UserRole.RESERVOIR_ENGINEER, UserRole.GEOSCIENTIST, UserRole.ADMIN])
    
    reservoir_service = ReservoirService(db)
    
    # Verify reservoir data exists and is accessible
    reservoir_data = reservoir_service.get_reservoir_data(simulation.reservoir_data_id)
    if not reservoir_data:
        raise HTTPException(status_code=404, detail="Reservoir data not found")
    
    if not reservoir_data.is_processed:
        raise HTTPException(status_code=400, detail="Reservoir data is not processed yet")
    
    # Create simulation
    created_simulation = reservoir_service.create_reservoir_simulation(simulation, current_user.id)
    
    # Start background task
    background_tasks.add_task(run_reservoir_simulation.delay, created_simulation.id)
    
    return created_simulation


@router.get("/simulations", response_model=ReservoirSimulationList)
async def get_simulation_list(
    reservoir_data_id: Optional[str] = Query(None),
    status: Optional[SimulationStatus] = Query(None),
    extraction_scenario: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get list of simulations"""
    validate_user_role(current_user, [UserRole.RESERVOIR_ENGINEER, UserRole.GEOSCIENTIST, UserRole.MANAGER, UserRole.ADMIN])
    
    skip = (page - 1) * page_size
    reservoir_service = ReservoirService(db)
    
    # Only show own simulations unless admin/manager
    user_filter = current_user.id if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER] else None
    
    items, total = reservoir_service.get_simulation_list(
        user_id=user_filter,
        reservoir_data_id=reservoir_data_id,
        status=status,
        extraction_scenario=extraction_scenario,
        skip=skip,
        limit=page_size
    )
    
    return ReservoirSimulationList(items=items, total=total, page=page, page_size=page_size)


@router.get("/simulations/{simulation_id}", response_model=ReservoirSimulationResponse)
async def get_simulation(
    simulation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get specific simulation"""
    validate_user_role(current_user, [UserRole.RESERVOIR_ENGINEER, UserRole.GEOSCIENTIST, UserRole.MANAGER, UserRole.ADMIN])
    
    reservoir_service = ReservoirService(db)
    simulation = reservoir_service.get_reservoir_simulation(simulation_id)
    
    if not simulation:
        raise HTTPException(status_code=404, detail="Simulation not found")
    
    # Check ownership unless admin/manager
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER] and simulation.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return simulation


@router.post("/simulations/compare")
async def compare_simulations(
    comparison_request: SimulationComparisonRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Compare different extraction scenarios"""
    validate_user_role(current_user, [UserRole.RESERVOIR_ENGINEER, UserRole.GEOSCIENTIST, UserRole.MANAGER, UserRole.ADMIN])
    
    reservoir_service = ReservoirService(db)
    simulations = reservoir_service.get_simulation_comparison_data(comparison_request.simulation_ids)
    
    if len(simulations) != len(comparison_request.simulation_ids):
        raise HTTPException(status_code=404, detail="One or more simulations not found or not completed")
    
    # Check access permissions
    for simulation in simulations:
        if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER] and simulation.created_by != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied to one or more simulations")
    
    # Generate comparison data
    comparison_data = {
        'simulations': [],
        'comparison_metrics': comparison_request.comparison_metrics,
        'visualization_type': comparison_request.visualization_type
    }
    
    for simulation in simulations:
        sim_data = {
            'id': simulation.id,
            'name': simulation.name,
            'extraction_scenario': simulation.extraction_scenario,
            'results_summary': simulation.results_summary,
            'visualization_data': simulation.visualization_data
        }
        comparison_data['simulations'].append(sim_data)
    
    return comparison_data


# Predictive Analysis Endpoints (Main Flow)
@router.post("/predictive-analysis", response_model=PredictionSessionResponse)
async def run_predictive_analysis_endpoint(
    analysis_request: PredictiveAnalysisRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Run predictive analysis (implements the main flow)"""
    validate_user_role(current_user, [UserRole.RESERVOIR_ENGINEER, UserRole.GEOSCIENTIST, UserRole.ADMIN])
    
    reservoir_service = ReservoirService(db)
    
    # Step 1: Reservoir Engineer navigates to predictive analytics interface (handled by frontend)
    
    # Step 2: Verify data sources exist and are accessible
    data_sources = reservoir_service.get_data_for_analysis(analysis_request.data_source_ids)
    if not data_sources:
        raise HTTPException(status_code=404, detail="No valid data sources found")
    
    # Create prediction session
    session_create = PredictionSessionCreate(
        session_name=analysis_request.session_name,
        description=analysis_request.description,
        data_sources=analysis_request.data_source_ids,
        analysis_parameters={
            'ml_algorithms': analysis_request.ml_algorithms,
            'forecast_horizon_days': analysis_request.forecast_horizon_days,
            'warning_thresholds': analysis_request.warning_thresholds or {}
        },
        preprocessing_steps=analysis_request.preprocessing_config,
        ml_pipeline_config={
            'models': {
                'random_forest': {'n_estimators': 100, 'max_depth': 10},
                'lstm': {'lstm_units': 50, 'epochs': 50, 'lookback': 60}
            },
            'forecast_horizon_days': analysis_request.forecast_horizon_days,
            'warning_thresholds': analysis_request.warning_thresholds or {
                'production_decline_threshold': -0.1,
                'low_production_threshold': 100,
                'high_volatility_threshold': 50
            }
        }
    )
    
    session = reservoir_service.create_prediction_session(session_create, current_user.id)
    
    # Start background analysis task (Steps 3-8 handled in background)
    background_tasks.add_task(
        run_predictive_analysis.delay, 
        session.id, 
        session_create.ml_pipeline_config
    )
    
    return session


@router.get("/forecasts", response_model=ReservoirForecastList)
async def get_forecast_list(
    simulation_id: Optional[str] = Query(None),
    status: Optional[ForecastStatus] = Query(None),
    model_type: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get list of forecasts"""
    validate_user_role(current_user, [UserRole.RESERVOIR_ENGINEER, UserRole.GEOSCIENTIST, UserRole.MANAGER, UserRole.ADMIN])
    
    skip = (page - 1) * page_size
    reservoir_service = ReservoirService(db)
    
    # Only show own forecasts unless admin/manager
    user_filter = current_user.id if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER] else None
    
    items, total = reservoir_service.get_forecast_list(
        user_id=user_filter,
        simulation_id=simulation_id,
        status=status,
        model_type=model_type,
        skip=skip,
        limit=page_size
    )
    
    return ReservoirForecastList(items=items, total=total, page=page, page_size=page_size)


@router.get("/forecasts/{forecast_id}", response_model=ReservoirForecastResponse)
async def get_forecast(
    forecast_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get specific forecast"""
    validate_user_role(current_user, [UserRole.RESERVOIR_ENGINEER, UserRole.GEOSCIENTIST, UserRole.MANAGER, UserRole.ADMIN])
    
    reservoir_service = ReservoirService(db)
    forecast = reservoir_service.get_reservoir_forecast(forecast_id)
    
    if not forecast:
        raise HTTPException(status_code=404, detail="Forecast not found")
    
    # Check ownership unless admin/manager
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER] and forecast.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return forecast


@router.put("/forecasts/{forecast_id}/publish", response_model=ReservoirForecastResponse)
async def publish_forecast(
    forecast_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Publish a forecast"""
    validate_user_role(current_user, [UserRole.RESERVOIR_ENGINEER, UserRole.ADMIN])
    
    reservoir_service = ReservoirService(db)
    forecast = reservoir_service.get_reservoir_forecast(forecast_id)
    
    if not forecast:
        raise HTTPException(status_code=404, detail="Forecast not found")
    
    # Check ownership unless admin
    if current_user.role != UserRole.ADMIN and forecast.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    published_forecast = reservoir_service.publish_forecast(forecast_id)
    return published_forecast


# Warning Management Endpoints
@router.get("/warnings", response_model=ReservoirWarningList)
async def get_warning_list(
    forecast_id: Optional[str] = Query(None),
    severity_level: Optional[WarningLevel] = Query(None),
    is_acknowledged: Optional[bool] = Query(None),
    warning_type: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get list of warnings"""
    validate_user_role(current_user, [UserRole.RESERVOIR_ENGINEER, UserRole.GEOSCIENTIST, UserRole.MANAGER, UserRole.ADMIN])
    
    skip = (page - 1) * page_size
    reservoir_service = ReservoirService(db)
    
    items, total = reservoir_service.get_warning_list(
        forecast_id=forecast_id,
        severity_level=severity_level,
        is_acknowledged=is_acknowledged,
        warning_type=warning_type,
        skip=skip,
        limit=page_size
    )
    
    return ReservoirWarningList(items=items, total=total, page=page, page_size=page_size)


@router.post("/warnings/acknowledge")
async def acknowledge_warnings(
    acknowledgment_request: WarningAcknowledgmentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Acknowledge multiple warnings"""
    validate_user_role(current_user, [UserRole.RESERVOIR_ENGINEER, UserRole.GEOSCIENTIST, UserRole.MANAGER, UserRole.ADMIN])
    
    reservoir_service = ReservoirService(db)
    acknowledged_warnings = reservoir_service.acknowledge_multiple_warnings(
        acknowledgment_request.warning_ids,
        current_user.id
    )
    
    return {
        "message": f"Acknowledged {len(acknowledged_warnings)} warnings",
        "acknowledged_warnings": [w.id for w in acknowledged_warnings]
    }


@router.get("/warnings/unacknowledged", response_model=List[ReservoirWarningResponse])
async def get_unacknowledged_warnings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get unacknowledged warnings for current user"""
    validate_user_role(current_user, [UserRole.RESERVOIR_ENGINEER, UserRole.GEOSCIENTIST, UserRole.MANAGER, UserRole.ADMIN])
    
    reservoir_service = ReservoirService(db)
    
    # Only show warnings from own forecasts unless admin/manager
    user_filter = current_user.id if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER] else None
    
    warnings = reservoir_service.get_unacknowledged_warnings(user_filter)
    return warnings


# Prediction Session Endpoints
@router.get("/prediction-sessions", response_model=PredictionSessionList)
async def get_prediction_sessions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get prediction sessions"""
    validate_user_role(current_user, [UserRole.RESERVOIR_ENGINEER, UserRole.GEOSCIENTIST, UserRole.MANAGER, UserRole.ADMIN])
    
    # For simplicity, return empty list - this would need pagination implementation in service
    return PredictionSessionList(items=[], total=0, page=page, page_size=page_size)


@router.get("/prediction-sessions/{session_id}", response_model=PredictionSessionResponse)
async def get_prediction_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get specific prediction session"""
    validate_user_role(current_user, [UserRole.RESERVOIR_ENGINEER, UserRole.GEOSCIENTIST, UserRole.MANAGER, UserRole.ADMIN])
    
    reservoir_service = ReservoirService(db)
    session = reservoir_service.get_prediction_session(session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Prediction session not found")
    
    # Check ownership unless admin/manager
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER] and session.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return session


@router.get("/dashboard/summary")
async def get_dashboard_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get dashboard summary for reservoir engineer"""
    validate_user_role(current_user, [UserRole.RESERVOIR_ENGINEER, UserRole.GEOSCIENTIST, UserRole.MANAGER, UserRole.ADMIN])
    
    reservoir_service = ReservoirService(db)
    
    # Get recent forecasts
    recent_forecasts = reservoir_service.get_recent_forecasts(
        user_id=current_user.id if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER] else None
    )
    
    # Get unacknowledged warnings
    unacknowledged_warnings = reservoir_service.get_unacknowledged_warnings(
        user_id=current_user.id if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER] else None
    )
    
    return {
        'recent_forecasts_count': len(recent_forecasts),
        'unacknowledged_warnings_count': len(unacknowledged_warnings),
        'critical_warnings_count': len([w for w in unacknowledged_warnings if w.severity_level == WarningLevel.CRITICAL]),
        'recent_forecasts': recent_forecasts[:5],  # Latest 5
        'urgent_warnings': [w for w in unacknowledged_warnings if w.severity_level in [WarningLevel.HIGH, WarningLevel.CRITICAL]][:5]
    }
