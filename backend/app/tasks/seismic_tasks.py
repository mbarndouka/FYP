from celery import current_task
from app.celery_app import celery_app
from app.database.config import SessionLocal
from app.models.seismic import SeismicAnalysis, SeismicDataset
from app.utils.seismic_visualization import Seismic3DVisualizer, SeismicProcessingAlgorithms
import numpy as np
import h5py
import segyio
from pathlib import Path
from datetime import datetime
import traceback
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@celery_app.task(bind=True)
def process_seismic_analysis(self, analysis_id: int):
    """Background task for processing seismic analysis"""
    db = SessionLocal()
    
    try:
        # Update task status
        current_task.update_state(state="PROGRESS", meta={"progress": 0, "status": "Starting analysis"})
        
        # Get analysis record
        analysis = db.query(SeismicAnalysis).filter(SeismicAnalysis.id == analysis_id).first()
        if not analysis:
            raise Exception(f"Analysis {analysis_id} not found")
        
        # Update analysis status
        analysis.status = "running"
        analysis.started_at = datetime.now()
        db.commit()
        
        # Get dataset
        dataset = db.query(SeismicDataset).filter(SeismicDataset.id == analysis.dataset_id).first()
        if not dataset:
            raise Exception("Dataset not found")
        
        current_task.update_state(state="PROGRESS", meta={"progress": 10, "status": "Loading data"})
        
        # Load seismic data
        data = load_seismic_data(dataset.file_path)
        
        current_task.update_state(state="PROGRESS", meta={"progress": 30, "status": "Processing data"})
        
        # Process based on analysis type
        if analysis.analysis_type == "noise_reduction":
            result = apply_noise_reduction(data, analysis.parameters or {})
        elif analysis.analysis_type == "migration":
            result = apply_migration(data, analysis.parameters or {})
        elif analysis.analysis_type == "attribute_analysis":
            result = compute_attributes(data, analysis.parameters or {})
        else:
            raise Exception(f"Unsupported analysis type: {analysis.analysis_type}")
        
        current_task.update_state(state="PROGRESS", meta={"progress": 80, "status": "Saving results"})
        
        # Save results
        result_dir = Path("processing/seismic/results")
        result_dir.mkdir(parents=True, exist_ok=True)
        result_file = result_dir / f"analysis_{analysis_id}_result.h5"
        
        save_analysis_result(result, result_file)
        
        # Update analysis record
        analysis.status = "completed"
        analysis.result_file_path = str(result_file)
        analysis.completed_at = datetime.now()
        analysis.progress = 100.0
        
        # Calculate processing time
        if analysis.started_at:
            processing_time = (analysis.completed_at - analysis.started_at).total_seconds()
            analysis.processing_time = processing_time
        
        db.commit()
        
        current_task.update_state(
            state="SUCCESS", 
            meta={"progress": 100, "status": "Analysis completed", "result_file": str(result_file)}
        )
        
        return {"status": "completed", "result_file": str(result_file)}
        
    except Exception as e:
        logger.error(f"Error processing analysis {analysis_id}: {str(e)}")
        logger.error(traceback.format_exc())
        
        # Update analysis record with error
        if 'analysis' in locals():
            analysis.status = "failed"
            analysis.error_message = str(e)
            analysis.progress = 0.0
            db.commit()
        
        current_task.update_state(
            state="FAILURE",
            meta={"progress": 0, "status": f"Analysis failed: {str(e)}"}
        )
        
        raise e
    
    finally:
        db.close()

