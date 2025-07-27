import numpy as np
import pyvista as pv
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import h5py
import segyio
import base64
import io
from typing import Dict, Any, List, Tuple, Optional
from pathlib import Path

class Seismic3DVisualizer:
    """3D Seismic Data Visualization using PyVista and Plotly"""
    
    def __init__(self):
        self.plotter = None
        self.mesh = None
        
    def load_seismic_data(self, file_path: str) -> np.ndarray:
        """Load seismic data from various formats"""
        file_ext = Path(file_path).suffix.lower()
        
        if file_ext in ['.sgy', '.segy']:
            return self._load_segy_data(file_path)
        elif file_ext in ['.h5', '.hdf5']:
            return self._load_hdf5_data(file_path)
        else:
            raise ValueError(f"Unsupported file format: {file_ext}")
    
    def _load_segy_data(self, file_path: str) -> np.ndarray:
        """Load SEG-Y data"""
        with segyio.open(file_path, "r") as segy:
            data = segyio.tools.cube(segy)
            return data
    
    def _load_hdf5_data(self, file_path: str) -> np.ndarray:
        """Load HDF5 data"""
        with h5py.File(file_path, 'r') as f:
            # Adjust based on your HDF5 structure
            data = f['seismic_data'][:]
            return data
    
    def create_3d_volume(self, data: np.ndarray, spacing: Tuple[float, float, float] = (1, 1, 1)) -> pv.UniformGrid:
        """Create 3D volume mesh from seismic data"""
        # Create uniform grid
        grid = pv.UniformGrid(
            dimensions=data.shape,
            spacing=spacing,
            origin=(0, 0, 0)
        )
        
        # Add seismic amplitude data
        grid.point_data["amplitude"] = data.flatten(order="F")
        
        return grid
    
    def create_slice_visualization(self, data: np.ndarray, slice_type: str, position: int) -> Dict[str, Any]:
        """Create 2D slice visualization"""
        if slice_type == "inline":
            slice_data = data[position, :, :]
            title = f"Inline {position}"
            xlabel, ylabel = "Crossline", "Time (ms)"
        elif slice_type == "crossline":
            slice_data = data[:, position, :]
            title = f"Crossline {position}"
            xlabel, ylabel = "Inline", "Time (ms)"
        elif slice_type == "time":
            slice_data = data[:, :, position]
            title = f"Time Slice {position}"
            xlabel, ylabel = "Inline", "Crossline"
        else:
            raise ValueError("slice_type must be 'inline', 'crossline', or 'time'")
        
        # Create Plotly figure
        fig = go.Figure(data=go.Heatmap(
            z=slice_data,
            colorscale='RdBu',
            zmid=0,
            colorbar=dict(title="Amplitude")
        ))
        
        fig.update_layout(
            title=title,
            xaxis_title=xlabel,
            yaxis_title=ylabel,
            width=800,
            height=600
        )
        
        return {
            "figure": fig,
            "data": slice_data,
            "slice_type": slice_type,
            "position": position
        }
    
    def create_interactive_3d_plot(self, data: np.ndarray, opacity: float = 0.1) -> str:
        """Create interactive 3D visualization using Plotly"""
        # Sample data for better performance
        if data.size > 1000000:  # If data is too large, sample it
            step = max(1, int(np.cbrt(data.size / 1000000)))
            data = data[::step, ::step, ::step]
        
        # Get coordinates for non-zero values
        coords = np.where(np.abs(data) > np.percentile(np.abs(data), 95))
        x, y, z = coords
        values = data[coords]
        
        # Create 3D scatter plot
        fig = go.Figure(data=go.Scatter3d(
            x=x,
            y=y,
            z=z,
            mode='markers',
            marker=dict(
                size=2,
                color=values,
                colorscale='RdBu',
                opacity=opacity,
                colorbar=dict(title="Amplitude")
            )
        ))
        
        fig.update_layout(
            title="3D Seismic Visualization",
            scene=dict(
                xaxis_title="Inline",
                yaxis_title="Crossline",
                zaxis_title="Time (ms)"
            ),
            width=1000,
            height=800
        )
        
        return fig.to_html(include_plotlyjs=True)
    
    def create_volume_rendering(self, data: np.ndarray) -> str:
        """Create volume rendering using Plotly"""
        # Normalize data
        data_norm = (data - data.min()) / (data.max() - data.min())
        
        # Create volume plot
        fig = go.Figure(data=go.Volume(
            x=np.arange(data.shape[0]),
            y=np.arange(data.shape[1]),
            z=np.arange(data.shape[2]),
            value=data_norm.flatten(),
            isomin=0.1,
            isomax=0.9,
            opacity=0.1,
            surface_count=10,
            colorscale='RdBu'
        ))
        
        fig.update_layout(
            title="Seismic Volume Rendering",
            scene=dict(
                xaxis_title="Inline",
                yaxis_title="Crossline",
                zaxis_title="Time (ms)"
            ),
            width=1000,
            height=800
        )
        
        return fig.to_html(include_plotlyjs=True)
    
    def add_interpretation_overlay(
        self, 
        fig: go.Figure, 
        interpretation_data: Dict[str, Any],
        interpretation_type: str
    ) -> go.Figure:
        """Add interpretation overlay to existing plot"""
        
        if interpretation_type == "horizon":
            return self._add_horizon_overlay(fig, interpretation_data)
        elif interpretation_type == "fault":
            return self._add_fault_overlay(fig, interpretation_data)
        elif interpretation_type == "salt_body":
            return self._add_salt_body_overlay(fig, interpretation_data)
        
        return fig
    
    def _add_horizon_overlay(self, fig: go.Figure, horizon_data: Dict[str, Any]) -> go.Figure:
        """Add horizon interpretation overlay"""
        points = horizon_data.get('points', [])
        if not points:
            return fig
        
        x_coords = [p['x'] for p in points]
        y_coords = [p['y'] for p in points]
        z_coords = [p['z'] for p in points]
        
        # Add horizon as a line
        fig.add_trace(go.Scatter3d(
            x=x_coords,
            y=y_coords,
            z=z_coords,
            mode='lines+markers',
            line=dict(
                color=horizon_data.get('color', '#FF0000'),
                width=horizon_data.get('thickness', 3)
            ),
            marker=dict(size=3),
            name=horizon_data.get('name', 'Horizon'),
            opacity=horizon_data.get('opacity', 1.0)
        ))
        
        return fig
    
    def _add_fault_overlay(self, fig: go.Figure, fault_data: Dict[str, Any]) -> go.Figure:
        """Add fault interpretation overlay"""
        points = fault_data.get('points', [])
        if not points:
            return fig
        
        # Create fault plane
        x_coords = [p['x'] for p in points]
        y_coords = [p['y'] for p in points]
        z_coords = [p['z'] for p in points]
        
        fig.add_trace(go.Scatter3d(
            x=x_coords,
            y=y_coords,
            z=z_coords,
            mode='lines',
            line=dict(
                color=fault_data.get('color', '#0000FF'),
                width=fault_data.get('thickness', 2)
            ),
            name=fault_data.get('name', 'Fault'),
            opacity=fault_data.get('opacity', 1.0)
        ))
        
        return fig
    
    def _add_salt_body_overlay(self, fig: go.Figure, salt_data: Dict[str, Any]) -> go.Figure:
        """Add salt body interpretation overlay"""
        # Implementation for salt body visualization
        return fig
    
    def create_attribute_visualization(
        self, 
        data: np.ndarray, 
        attribute_type: str,
        slice_position: Optional[int] = None
    ) -> Dict[str, Any]:
        """Create visualization for seismic attributes"""
        
        if attribute_type == "coherence":
            return self._create_coherence_viz(data, slice_position)
        elif attribute_type == "amplitude":
            return self._create_amplitude_viz(data, slice_position)
        elif attribute_type == "frequency":
            return self._create_frequency_viz(data, slice_position)
        
        return {}
    
    def _create_coherence_viz(self, data: np.ndarray, slice_position: Optional[int]) -> Dict[str, Any]:
        """Create coherence attribute visualization"""
        if slice_position is not None:
            slice_data = data[:, :, slice_position]
        else:
            slice_data = np.mean(data, axis=2)  # Time average
        
        fig = go.Figure(data=go.Heatmap(
            z=slice_data,
            colorscale='Viridis',
            colorbar=dict(title="Coherence")
        ))
        
        fig.update_layout(
            title="Coherence Attribute",
            xaxis_title="Crossline",
            yaxis_title="Inline"
        )
        
        return {"figure": fig, "data": slice_data}
    
    def _create_amplitude_viz(self, data: np.ndarray, slice_position: Optional[int]) -> Dict[str, Any]:
        """Create amplitude attribute visualization"""
        if slice_position is not None:
            slice_data = data[:, :, slice_position]
        else:
            slice_data = np.mean(np.abs(data), axis=2)  # RMS amplitude
        
        fig = go.Figure(data=go.Heatmap(
            z=slice_data,
            colorscale='RdBu',
            zmid=0,
            colorbar=dict(title="Amplitude")
        ))
        
        fig.update_layout(
            title="Amplitude Attribute",
            xaxis_title="Crossline",
            yaxis_title="Inline"
        )
        
        return {"figure": fig, "data": slice_data}
    
    def _create_frequency_viz(self, data: np.ndarray, slice_position: Optional[int]) -> Dict[str, Any]:
        """Create frequency attribute visualization"""
        # Compute instantaneous frequency
        analytic_signal = np.apply_along_axis(lambda x: np.imag(np.fft.hilbert(x)), axis=2, arr=data)
        freq_data = np.diff(np.unwrap(np.angle(analytic_signal), axis=2), axis=2)
        
        if slice_position is not None and slice_position < freq_data.shape[2]:
            slice_data = freq_data[:, :, slice_position]
        else:
            slice_data = np.mean(freq_data, axis=2)
        
        fig = go.Figure(data=go.Heatmap(
            z=slice_data,
            colorscale='Plasma',
            colorbar=dict(title="Frequency (Hz)")
        ))
        
        fig.update_layout(
            title="Instantaneous Frequency",
            xaxis_title="Crossline",
            yaxis_title="Inline"
        )
        
        return {"figure": fig, "data": slice_data}
    
    def create_multi_view_dashboard(
        self, 
        data: np.ndarray,
        inline_pos: int,
        crossline_pos: int,
        time_pos: int
    ) -> str:
        """Create multi-view dashboard with inline, crossline, and time slices"""
        
        # Create subplots
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('Inline View', 'Crossline View', 'Time Slice', '3D View'),
            specs=[[{"type": "heatmap"}, {"type": "heatmap"}],
                   [{"type": "heatmap"}, {"type": "scatter3d"}]]
        )
        
        # Inline slice
        inline_data = data[inline_pos, :, :]
        fig.add_trace(
            go.Heatmap(z=inline_data, colorscale='RdBu', zmid=0, showscale=False),
            row=1, col=1
        )
        
        # Crossline slice
        crossline_data = data[:, crossline_pos, :]
        fig.add_trace(
            go.Heatmap(z=crossline_data, colorscale='RdBu', zmid=0, showscale=False),
            row=1, col=2
        )
        
        # Time slice
        time_data = data[:, :, time_pos]
        fig.add_trace(
            go.Heatmap(z=time_data, colorscale='RdBu', zmid=0, showscale=False),
            row=2, col=1
        )
        
        # 3D scatter (sampled for performance)
        sample_step = max(1, data.shape[0] // 50)
        x, y, z = np.meshgrid(
            np.arange(0, data.shape[0], sample_step),
            np.arange(0, data.shape[1], sample_step),
            np.arange(0, data.shape[2], sample_step),
            indexing='ij'
        )
        
        sampled_data = data[::sample_step, ::sample_step, ::sample_step]
        mask = np.abs(sampled_data) > np.percentile(np.abs(sampled_data), 90)
        
        fig.add_trace(
            go.Scatter3d(
                x=x[mask],
                y=y[mask],
                z=z[mask],
                mode='markers',
                marker=dict(
                    size=2,
                    color=sampled_data[mask],
                    colorscale='RdBu',
                    opacity=0.6
                ),
                showlegend=False
            ),
            row=2, col=2
        )
        
        fig.update_layout(
            height=800,
            title_text="Seismic Multi-View Dashboard"
        )
        
        return fig.to_html(include_plotlyjs=True)

class SeismicProcessingAlgorithms:
    """Advanced seismic processing algorithms"""
    
    @staticmethod
    def apply_bandpass_filter(data: np.ndarray, low_freq: float, high_freq: float, sample_rate: float) -> np.ndarray:
        """Apply bandpass filter to seismic data"""
        from scipy import signal
        
        nyquist = 0.5 * sample_rate
        low = low_freq / nyquist
        high = high_freq / nyquist
        
        b, a = signal.butter(4, [low, high], btype='band')
        
        # Apply filter along time axis
        filtered_data = np.apply_along_axis(
            lambda x: signal.filtfilt(b, a, x), 
            axis=2, 
            arr=data
        )
        
        return filtered_data
    
    @staticmethod
    def compute_coherence_attribute(data: np.ndarray, window_size: int = 5) -> np.ndarray:
        """Compute coherence attribute"""
        from scipy import ndimage
        
        # Compute gradients
        grad_x = np.gradient(data, axis=0)
        grad_y = np.gradient(data, axis=1)
        grad_z = np.gradient(data, axis=2)
        
        # Compute structure tensor
        gxx = ndimage.uniform_filter(grad_x**2, size=window_size)
        gyy = ndimage.uniform_filter(grad_y**2, size=window_size)
        gzz = ndimage.uniform_filter(grad_z**2, size=window_size)
        gxy = ndimage.uniform_filter(grad_x * grad_y, size=window_size)
        gxz = ndimage.uniform_filter(grad_x * grad_z, size=window_size)
        gyz = ndimage.uniform_filter(grad_y * grad_z, size=window_size)
        
        # Compute coherence
        coherence = np.zeros_like(data)
        
        for i in range(data.shape[0]):
            for j in range(data.shape[1]):
                for k in range(data.shape[2]):
                    # Structure tensor at this point
                    G = np.array([
                        [gxx[i,j,k], gxy[i,j,k], gxz[i,j,k]],
                        [gxy[i,j,k], gyy[i,j,k], gyz[i,j,k]],
                        [gxz[i,j,k], gyz[i,j,k], gzz[i,j,k]]
                    ])
                    
                    # Compute eigenvalues
                    eigenvals = np.linalg.eigvals(G)
                    eigenvals = np.sort(eigenvals)[::-1]  # Sort descending
                    
                    # Coherence = (λ1 - λ2) / (λ1 + λ2 + λ3)
                    if np.sum(eigenvals) > 1e-10:
                        coherence[i,j,k] = (eigenvals[0] - eigenvals[1]) / np.sum(eigenvals)
        
        return coherence
    
    @staticmethod
    def compute_amplitude_envelope(data: np.ndarray) -> np.ndarray:
        """Compute amplitude envelope using Hilbert transform"""
        from scipy.signal import hilbert
        
        envelope = np.abs(hilbert(data, axis=2))
        return envelope
    
    @staticmethod
    def apply_agc(data: np.ndarray, window_length: int = 100) -> np.ndarray:
        """Apply Automatic Gain Control (AGC)"""
        agc_data = np.zeros_like(data)
        
        for i in range(data.shape[0]):
            for j in range(data.shape[1]):
                trace = data[i, j, :]
                
                # Compute running RMS
                rms = np.zeros_like(trace)
                half_window = window_length // 2
                
                for k in range(len(trace)):
                    start = max(0, k - half_window)
                    end = min(len(trace), k + half_window + 1)
                    rms[k] = np.sqrt(np.mean(trace[start:end]**2))
                
                # Apply AGC
                agc_data[i, j, :] = np.where(rms > 1e-10, trace / rms, trace)
        
        return agc_data
