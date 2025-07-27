from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
import json

from app.database.config import get_db
from app.auth.dependencies import get_current_user
from app.models.user import User
from app.schemas.seismic import (
    SeismicDataset, SeismicDatasetCreate, SeismicDatasetUpdate,
    SeismicInterpretation, SeismicInterpretationCreate, SeismicInterpretationUpdate,
    SeismicAnalysis, SeismicAnalysisCreate, SeismicAnalysisUpdate,
    SeismicSession, SeismicSessionCreate, SeismicSessionUpdate,
    SeismicUploadResponse, ProcessingParameters, VisualizationSettings
)
from app.services.seismic_service import (
    SeismicDataService, SeismicAnalysisService, 
    SeismicInterpretationService, SeismicVisualizationService
)

router = APIRouter(prefix="/api/v1/seismic", tags=["seismic"])

# Initialize services
data_service = SeismicDataService()
analysis_service = SeismicAnalysisService()
interpretation_service = SeismicInterpretationService()
visualization_service = SeismicVisualizationService()

# Dataset endpoints
@router.post("/datasets/upload", response_model=SeismicUploadResponse)
async def upload_seismic_dataset(
    file: UploadFile = File(...),
    name: str = Form(...),
    description: Optional[str] = Form(None),
    file_format: str = Form(...),
    acquisition_date: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Upload a new seismic dataset"""
    
    # Parse acquisition date if provided
    from datetime import datetime
    parsed_date = None
    if acquisition_date:
        try:
            parsed_date = datetime.fromisoformat(acquisition_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format")
    
    dataset_create = SeismicDatasetCreate(
        name=name,
        description=description,
        file_format=file_format,
        acquisition_date=parsed_date
    )
    
    dataset = await data_service.upload_seismic_file(
        file=file,
        dataset_create=dataset_create,
        user_id=current_user.id,
        db=db
    )
    
    return SeismicUploadResponse(
        dataset_id=dataset.id,
        message="Dataset uploaded successfully",
        file_info={
            "filename": file.filename,
            "size": dataset.file_size,
            "format": dataset.file_format,
            "trace_count": dataset.trace_count
        }
    )

@router.get("/datasets", response_model=List[SeismicDataset])
def get_seismic_datasets(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    user_only: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get list of seismic datasets"""
    user_id = current_user.id if user_only else None
    return data_service.get_datasets(db=db, user_id=user_id, skip=skip, limit=limit)

@router.get("/datasets/{dataset_id}", response_model=SeismicDataset)
def get_seismic_dataset(
    dataset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific seismic dataset"""
    dataset = data_service.get_dataset(db=db, dataset_id=dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return dataset

@router.put("/datasets/{dataset_id}", response_model=SeismicDataset)
def update_seismic_dataset(
    dataset_id: int,
    dataset_update: SeismicDatasetUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update seismic dataset metadata"""
    dataset = data_service.update_dataset(db=db, dataset_id=dataset_id, dataset_update=dataset_update)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return dataset

@router.delete("/datasets/{dataset_id}")
def delete_seismic_dataset(
    dataset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a seismic dataset"""
    success = data_service.delete_dataset(db=db, dataset_id=dataset_id)
    if not success:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return {"message": "Dataset deleted successfully"}

# Analysis endpoints
@router.post("/analysis", response_model=SeismicAnalysis)
def create_seismic_analysis(
    analysis_create: SeismicAnalysisCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new seismic analysis job"""
    # Verify dataset exists
    dataset = data_service.get_dataset(db=db, dataset_id=analysis_create.dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    return analysis_service.create_analysis(
        db=db, 
        analysis_create=analysis_create,
        user_id=current_user.id
    )

@router.get("/analysis/{analysis_id}", response_model=SeismicAnalysis)
def get_seismic_analysis(
    analysis_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get seismic analysis status and results"""
    from app.models.seismic import SeismicAnalysis as SeismicAnalysisModel
    
    analysis = db.query(SeismicAnalysisModel).filter(
        SeismicAnalysisModel.id == analysis_id
    ).first()
    
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    return analysis

@router.get("/datasets/{dataset_id}/analyses", response_model=List[SeismicAnalysis])
def get_dataset_analyses(
    dataset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all analyses for a dataset"""
    from app.models.seismic import SeismicAnalysis as SeismicAnalysisModel
    
    # Verify dataset exists
    dataset = data_service.get_dataset(db=db, dataset_id=dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    return db.query(SeismicAnalysisModel).filter(
        SeismicAnalysisModel.dataset_id == dataset_id
    ).all()

# Interpretation endpoints
@router.post("/interpretations", response_model=SeismicInterpretation)
def create_seismic_interpretation(
    interpretation_create: SeismicInterpretationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new seismic interpretation"""
    # Verify dataset exists
    dataset = data_service.get_dataset(db=db, dataset_id=interpretation_create.dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    return interpretation_service.create_interpretation(
        db=db,
        interpretation_create=interpretation_create,
        user_id=current_user.id
    )

@router.get("/datasets/{dataset_id}/interpretations", response_model=List[SeismicInterpretation])
def get_dataset_interpretations(
    dataset_id: int,
    interpretation_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get interpretations for a dataset"""
    # Verify dataset exists
    dataset = data_service.get_dataset(db=db, dataset_id=dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    return interpretation_service.get_interpretations(
        db=db,
        dataset_id=dataset_id,
        interpretation_type=interpretation_type
    )

@router.put("/interpretations/{interpretation_id}", response_model=SeismicInterpretation)
def update_seismic_interpretation(
    interpretation_id: int,
    interpretation_update: SeismicInterpretationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a seismic interpretation"""
    interpretation = interpretation_service.update_interpretation(
        db=db,
        interpretation_id=interpretation_id,
        interpretation_update=interpretation_update
    )
    
    if not interpretation:
        raise HTTPException(status_code=404, detail="Interpretation not found")
    
    return interpretation

# Visualization endpoints
@router.post("/datasets/{dataset_id}/visualization")
async def generate_3d_visualization(
    dataset_id: int,
    settings: VisualizationSettings,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Generate 3D visualization for seismic dataset"""
    return await visualization_service.generate_3d_visualization(
        dataset_id=dataset_id,
        settings=settings,
        db=db
    )

@router.get("/datasets/{dataset_id}/slice")
async def get_seismic_slice(
    dataset_id: int,
    slice_type: str = Query(..., regex="^(inline|crossline|time)$"),
    slice_position: float = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a 2D slice from 3D seismic data"""
    # Verify dataset exists
    dataset = data_service.get_dataset(db=db, dataset_id=dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    # This would implement slice extraction logic
    return {
        "dataset_id": dataset_id,
        "slice_type": slice_type,
        "slice_position": slice_position,
        "image_url": f"/api/v1/seismic/datasets/{dataset_id}/slice/{slice_type}/{slice_position}",
        "metadata": {
            "dimensions": [dataset.max_inline - dataset.min_inline + 1, 
                         dataset.max_crossline - dataset.min_crossline + 1],
            "sample_rate": dataset.sample_rate
        }
    }

# Session management endpoints
@router.post("/sessions", response_model=SeismicSession)
def create_seismic_session(
    session_create: SeismicSessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new seismic analysis session"""
    from app.models.seismic import SeismicSession as SeismicSessionModel
    
    session = SeismicSessionModel(
        user_id=current_user.id,
        session_name=session_create.session_name,
        description=session_create.description,
        datasets=session_create.datasets,
        viewport_settings=session_create.viewport_settings,
        display_settings=session_create.display_settings,
        is_shared=session_create.is_shared,
        shared_with=session_create.shared_with
    )
    
    db.add(session)
    db.commit()
    db.refresh(session)
    
    return session

@router.get("/sessions", response_model=List[SeismicSession])
def get_seismic_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get user's seismic analysis sessions"""
    from app.models.seismic import SeismicSession as SeismicSessionModel
    
    return db.query(SeismicSessionModel).filter(
        SeismicSessionModel.user_id == current_user.id
    ).all()

@router.get("/sessions/{session_id}", response_model=SeismicSession)
def get_seismic_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific seismic session"""
    from app.models.seismic import SeismicSession as SeismicSessionModel
    
    session = db.query(SeismicSessionModel).filter(
        SeismicSessionModel.id == session_id
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Check access permissions
    if session.user_id != current_user.id and not session.is_shared:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Update last accessed time
    from datetime import datetime
    session.last_accessed = datetime.now()
    db.commit()
    
    return session

# Processing algorithms endpoints
@router.post("/algorithms/noise-reduction")
async def apply_noise_reduction(
    dataset_id: int,
    parameters: ProcessingParameters,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Apply noise reduction to seismic data"""
    analysis_create = SeismicAnalysisCreate(
        dataset_id=dataset_id,
        name=f"Noise Reduction - {parameters.filter_type}",
        description="Automated noise reduction processing",
        analysis_type="noise_reduction",
        parameters=parameters.dict()
    )
    
    return analysis_service.create_analysis(
        db=db,
        analysis_create=analysis_create,
        user_id=current_user.id
    )

@router.post("/algorithms/migration")
async def apply_migration(
    dataset_id: int,
    parameters: ProcessingParameters,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Apply seismic migration"""
    analysis_create = SeismicAnalysisCreate(
        dataset_id=dataset_id,
        name=f"Migration - {parameters.migration_type}",
        description="Seismic migration processing",
        analysis_type="migration",
        parameters=parameters.dict()
    )
    
    return analysis_service.create_analysis(
        db=db,
        analysis_create=analysis_create,
        user_id=current_user.id
    )

@router.post("/algorithms/attributes")
async def compute_attributes(
    dataset_id: int,
    parameters: ProcessingParameters,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Compute seismic attributes"""
    analysis_create = SeismicAnalysisCreate(
        dataset_id=dataset_id,
        name=f"Attributes - {parameters.attribute_type}",
        description="Seismic attribute computation",
        analysis_type="attribute_analysis",
        parameters=parameters.dict()
    )
    
    return analysis_service.create_analysis(
        db=db,
        analysis_create=analysis_create,
        user_id=current_user.id
    )

# Data export endpoints
@router.get("/datasets/{dataset_id}/export")
async def export_seismic_data(
    dataset_id: int,
    export_format: str = Query(..., regex="^(segy|hdf5|csv)$"),
    include_interpretations: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Export seismic data in various formats"""
    # Verify dataset exists
    dataset = data_service.get_dataset(db=db, dataset_id=dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    export_info = {
        "dataset_id": dataset_id,
        "export_format": export_format,
        "include_interpretations": include_interpretations,
        "download_url": f"/api/v1/seismic/datasets/{dataset_id}/download/{export_format}",
        "estimated_size": dataset.file_size,
        "processing_time": "2-5 minutes"
    }
    
    return export_info