@celery_app.task(bind=True)
def generate_visualization(self, dataset_id: int, visualization_type: str, parameters: dict):
    """Background task for generating 3D visualizations"""
    db = SessionLocal()
    
    try:
        current_task.update_state(state="PROGRESS", meta={"progress": 0, "status": "Loading dataset"})
        
        # Get dataset
        dataset = db.query(SeismicDataset).filter(SeismicDataset.id == dataset_id).first()
        if not dataset:
            raise Exception("Dataset not found")
        
        current_task.update_state(state="PROGRESS", meta={"progress": 20, "status": "Loading seismic data"})
        
        # Load data
        data = load_seismic_data(dataset.file_path)
        
        current_task.update_state(state="PROGRESS", meta={"progress": 50, "status": "Generating visualization"})
        
        # Create visualizer
        visualizer = Seismic3DVisualizer()
        
        # Generate visualization based on type
        if visualization_type == "3d_volume":
            result = visualizer.create_interactive_3d_plot(data, opacity=parameters.get("opacity", 0.1))
        elif visualization_type == "slice":
            slice_type = parameters.get("slice_type", "inline")
            position = parameters.get("position", data.shape[0] // 2)
            result = visualizer.create_slice_visualization(data, slice_type, position)
        elif visualization_type == "multi_view":
            inline_pos = parameters.get("inline_pos", data.shape[0] // 2)
            crossline_pos = parameters.get("crossline_pos", data.shape[1] // 2)
            time_pos = parameters.get("time_pos", data.shape[2] // 2)
            result = visualizer.create_multi_view_dashboard(data, inline_pos, crossline_pos, time_pos)
        else:
            raise Exception(f"Unsupported visualization type: {visualization_type}")
        
        current_task.update_state(state="PROGRESS", meta={"progress": 90, "status": "Saving visualization"})
        
        # Save visualization
        viz_dir = Path("processing/seismic/visualizations")
        viz_dir.mkdir(parents=True, exist_ok=True)
        viz_file = viz_dir / f"viz_{dataset_id}_{visualization_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        
        if isinstance(result, str):
            with open(viz_file, 'w') as f:
                f.write(result)
        else:
            # Handle other result types (e.g., Plotly figures)
            if hasattr(result, 'to_html'):
                result.to_html(str(viz_file))
        
        current_task.update_state(
            state="SUCCESS",
            meta={"progress": 100, "status": "Visualization completed", "file": str(viz_file)}
        )
        
        return {"status": "completed", "visualization_file": str(viz_file)}
        
    except Exception as e:
        logger.error(f"Error generating visualization for dataset {dataset_id}: {str(e)}")
        logger.error(traceback.format_exc())
        
        current_task.update_state(
            state="FAILURE",
            meta={"progress": 0, "status": f"Visualization failed: {str(e)}"}
        )
        
        raise e
    
    finally:
        db.close()

@celery_app.task(bind=True)
def compute_seismic_attributes(self, dataset_id: int, attribute_types: list):
    """Background task for computing seismic attributes"""
    db = SessionLocal()
    
    try:
        current_task.update_state(state="PROGRESS", meta={"progress": 0, "status": "Loading dataset"})
        
        # Get dataset
        dataset = db.query(SeismicDataset).filter(SeismicDataset.id == dataset_id).first()
        if not dataset:
            raise Exception("Dataset not found")
        
        # Load data
        data = load_seismic_data(dataset.file_path)
        
        results = {}
        total_attributes = len(attribute_types)
        
        for i, attr_type in enumerate(attribute_types):
            progress = int((i / total_attributes) * 80) + 10
            current_task.update_state(
                state="PROGRESS", 
                meta={"progress": progress, "status": f"Computing {attr_type} attribute"}
            )
            
            if attr_type == "coherence":
                result = SeismicProcessingAlgorithms.compute_coherence_attribute(data)
            elif attr_type == "amplitude_envelope":
                result = SeismicProcessingAlgorithms.compute_amplitude_envelope(data)
            elif attr_type == "agc":
                result = SeismicProcessingAlgorithms.apply_agc(data)
            else:
                logger.warning(f"Unknown attribute type: {attr_type}")
                continue
            
            # Save attribute
            attr_dir = Path("processing/seismic/attributes")
            attr_dir.mkdir(parents=True, exist_ok=True)
            attr_file = attr_dir / f"attr_{dataset_id}_{attr_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.h5"
            
            save_analysis_result(result, attr_file)
            results[attr_type] = str(attr_file)
        
        current_task.update_state(
            state="SUCCESS",
            meta={"progress": 100, "status": "Attributes computed", "results": results}
        )
        
        return {"status": "completed", "attribute_files": results}
        
    except Exception as e:
        logger.error(f"Error computing attributes for dataset {dataset_id}: {str(e)}")
        logger.error(traceback.format_exc())
        
        current_task.update_state(
            state="FAILURE",
            meta={"progress": 0, "status": f"Attribute computation failed: {str(e)}"}
        )
        
        raise e
    
    finally:
        db.close()

# Helper functions
def load_seismic_data(file_path: str) -> np.ndarray:
    """Load seismic data from file"""
    file_ext = Path(file_path).suffix.lower()
    
    if file_ext in ['.sgy', '.segy']:
        with segyio.open(file_path, "r") as segy:
            data = segyio.tools.cube(segy)
            return data
    elif file_ext in ['.h5', '.hdf5']:
        with h5py.File(file_path, 'r') as f:
            # Adjust based on your HDF5 structure
            data = f['data'][:]
            return data
    else:
        raise ValueError(f"Unsupported file format: {file_ext}")

def apply_noise_reduction(data: np.ndarray, parameters: dict) -> np.ndarray:
    """Apply noise reduction algorithms"""
    filter_type = parameters.get("filter_type", "bandpass")
    
    if filter_type == "bandpass":
        low_freq = parameters.get("low_frequency", 5.0)
        high_freq = parameters.get("high_frequency", 80.0)
        sample_rate = parameters.get("sample_rate", 4.0)
        
        return SeismicProcessingAlgorithms.apply_bandpass_filter(
            data, low_freq, high_freq, sample_rate
        )
    else:
        raise ValueError(f"Unsupported filter type: {filter_type}")

def apply_migration(data: np.ndarray, parameters: dict) -> np.ndarray:
    """Apply seismic migration (placeholder implementation)"""
    # This is a placeholder - real migration algorithms are complex
    # and would require specialized libraries like SeisUn, Madagascar, etc.
    migration_type = parameters.get("migration_type", "kirchhoff")
    
    if migration_type == "kirchhoff":
        # Placeholder: apply simple smoothing as a migration approximation
        from scipy import ndimage
        smoothed = ndimage.gaussian_filter(data, sigma=1.0)
        return smoothed
    else:
        return data

def compute_attributes(data: np.ndarray, parameters: dict) -> np.ndarray:
    """Compute seismic attributes"""
    attribute_type = parameters.get("attribute_type", "coherence")
    
    if attribute_type == "coherence":
        window_size = parameters.get("window_size", 5)
        return SeismicProcessingAlgorithms.compute_coherence_attribute(data, window_size)
    elif attribute_type == "amplitude":
        return SeismicProcessingAlgorithms.compute_amplitude_envelope(data)
    else:
        raise ValueError(f"Unsupported attribute type: {attribute_type}")

def save_analysis_result(result: np.ndarray, file_path: Path):
    """Save analysis results to HDF5 file"""
    with h5py.File(str(file_path), 'w') as f:
        f.create_dataset('data', data=result, compression='gzip')
        f.attrs['created_at'] = datetime.now().isoformat()
        f.attrs['shape'] = result.shape
        f.attrs['dtype'] = str(result.dtype)
