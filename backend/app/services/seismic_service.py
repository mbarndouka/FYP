import os
import numpy as np
import segyio
import h5py
import json
import asyncio
from typing import List, Optional, Dict, Any, Tuple
from pathlib import Path
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from fastapi import HTTPException, UploadFile
import aiofiles

from app.models.seismic import (
    SeismicDataset, SeismicInterpretation, SeismicAnalysis, 
    SeismicAttribute, SeismicSession
)
from app.schemas.seismic import (
    SeismicDatasetCreate, SeismicDatasetUpdate,
    SeismicInterpretationCreate, SeismicInterpretationUpdate,
    SeismicAnalysisCreate, SeismicAnalysisUpdate,
    ProcessingParameters, VisualizationSettings
)

class SeismicDataService:
    def __init__(self, upload_dir: str = "uploads/seismic"):
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        
    async def upload_seismic_file(
        self, 
        file: UploadFile, 
        dataset_create: SeismicDatasetCreate,
        user_id: int,
        db: Session
    ) -> SeismicDataset:
        """Upload and process a seismic data file"""
        
        # Validate file format
        if not self._is_valid_seismic_format(file.filename):
            raise HTTPException(
                status_code=400, 
                detail="Unsupported file format. Supported formats: .sgy, .segy, .h5, .hdf5"
            )
        
        # Create unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_extension = Path(file.filename).suffix
        unique_filename = f"{timestamp}_{file.filename}"
        file_path = self.upload_dir / unique_filename
        
        # Save file
        async with aiofiles.open(file_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
        
        # Extract metadata from file
        try:
            metadata = await self._extract_seismic_metadata(file_path, file_extension)
        except Exception as e:
            # Clean up file if metadata extraction fails
            file_path.unlink(missing_ok=True)
            raise HTTPException(
                status_code=400,
                detail=f"Error processing seismic file: {str(e)}"
            )
        
        # Create database record
        dataset = SeismicDataset(
            name=dataset_create.name,
            description=dataset_create.description,
            file_path=str(file_path),
            file_format=dataset_create.file_format,
            file_size=len(content),
            acquisition_date=dataset_create.acquisition_date,
            uploaded_by=user_id,
            **metadata
        )
        
        db.add(dataset)
        db.commit()
        db.refresh(dataset)
        
        return dataset
    
    def get_datasets(
        self, 
        db: Session, 
        user_id: Optional[int] = None,
        skip: int = 0, 
        limit: int = 100
    ) -> List[SeismicDataset]:
        """Get seismic datasets with optional user filtering"""
        query = db.query(SeismicDataset)
        
        if user_id:
            query = query.filter(SeismicDataset.uploaded_by == user_id)
            
        return query.offset(skip).limit(limit).all()
    
    def get_dataset(self, db: Session, dataset_id: int) -> Optional[SeismicDataset]:
        """Get a specific seismic dataset"""
        return db.query(SeismicDataset).filter(SeismicDataset.id == dataset_id).first()
    
    def update_dataset(
        self, 
        db: Session, 
        dataset_id: int, 
        dataset_update: SeismicDatasetUpdate
    ) -> Optional[SeismicDataset]:
        """Update dataset metadata"""
        dataset = self.get_dataset(db, dataset_id)
        if not dataset:
            return None
            
        update_data = dataset_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(dataset, field, value)
        
        db.commit()
        db.refresh(dataset)
        return dataset
    
    def delete_dataset(self, db: Session, dataset_id: int) -> bool:
        """Delete dataset and associated file"""
        dataset = self.get_dataset(db, dataset_id)
        if not dataset:
            return False
        
        # Delete file
        file_path = Path(dataset.file_path)
        file_path.unlink(missing_ok=True)
        
        # Delete database record
        db.delete(dataset)
        db.commit()
        return True
    
    async def _extract_seismic_metadata(self, file_path: Path, file_extension: str) -> Dict[str, Any]:
        """Extract metadata from seismic files"""
        metadata = {}
        
        if file_extension.lower() in ['.sgy', '.segy']:
            metadata = await self._extract_segy_metadata(file_path)
        elif file_extension.lower() in ['.h5', '.hdf5']:
            metadata = await self._extract_hdf5_metadata(file_path)
        
        return metadata
    
    async def _extract_segy_metadata(self, file_path: Path) -> Dict[str, Any]:
        """Extract metadata from SEG-Y files"""
        try:
            with segyio.open(str(file_path), "r") as segy:
                metadata = {
                    "min_inline": int(segy.ilines[0]),
                    "max_inline": int(segy.ilines[-1]),
                    "min_crossline": int(segy.xlines[0]),
                    "max_crossline": int(segy.xlines[-1]),
                    "min_time": float(segy.samples[0]),
                    "max_time": float(segy.samples[-1]),
                    "sample_rate": float(segy.bin[segyio.BinField.Interval] / 1000),  # Convert to ms
                    "trace_count": len(segy.trace),
                    "inline_increment": int(segy.ilines[1] - segy.ilines[0]) if len(segy.ilines) > 1 else 1,
                    "crossline_increment": int(segy.xlines[1] - segy.xlines[0]) if len(segy.xlines) > 1 else 1,
                }
                return metadata
        except Exception as e:
            raise Exception(f"Error reading SEG-Y file: {str(e)}")
    
    async def _extract_hdf5_metadata(self, file_path: Path) -> Dict[str, Any]:
        """Extract metadata from HDF5 files"""
        try:
            with h5py.File(str(file_path), 'r') as hdf:
                # This is a generic HDF5 reader - adjust based on your HDF5 structure
                metadata = {
                    "trace_count": len(list(hdf.keys())),
                    "sample_rate": 2.0,  # Default value, should be read from file
                }
                
                # Try to extract spatial information if available
                if 'inline' in hdf.attrs:
                    metadata["min_inline"] = int(hdf.attrs['min_inline'])
                    metadata["max_inline"] = int(hdf.attrs['max_inline'])
                
                return metadata
        except Exception as e:
            raise Exception(f"Error reading HDF5 file: {str(e)}")
    
    def _is_valid_seismic_format(self, filename: str) -> bool:
        """Check if the file format is supported"""
        valid_extensions = {'.sgy', '.segy', '.h5', '.hdf5'}
        return Path(filename).suffix.lower() in valid_extensions

class SeismicAnalysisService:
    def __init__(self):
        self.processing_dir = Path("processing/seismic")
        self.processing_dir.mkdir(parents=True, exist_ok=True)
    
    def create_analysis(
        self, 
        db: Session, 
        analysis_create: SeismicAnalysisCreate,
        user_id: int
    ) -> SeismicAnalysis:
        """Create a new seismic analysis job"""
        analysis = SeismicAnalysis(
            dataset_id=analysis_create.dataset_id,
            name=analysis_create.name,
            description=analysis_create.description,
            analysis_type=analysis_create.analysis_type,
            parameters=analysis_create.parameters,
            analyst_id=user_id,
            started_at=datetime.now()
        )
        
        db.add(analysis)
        db.commit()
        db.refresh(analysis)
        
        # Start background processing
        asyncio.create_task(self._process_analysis(analysis.id, db))
        
        return analysis
    
    async def _process_analysis(self, analysis_id: int, db: Session):
        """Background processing of seismic analysis"""
        analysis = db.query(SeismicAnalysis).filter(SeismicAnalysis.id == analysis_id).first()
        if not analysis:
            return
        
        try:
            analysis.status = "running"
            db.commit()
            
            # Get dataset
            dataset = db.query(SeismicDataset).filter(SeismicDataset.id == analysis.dataset_id).first()
            if not dataset:
                raise Exception("Dataset not found")
            
            # Process based on analysis type
            if analysis.analysis_type == "noise_reduction":
                result = await self._apply_noise_reduction(dataset.file_path, analysis.parameters)
            elif analysis.analysis_type == "migration":
                result = await self._apply_migration(dataset.file_path, analysis.parameters)
            elif analysis.analysis_type == "attribute_analysis":
                result = await self._compute_attributes(dataset.file_path, analysis.parameters)
            else:
                raise Exception(f"Unsupported analysis type: {analysis.analysis_type}")
            
            # Save results
            result_file = self.processing_dir / f"analysis_{analysis_id}_result.h5"
            await self._save_analysis_result(result, result_file)
            
            # Update analysis record
            analysis.status = "completed"
            analysis.result_file_path = str(result_file)
            analysis.completed_at = datetime.now()
            analysis.progress = 100.0
            
        except Exception as e:
            analysis.status = "failed"
            analysis.error_message = str(e)
            analysis.progress = 0.0
        
        finally:
            db.commit()
    
    async def _apply_noise_reduction(self, file_path: str, parameters: Dict[str, Any]) -> np.ndarray:
        """Apply noise reduction algorithms"""
        # Placeholder for noise reduction implementation
        # This would use scipy.signal filters
        pass
    
    async def _apply_migration(self, file_path: str, parameters: Dict[str, Any]) -> np.ndarray:
        """Apply seismic migration"""
        # Placeholder for migration implementation
        pass
    
    async def _compute_attributes(self, file_path: str, parameters: Dict[str, Any]) -> np.ndarray:
        """Compute seismic attributes"""
        # Placeholder for attribute computation
        pass
    
    async def _save_analysis_result(self, result: np.ndarray, file_path: Path):
        """Save analysis results to file"""
        with h5py.File(str(file_path), 'w') as f:
            f.create_dataset('data', data=result)

class SeismicInterpretationService:
    def create_interpretation(
        self, 
        db: Session, 
        interpretation_create: SeismicInterpretationCreate,
        user_id: int
    ) -> SeismicInterpretation:
        """Create a new seismic interpretation"""
        interpretation = SeismicInterpretation(
            dataset_id=interpretation_create.dataset_id,
            name=interpretation_create.name,
            description=interpretation_create.description,
            interpretation_type=interpretation_create.interpretation_type,
            geometry_data=interpretation_create.geometry_data,
            color=interpretation_create.color,
            opacity=interpretation_create.opacity,
            thickness=interpretation_create.thickness,
            confidence_level=interpretation_create.confidence_level,
            quality_score=interpretation_create.quality_score,
            interpreter_id=user_id
        )
        
        db.add(interpretation)
        db.commit()
        db.refresh(interpretation)
        
        return interpretation
    
    def get_interpretations(
        self, 
        db: Session, 
        dataset_id: int,
        interpretation_type: Optional[str] = None
    ) -> List[SeismicInterpretation]:
        """Get interpretations for a dataset"""
        query = db.query(SeismicInterpretation).filter(
            SeismicInterpretation.dataset_id == dataset_id,
            SeismicInterpretation.is_active == True
        )
        
        if interpretation_type:
            query = query.filter(SeismicInterpretation.interpretation_type == interpretation_type)
        
        return query.all()
    
    def update_interpretation(
        self, 
        db: Session, 
        interpretation_id: int,
        interpretation_update: SeismicInterpretationUpdate
    ) -> Optional[SeismicInterpretation]:
        """Update an interpretation"""
        interpretation = db.query(SeismicInterpretation).filter(
            SeismicInterpretation.id == interpretation_id
        ).first()
        
        if not interpretation:
            return None
        
        update_data = interpretation_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(interpretation, field, value)
        
        db.commit()
        db.refresh(interpretation)
        return interpretation

class SeismicVisualizationService:
    def __init__(self):
        self.cache_dir = Path("cache/visualization")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    async def generate_3d_visualization(
        self, 
        dataset_id: int, 
        settings: VisualizationSettings,
        db: Session
    ) -> Dict[str, Any]:
        """Generate 3D visualization data"""
        dataset = db.query(SeismicDataset).filter(SeismicDataset.id == dataset_id).first()
        if not dataset:
            raise HTTPException(status_code=404, detail="Dataset not found")
        
        # Load seismic data
        data = await self._load_seismic_data(dataset.file_path)
        
        # Generate visualization
        viz_data = {
            "dataset_id": dataset_id,
            "dimensions": data.shape,
            "data_range": [float(data.min()), float(data.max())],
            "spatial_info": {
                "inline_range": [dataset.min_inline, dataset.max_inline],
                "crossline_range": [dataset.min_crossline, dataset.max_crossline],
                "time_range": [dataset.min_time, dataset.max_time]
            },
            "visualization_url": f"/api/v1/seismic/visualization/{dataset_id}",
            "settings": settings.dict()
        }
        
        return viz_data
    
    async def _load_seismic_data(self, file_path: str) -> np.ndarray:
        """Load seismic data from file"""
        file_ext = Path(file_path).suffix.lower()
        
        if file_ext in ['.sgy', '.segy']:
            return await self._load_segy_data(file_path)
        elif file_ext in ['.h5', '.hdf5']:
            return await self._load_hdf5_data(file_path)
        else:
            raise Exception(f"Unsupported file format: {file_ext}")
    
    async def _load_segy_data(self, file_path: str) -> np.ndarray:
        """Load data from SEG-Y file"""
        with segyio.open(file_path, "r") as segy:
            data = segyio.tools.cube(segy)
            return data
    
    async def _load_hdf5_data(self, file_path: str) -> np.ndarray:
        """Load data from HDF5 file"""
        with h5py.File(file_path, 'r') as f:
            # Adjust based on your HDF5 structure
            data = f['data'][:]
            return data
