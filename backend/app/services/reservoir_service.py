from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc, func
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import uuid
import json
import os
import shutil
from pathlib import Path

from app.models.reservoir import (
    ReservoirData, ReservoirSimulation, ReservoirForecast,
    ReservoirWarning, PredictionSession, ReservoirDataType,
    SimulationStatus, ForecastStatus, WarningLevel
)
from app.schemas.reservoir import (
    ReservoirDataCreate, ReservoirDataUpdate,
    ReservoirSimulationCreate, ReservoirSimulationUpdate,
    ReservoirForecastCreate, ReservoirForecastUpdate,
    ReservoirWarningCreate, ReservoirWarningUpdate,
    PredictionSessionCreate, PredictiveAnalysisRequest
)


class ReservoirService:
    def __init__(self, db: Session):
        self.db = db

    # Reservoir Data CRUD Operations
    def create_reservoir_data(self, data: ReservoirDataCreate, user_id: str, file_path: str, file_size: int) -> ReservoirData:
        """Create new reservoir data entry"""
        db_data = ReservoirData(
            id=str(uuid.uuid4()),
            name=data.name,
            description=data.description,
            data_type=data.data_type,
            file_path=file_path,
            file_size=file_size,
            metadata=data.metadata,
            location_data=data.location_data,
            time_range_start=data.time_range_start,
            time_range_end=data.time_range_end,
            uploaded_by=user_id,
            is_processed=False
        )
        self.db.add(db_data)
        self.db.commit()
        self.db.refresh(db_data)
        return db_data

    def get_reservoir_data(self, data_id: str) -> Optional[ReservoirData]:
        """Get reservoir data by ID"""
        return self.db.query(ReservoirData).filter(ReservoirData.id == data_id).first()

    def get_reservoir_data_list(
        self, 
        user_id: str = None,
        data_type: ReservoirDataType = None,
        is_processed: bool = None,
        skip: int = 0,
        limit: int = 50
    ) -> tuple[List[ReservoirData], int]:
        """Get list of reservoir data with filtering"""
        query = self.db.query(ReservoirData)
        
        if user_id:
            query = query.filter(ReservoirData.uploaded_by == user_id)
        if data_type:
            query = query.filter(ReservoirData.data_type == data_type)
        if is_processed is not None:
            query = query.filter(ReservoirData.is_processed == is_processed)
            
        total = query.count()
        items = query.order_by(desc(ReservoirData.created_at)).offset(skip).limit(limit).all()
        
        return items, total

    def update_reservoir_data(self, data_id: str, data: ReservoirDataUpdate) -> Optional[ReservoirData]:
        """Update reservoir data"""
        db_data = self.get_reservoir_data(data_id)
        if not db_data:
            return None
            
        update_dict = {k: v for k, v in data.dict(exclude_unset=True).items() if v is not None}
        update_dict['updated_at'] = datetime.utcnow()
        
        for key, value in update_dict.items():
            setattr(db_data, key, value)
            
        self.db.commit()
        self.db.refresh(db_data)
        return db_data

    def delete_reservoir_data(self, data_id: str) -> bool:
        """Delete reservoir data and associated file"""
        db_data = self.get_reservoir_data(data_id)
        if not db_data:
            return False
            
        # Delete associated file
        try:
            if os.path.exists(db_data.file_path):
                os.remove(db_data.file_path)
        except Exception as e:
            print(f"Error deleting file: {e}")
            
        # Delete from database
        self.db.delete(db_data)
        self.db.commit()
        return True

    # Reservoir Simulation CRUD Operations
    def create_reservoir_simulation(self, simulation: ReservoirSimulationCreate, user_id: str) -> ReservoirSimulation:
        """Create new reservoir simulation"""
        db_simulation = ReservoirSimulation(
            id=str(uuid.uuid4()),
            name=simulation.name,
            description=simulation.description,
            reservoir_data_id=simulation.reservoir_data_id,
            simulation_parameters=simulation.simulation_parameters,
            extraction_scenario=simulation.extraction_scenario,
            created_by=user_id,
            status=SimulationStatus.PENDING
        )
        self.db.add(db_simulation)
        self.db.commit()
        self.db.refresh(db_simulation)
        return db_simulation

    def get_reservoir_simulation(self, simulation_id: str) -> Optional[ReservoirSimulation]:
        """Get reservoir simulation by ID"""
        return self.db.query(ReservoirSimulation).filter(ReservoirSimulation.id == simulation_id).first()

    def get_simulation_list(
        self,
        user_id: str = None,
        reservoir_data_id: str = None,
        status: SimulationStatus = None,
        extraction_scenario: str = None,
        skip: int = 0,
        limit: int = 50
    ) -> tuple[List[ReservoirSimulation], int]:
        """Get list of simulations with filtering"""
        query = self.db.query(ReservoirSimulation)
        
        if user_id:
            query = query.filter(ReservoirSimulation.created_by == user_id)
        if reservoir_data_id:
            query = query.filter(ReservoirSimulation.reservoir_data_id == reservoir_data_id)
        if status:
            query = query.filter(ReservoirSimulation.status == status)
        if extraction_scenario:
            query = query.filter(ReservoirSimulation.extraction_scenario.ilike(f"%{extraction_scenario}%"))
            
        total = query.count()
        items = query.order_by(desc(ReservoirSimulation.created_at)).offset(skip).limit(limit).all()
        
        return items, total

    def update_reservoir_simulation(self, simulation_id: str, simulation: ReservoirSimulationUpdate) -> Optional[ReservoirSimulation]:
        """Update reservoir simulation"""
        db_simulation = self.get_reservoir_simulation(simulation_id)
        if not db_simulation:
            return None
            
        update_dict = {k: v for k, v in simulation.dict(exclude_unset=True).items() if v is not None}
        update_dict['updated_at'] = datetime.utcnow()
        
        for key, value in update_dict.items():
            setattr(db_simulation, key, value)
            
        self.db.commit()
        self.db.refresh(db_simulation)
        return db_simulation

    def start_simulation(self, simulation_id: str) -> Optional[ReservoirSimulation]:
        """Mark simulation as started"""
        db_simulation = self.get_reservoir_simulation(simulation_id)
        if not db_simulation:
            return None
            
        db_simulation.status = SimulationStatus.PROCESSING
        db_simulation.started_at = datetime.utcnow()
        db_simulation.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(db_simulation)
        return db_simulation

    def complete_simulation(self, simulation_id: str, results_summary: Dict[str, Any], visualization_data: Dict[str, Any], results_path: str = None) -> Optional[ReservoirSimulation]:
        """Mark simulation as completed with results"""
        db_simulation = self.get_reservoir_simulation(simulation_id)
        if not db_simulation:
            return None
            
        db_simulation.status = SimulationStatus.COMPLETED
        db_simulation.completed_at = datetime.utcnow()
        db_simulation.results_summary = results_summary
        db_simulation.visualization_data = visualization_data
        db_simulation.results_path = results_path
        db_simulation.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(db_simulation)
        return db_simulation

    def fail_simulation(self, simulation_id: str, error_message: str) -> Optional[ReservoirSimulation]:
        """Mark simulation as failed"""
        db_simulation = self.get_reservoir_simulation(simulation_id)
        if not db_simulation:
            return None
            
        db_simulation.status = SimulationStatus.FAILED
        db_simulation.error_message = error_message
        db_simulation.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(db_simulation)
        return db_simulation

    # Reservoir Forecast CRUD Operations
    def create_reservoir_forecast(self, forecast: ReservoirForecastCreate, user_id: str) -> ReservoirForecast:
        """Create new reservoir forecast"""
        db_forecast = ReservoirForecast(
            id=str(uuid.uuid4()),
            name=forecast.name,
            description=forecast.description,
            simulation_id=forecast.simulation_id,
            model_type=forecast.model_type,
            model_parameters=forecast.model_parameters,
            forecast_horizon_days=forecast.forecast_horizon_days,
            created_by=user_id,
            status=ForecastStatus.DRAFT,
            forecast_data={}  # Will be populated by ML service
        )
        self.db.add(db_forecast)
        self.db.commit()
        self.db.refresh(db_forecast)
        return db_forecast

    def get_reservoir_forecast(self, forecast_id: str) -> Optional[ReservoirForecast]:
        """Get reservoir forecast by ID"""
        return self.db.query(ReservoirForecast).filter(ReservoirForecast.id == forecast_id).first()

    def get_forecast_list(
        self,
        user_id: str = None,
        simulation_id: str = None,
        status: ForecastStatus = None,
        model_type: str = None,
        skip: int = 0,
        limit: int = 50
    ) -> tuple[List[ReservoirForecast], int]:
        """Get list of forecasts with filtering"""
        query = self.db.query(ReservoirForecast)
        
        if user_id:
            query = query.filter(ReservoirForecast.created_by == user_id)
        if simulation_id:
            query = query.filter(ReservoirForecast.simulation_id == simulation_id)
        if status:
            query = query.filter(ReservoirForecast.status == status)
        if model_type:
            query = query.filter(ReservoirForecast.model_type.ilike(f"%{model_type}%"))
            
        total = query.count()
        items = query.order_by(desc(ReservoirForecast.generated_at)).offset(skip).limit(limit).all()
        
        return items, total

    def update_reservoir_forecast(self, forecast_id: str, forecast: ReservoirForecastUpdate) -> Optional[ReservoirForecast]:
        """Update reservoir forecast"""
        db_forecast = self.get_reservoir_forecast(forecast_id)
        if not db_forecast:
            return None
            
        update_dict = {k: v for k, v in forecast.dict(exclude_unset=True).items() if v is not None}
        
        for key, value in update_dict.items():
            setattr(db_forecast, key, value)
            
        self.db.commit()
        self.db.refresh(db_forecast)
        return db_forecast

    def publish_forecast(self, forecast_id: str) -> Optional[ReservoirForecast]:
        """Publish a forecast"""
        db_forecast = self.get_reservoir_forecast(forecast_id)
        if not db_forecast:
            return None
            
        db_forecast.status = ForecastStatus.PUBLISHED
        db_forecast.published_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(db_forecast)
        return db_forecast

    # Reservoir Warning CRUD Operations
    def create_reservoir_warning(self, warning: ReservoirWarningCreate) -> ReservoirWarning:
        """Create new reservoir warning"""
        db_warning = ReservoirWarning(
            id=str(uuid.uuid4()),
            forecast_id=warning.forecast_id,
            warning_type=warning.warning_type,
            severity_level=warning.severity_level,
            title=warning.title,
            description=warning.description,
            trigger_conditions=warning.trigger_conditions,
            recommended_actions=warning.recommended_actions,
            predicted_occurrence_date=warning.predicted_occurrence_date,
            confidence_score=warning.confidence_score,
            is_acknowledged=False
        )
        self.db.add(db_warning)
        self.db.commit()
        self.db.refresh(db_warning)
        return db_warning

    def get_warning_list(
        self,
        forecast_id: str = None,
        severity_level: WarningLevel = None,
        is_acknowledged: bool = None,
        warning_type: str = None,
        skip: int = 0,
        limit: int = 50
    ) -> tuple[List[ReservoirWarning], int]:
        """Get list of warnings with filtering"""
        query = self.db.query(ReservoirWarning)
        
        if forecast_id:
            query = query.filter(ReservoirWarning.forecast_id == forecast_id)
        if severity_level:
            query = query.filter(ReservoirWarning.severity_level == severity_level)
        if is_acknowledged is not None:
            query = query.filter(ReservoirWarning.is_acknowledged == is_acknowledged)
        if warning_type:
            query = query.filter(ReservoirWarning.warning_type.ilike(f"%{warning_type}%"))
            
        total = query.count()
        items = query.order_by(desc(ReservoirWarning.created_at)).offset(skip).limit(limit).all()
        
        return items, total

    def acknowledge_warning(self, warning_id: str, user_id: str) -> Optional[ReservoirWarning]:
        """Acknowledge a warning"""
        db_warning = self.db.query(ReservoirWarning).filter(ReservoirWarning.id == warning_id).first()
        if not db_warning:
            return None
            
        db_warning.is_acknowledged = True
        db_warning.acknowledged_by = user_id
        db_warning.acknowledged_at = datetime.utcnow()
        db_warning.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(db_warning)
        return db_warning

    def acknowledge_multiple_warnings(self, warning_ids: List[str], user_id: str) -> List[ReservoirWarning]:
        """Acknowledge multiple warnings"""
        warnings = self.db.query(ReservoirWarning).filter(ReservoirWarning.id.in_(warning_ids)).all()
        
        for warning in warnings:
            warning.is_acknowledged = True
            warning.acknowledged_by = user_id
            warning.acknowledged_at = datetime.utcnow()
            warning.updated_at = datetime.utcnow()
            
        self.db.commit()
        return warnings

    # Prediction Session Operations
    def create_prediction_session(self, session: PredictionSessionCreate, user_id: str) -> PredictionSession:
        """Create new prediction session"""
        db_session = PredictionSession(
            id=str(uuid.uuid4()),
            session_name=session.session_name,
            description=session.description,
            data_sources=session.data_sources,
            analysis_parameters=session.analysis_parameters,
            preprocessing_steps=session.preprocessing_steps,
            ml_pipeline_config=session.ml_pipeline_config,
            feature_engineering_steps=session.feature_engineering_steps,
            model_selection_criteria=session.model_selection_criteria,
            created_by=user_id
        )
        self.db.add(db_session)
        self.db.commit()
        self.db.refresh(db_session)
        return db_session

    def get_prediction_session(self, session_id: str) -> Optional[PredictionSession]:
        """Get prediction session by ID"""
        return self.db.query(PredictionSession).filter(PredictionSession.id == session_id).first()

    def complete_prediction_session(
        self, 
        session_id: str, 
        session_results: Dict[str, Any],
        forecast_ids: List[str] = None,
        warning_ids: List[str] = None,
        duration_seconds: int = None
    ) -> Optional[PredictionSession]:
        """Complete prediction session with results"""
        db_session = self.get_prediction_session(session_id)
        if not db_session:
            return None
            
        db_session.session_results = session_results
        db_session.generated_forecasts = forecast_ids or []
        db_session.generated_warnings = warning_ids or []
        db_session.completed_at = datetime.utcnow()
        db_session.duration_seconds = duration_seconds
        
        self.db.commit()
        self.db.refresh(db_session)
        return db_session

    # Utility Methods
    def get_data_for_analysis(self, data_ids: List[str]) -> List[ReservoirData]:
        """Get reservoir data for analysis"""
        return self.db.query(ReservoirData).filter(
            and_(
                ReservoirData.id.in_(data_ids),
                ReservoirData.is_processed == True
            )
        ).all()

    def get_simulation_comparison_data(self, simulation_ids: List[str]) -> List[ReservoirSimulation]:
        """Get simulations for comparison"""
        return self.db.query(ReservoirSimulation).filter(
            and_(
                ReservoirSimulation.id.in_(simulation_ids),
                ReservoirSimulation.status == SimulationStatus.COMPLETED
            )
        ).all()

    def get_unacknowledged_warnings(self, user_id: str = None) -> List[ReservoirWarning]:
        """Get unacknowledged warnings, optionally filtered by user"""
        query = self.db.query(ReservoirWarning).filter(ReservoirWarning.is_acknowledged == False)
        
        if user_id:
            # Get warnings from forecasts created by the user
            query = query.join(ReservoirForecast).filter(ReservoirForecast.created_by == user_id)
            
        return query.order_by(desc(ReservoirWarning.severity_level), desc(ReservoirWarning.created_at)).all()

    def get_recent_forecasts(self, user_id: str = None, days: int = 30) -> List[ReservoirForecast]:
        """Get recent forecasts"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        query = self.db.query(ReservoirForecast).filter(ReservoirForecast.generated_at >= cutoff_date)
        
        if user_id:
            query = query.filter(ReservoirForecast.created_by == user_id)
            
        return query.order_by(desc(ReservoirForecast.generated_at)).all()
