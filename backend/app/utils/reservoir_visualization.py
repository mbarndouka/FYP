import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
import json
from datetime import datetime, timedelta


class ReservoirVisualization:
    """Utility class for creating reservoir analysis visualizations"""
    
    def __init__(self):
        self.color_palette = {
            'primary': '#1f77b4',
            'secondary': '#ff7f0e', 
            'success': '#2ca02c',
            'warning': '#ffcc00',
            'danger': '#d62728',
            'info': '#17a2b8'
        }
    
    def create_production_forecast_chart(self, forecast_data: Dict[str, Any], title: str = "Production Forecast") -> Dict[str, Any]:
        """Create production forecast visualization"""
        
        forecasts = forecast_data.get('forecasts', [])
        confidence_intervals = forecast_data.get('confidence_intervals', [])
        dates = forecast_data.get('forecast_dates', [])
        
        if not forecasts or not dates:
            return {"error": "No forecast data available"}
        
        # Convert dates to datetime
        date_objects = [datetime.fromisoformat(date.replace('Z', '+00:00')) if isinstance(date, str) else date for date in dates]
        
        fig = go.Figure()
        
        # Add confidence interval if available
        if confidence_intervals:
            upper_bounds = [ci.get('upper', 0) for ci in confidence_intervals]
            lower_bounds = [ci.get('lower', 0) for ci in confidence_intervals]
            
            fig.add_trace(go.Scatter(
                x=date_objects + date_objects[::-1],
                y=upper_bounds + lower_bounds[::-1],
                fill='toself',
                fillcolor='rgba(31, 119, 180, 0.2)',
                line=dict(color='rgba(255,255,255,0)'),
                showlegend=True,
                name='Confidence Interval'
            ))
        
        # Add forecast line
        fig.add_trace(go.Scatter(
            x=date_objects,
            y=forecasts,
            mode='lines+markers',
            name='Forecast',
            line=dict(color=self.color_palette['primary'], width=3),
            marker=dict(size=6)
        ))
        
        fig.update_layout(
            title=dict(text=title, x=0.5),
            xaxis_title="Date",
            yaxis_title="Production Rate (bbl/day)",
            hovermode='x unified',
            template='plotly_white',
            width=800,
            height=500
        )
        
        return fig.to_dict()
    
    def create_simulation_comparison_chart(self, simulations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create comparison chart for different extraction scenarios"""
        
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('Production Rates', 'Cumulative Production', 'Recovery Factors', 'Final Rates'),
            specs=[[{"secondary_y": False}, {"secondary_y": False}],
                   [{"type": "bar"}, {"type": "bar"}]]
        )
        
        colors = [self.color_palette['primary'], self.color_palette['secondary'], self.color_palette['success']]
        
        recovery_factors = []
        final_rates = []
        scenario_names = []
        
        for i, sim in enumerate(simulations[:3]):  # Limit to 3 scenarios
            results = sim.get('results_summary', {})
            viz_data = sim.get('visualization_data', {})
            scenario = sim.get('extraction_scenario', f'Scenario {i+1}')
            scenario_names.append(scenario)
            
            # Production rates over time
            if 'daily_production_rates' in results:
                rates = results['daily_production_rates'][:365]  # First year
                days = list(range(len(rates)))
                
                fig.add_trace(
                    go.Scatter(x=days, y=rates, name=f'{scenario} - Production',
                              line=dict(color=colors[i % len(colors)])),
                    row=1, col=1
                )
                
                # Cumulative production
                cumulative = np.cumsum(rates)
                fig.add_trace(
                    go.Scatter(x=days, y=cumulative, name=f'{scenario} - Cumulative',
                              line=dict(color=colors[i % len(colors)])),
                    row=1, col=2
                )
                
                final_rates.append(rates[-1] if rates else 0)
            else:
                final_rates.append(0)
            
            recovery_factors.append(results.get('recovery_factor', 0))
        
        # Recovery factors bar chart
        fig.add_trace(
            go.Bar(x=scenario_names, y=recovery_factors, name='Recovery Factor',
                   marker_color=[colors[i % len(colors)] for i in range(len(scenario_names))]),
            row=2, col=1
        )
        
        # Final rates bar chart
        fig.add_trace(
            go.Bar(x=scenario_names, y=final_rates, name='Final Rate',
                   marker_color=[colors[i % len(colors)] for i in range(len(scenario_names))]),
            row=2, col=2
        )
        
        fig.update_layout(height=800, showlegend=True, title_text="Extraction Scenario Comparison")
        fig.update_xaxes(title_text="Days", row=1, col=1)
        fig.update_xaxes(title_text="Days", row=1, col=2)
        fig.update_xaxes(title_text="Scenario", row=2, col=1)
        fig.update_xaxes(title_text="Scenario", row=2, col=2)
        fig.update_yaxes(title_text="Rate (bbl/day)", row=1, col=1)
        fig.update_yaxes(title_text="Cumulative (bbl)", row=1, col=2)
        fig.update_yaxes(title_text="Recovery Factor", row=2, col=1)
        fig.update_yaxes(title_text="Final Rate (bbl/day)", row=2, col=2)
        
        return fig.to_dict()
    
    def create_warnings_dashboard(self, warnings: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create warnings dashboard visualization"""
        
        if not warnings:
            return {"message": "No warnings to display"}
        
        # Count warnings by severity
        severity_counts = {}
        warning_types = {}
        
        for warning in warnings:
            severity = warning.get('severity_level', 'unknown')
            warning_type = warning.get('warning_type', 'unknown')
            
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
            warning_types[warning_type] = warning_types.get(warning_type, 0) + 1
        
        fig = make_subplots(
            rows=1, cols=2,
            subplot_titles=('Warnings by Severity', 'Warnings by Type'),
            specs=[[{"type": "pie"}, {"type": "bar"}]]
        )
        
        # Severity pie chart
        severity_colors = {
            'critical': self.color_palette['danger'],
            'high': '#ff6b6b',
            'medium': self.color_palette['warning'],
            'low': '#95a5a6'
        }
        
        fig.add_trace(
            go.Pie(labels=list(severity_counts.keys()), 
                   values=list(severity_counts.values()),
                   marker_colors=[severity_colors.get(s, '#95a5a6') for s in severity_counts.keys()],
                   name="Severity"),
            row=1, col=1
        )
        
        # Warning types bar chart
        fig.add_trace(
            go.Bar(x=list(warning_types.keys()), 
                   y=list(warning_types.values()),
                   marker_color=self.color_palette['info'],
                   name="Types"),
            row=1, col=2
        )
        
        fig.update_layout(height=400, showlegend=False, title_text="Reservoir Warnings Overview")
        
        return fig.to_dict()
    
    def create_model_performance_chart(self, model_metrics: Dict[str, Dict[str, float]]) -> Dict[str, Any]:
        """Create model performance comparison chart"""
        
        if not model_metrics:
            return {"error": "No model metrics available"}
        
        models = list(model_metrics.keys())
        metrics = ['mse', 'rmse', 'mae', 'r2']
        
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('Mean Squared Error', 'Root Mean Squared Error', 'Mean Absolute Error', 'R² Score')
        )
        
        positions = [(1, 1), (1, 2), (2, 1), (2, 2)]
        colors = [self.color_palette['primary'], self.color_palette['secondary'], self.color_palette['success']]
        
        for i, metric in enumerate(metrics):
            values = [model_metrics[model].get(metric, 0) for model in models]
            
            fig.add_trace(
                go.Bar(x=models, y=values, name=metric.upper(),
                       marker_color=[colors[j % len(colors)] for j in range(len(models))],
                       showlegend=False),
                row=positions[i][0], col=positions[i][1]
            )
        
        fig.update_layout(height=600, title_text="ML Model Performance Comparison")
        
        return fig.to_dict()
    
    def create_reservoir_data_overview(self, data: pd.DataFrame, data_type: str) -> Dict[str, Any]:
        """Create overview visualization for reservoir data"""
        
        if data.empty:
            return {"error": "No data available"}
        
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('Production Over Time', 'Pressure Over Time', 'Data Distribution', 'Correlation Matrix')
        )
        
        # Time series plots
        if 'timestamp' in data.columns:
            timestamps = pd.to_datetime(data['timestamp'])
            
            if 'production_rate' in data.columns:
                fig.add_trace(
                    go.Scatter(x=timestamps, y=data['production_rate'],
                              mode='lines', name='Production Rate',
                              line=dict(color=self.color_palette['primary'])),
                    row=1, col=1
                )
            
            if 'reservoir_pressure' in data.columns:
                fig.add_trace(
                    go.Scatter(x=timestamps, y=data['reservoir_pressure'],
                              mode='lines', name='Reservoir Pressure',
                              line=dict(color=self.color_palette['secondary'])),
                    row=1, col=2
                )
        
        # Data distribution
        numeric_columns = data.select_dtypes(include=[np.number]).columns
        if len(numeric_columns) > 0:
            main_column = 'production_rate' if 'production_rate' in numeric_columns else numeric_columns[0]
            fig.add_trace(
                go.Histogram(x=data[main_column], name='Distribution',
                            marker_color=self.color_palette['success']),
                row=2, col=1
            )
        
        # Correlation matrix (simplified)
        if len(numeric_columns) > 1:
            corr_matrix = data[numeric_columns].corr()
            fig.add_trace(
                go.Heatmap(z=corr_matrix.values,
                          x=corr_matrix.columns,
                          y=corr_matrix.columns,
                          colorscale='RdBu',
                          name='Correlation'),
                row=2, col=2
            )
        
        fig.update_layout(height=700, title_text=f"Reservoir Data Overview - {data_type}")
        
        return fig.to_dict()
    
    def export_visualization_config(self, viz_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Export visualization configuration for frontend use"""
        
        base_config = {
            'responsive': True,
            'displayModeBar': True,
            'displaylogo': False,
            'modeBarButtonsToRemove': ['pan2d', 'lasso2d', 'select2d'],
            'toImageButtonOptions': {
                'format': 'png',
                'filename': f'reservoir_{viz_type}_{datetime.now().strftime("%Y%m%d_%H%M%S")}',
                'height': 500,
                'width': 800,
                'scale': 1
            }
        }
        
        return {
            'data': data,
            'config': base_config,
            'layout': {
                'autosize': True,
                'margin': {'l': 50, 'r': 50, 't': 50, 'b': 50},
                'font': {'family': 'Arial, sans-serif', 'size': 12},
                'plot_bgcolor': 'rgba(0,0,0,0)',
                'paper_bgcolor': 'rgba(0,0,0,0)'
            }
        }


def generate_sample_data():
    """Generate sample reservoir data for testing"""
    
    # Generate time series data
    dates = pd.date_range('2023-01-01', periods=365, freq='D')
    
    # Simulate production decline
    base_production = 1000
    decline_rate = 0.1
    noise = np.random.normal(0, 50, len(dates))
    
    production_rates = []
    for i, date in enumerate(dates):
        rate = base_production * (1 - decline_rate * i / 365) + noise[i]
        rate = max(rate, 0)  # Ensure non-negative
        production_rates.append(rate)
    
    # Simulate pressure data
    base_pressure = 2000  # psi
    pressure_decline = 0.15
    pressure_noise = np.random.normal(0, 20, len(dates))
    
    pressures = []
    for i, date in enumerate(dates):
        pressure = base_pressure * (1 - pressure_decline * i / 365) + pressure_noise[i]
        pressure = max(pressure, 500)  # Minimum pressure
        pressures.append(pressure)
    
    return pd.DataFrame({
        'timestamp': dates,
        'production_rate': production_rates,
        'reservoir_pressure': pressures,
        'water_cut': np.random.uniform(0.1, 0.8, len(dates)),
        'gas_oil_ratio': np.random.uniform(100, 500, len(dates)),
        'well_head_temperature': np.random.uniform(80, 120, len(dates))
    })


if __name__ == "__main__":
    # Test the visualization functions
    viz = ReservoirVisualization()
    
    # Generate sample data
    sample_data = generate_sample_data()
    
    # Test data overview
    overview_chart = viz.create_reservoir_data_overview(sample_data, "Historical")
    print("Data overview chart created successfully")
    
    # Test forecast chart
    sample_forecast = {
        'forecasts': [900, 885, 870, 855, 840, 825, 810, 795, 780, 765],
        'forecast_dates': [(datetime.now() + timedelta(days=i)).isoformat() for i in range(10)],
        'confidence_intervals': [
            {'lower': f - 50, 'upper': f + 50} for f in [900, 885, 870, 855, 840, 825, 810, 795, 780, 765]
        ]
    }
    
    forecast_chart = viz.create_production_forecast_chart(sample_forecast)
    print("Forecast chart created successfully")
    
    print("Reservoir visualization utilities are working correctly!")
