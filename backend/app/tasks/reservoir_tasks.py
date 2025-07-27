from celery import current_task
from app.celery_app import celery_app
from app.database.config import SessionLocal
from app.models.reservoir import (
    ReservoirData, ReservoirSimulation, ReservoirForecast, 
    ReservoirWarning, PredictionSession,
    SimulationStatus, ForecastStatus, WarningLevel
)
from app.services.reservoir_service import ReservoirService
from app.schemas.reservoir import ReservoirWarningCreate

import numpy as np
import pandas as pd
import json
from pathlib import Path
from datetime import datetime, timedelta
import traceback
import logging
from typing import Dict, List, Any, Optional
import uuid

# ML imports
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
import joblib
import pickle

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ReservoirMLProcessor:
    """Machine Learning processor for reservoir analysis"""
    
    def __init__(self):
        self.scaler = StandardScaler()
        self.models = {}
        
    def preprocess_data(self, data: pd.DataFrame, config: Dict[str, Any]) -> pd.DataFrame:
        """Preprocess reservoir data for ML analysis"""
        logger.info("Starting data preprocessing")
        
        # Handle missing values
        if config.get('fill_missing', True):
            data = data.fillna(method='forward').fillna(method='backward')
        
        # Remove outliers using IQR method
        if config.get('remove_outliers', True):
            Q1 = data.quantile(0.25)
            Q3 = data.quantile(0.75)
            IQR = Q3 - Q1
            data = data[~((data < (Q1 - 1.5 * IQR)) | (data > (Q3 + 1.5 * IQR))).any(axis=1)]
        
        # Normalize values if requested
        if config.get('normalize', True):
            numeric_columns = data.select_dtypes(include=[np.number]).columns
            data[numeric_columns] = self.scaler.fit_transform(data[numeric_columns])
        
        # Feature engineering
        if config.get('create_time_features', True) and 'timestamp' in data.columns:
            data['hour'] = pd.to_datetime(data['timestamp']).dt.hour
            data['day'] = pd.to_datetime(data['timestamp']).dt.day
            data['month'] = pd.to_datetime(data['timestamp']).dt.month
            data['year'] = pd.to_datetime(data['timestamp']).dt.year
            
        logger.info(f"Preprocessing completed. Shape: {data.shape}")
        return data
    
    def create_lstm_model(self, input_shape: tuple, config: Dict[str, Any]) -> tf.keras.Model:
        """Create LSTM model for time series forecasting"""
        model = Sequential([
            LSTM(config.get('lstm_units', 50), return_sequences=True, input_shape=input_shape),
            Dropout(config.get('dropout_rate', 0.2)),
            LSTM(config.get('lstm_units', 50), return_sequences=False),
            Dropout(config.get('dropout_rate', 0.2)),
            Dense(config.get('dense_units', 25)),
            Dense(1)
        ])
        
        model.compile(
            optimizer=config.get('optimizer', 'adam'),
            loss=config.get('loss', 'mse'),
            metrics=['mae']
        )
        
        return model
    
    def prepare_lstm_data(self, data: np.ndarray, lookback: int = 60) -> tuple:
        """Prepare data for LSTM training"""
        X, y = [], []
        for i in range(lookback, len(data)):
            X.append(data[i-lookback:i])
            y.append(data[i])
        return np.array(X), np.array(y)
    
    def train_random_forest(self, X: np.ndarray, y: np.ndarray, config: Dict[str, Any]) -> RandomForestRegressor:
        """Train Random Forest model"""
        model = RandomForestRegressor(
            n_estimators=config.get('n_estimators', 100),
            max_depth=config.get('max_depth', None),
            random_state=config.get('random_state', 42),
            n_jobs=-1
        )
        
        model.fit(X, y)
        return model
    
    def evaluate_model(self, model, X_test: np.ndarray, y_test: np.ndarray) -> Dict[str, float]:
        """Evaluate model performance"""
        if hasattr(model, 'predict'):
            predictions = model.predict(X_test)
        else:
            predictions = model.predict(X_test).flatten()
        
        return {
            'mse': float(mean_squared_error(y_test, predictions)),
            'rmse': float(np.sqrt(mean_squared_error(y_test, predictions))),
            'mae': float(mean_absolute_error(y_test, predictions)),
            'r2': float(r2_score(y_test, predictions))
        }
    
    def generate_forecast(self, model, last_data: np.ndarray, forecast_days: int, config: Dict[str, Any]) -> Dict[str, Any]:
        """Generate forecast using trained model"""
        forecasts = []
        confidence_intervals = []
        
        current_data = last_data.copy()
        
        for day in range(forecast_days):
            if hasattr(model, 'predict'):
                # Random Forest prediction
                prediction = model.predict(current_data.reshape(1, -1))[0]
                # Simple confidence interval estimation
                std_error = config.get('prediction_std', 0.1) * abs(prediction)
                confidence_intervals.append({
                    'lower': prediction - 1.96 * std_error,
                    'upper': prediction + 1.96 * std_error
                })
            else:
                # LSTM prediction
                prediction = model.predict(current_data.reshape(1, current_data.shape[0], 1))[0][0]
                std_error = config.get('prediction_std', 0.1) * abs(prediction)
                confidence_intervals.append({
                    'lower': prediction - 1.96 * std_error,
                    'upper': prediction + 1.96 * std_error
                })
            
            forecasts.append(float(prediction))
            
            # Update current_data for next prediction (rolling window)
            if len(current_data.shape) == 1:
                current_data = np.roll(current_data, -1)
                current_data[-1] = prediction
            
        return {
            'forecasts': forecasts,
            'confidence_intervals': confidence_intervals,
            'forecast_dates': [(datetime.now() + timedelta(days=i+1)).isoformat() for i in range(forecast_days)]
        }
    
    def detect_anomalies_and_warnings(self, forecast_data: Dict[str, Any], thresholds: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Detect potential issues and generate warnings"""
        warnings = []
        forecasts = forecast_data['forecasts']
        dates = forecast_data['forecast_dates']
        
        # Production decline warning
        if len(forecasts) > 1:
            decline_rate = (forecasts[-1] - forecasts[0]) / len(forecasts)
            if decline_rate < thresholds.get('production_decline_threshold', -0.1):
                warnings.append({
                    'warning_type': 'production_decline',
                    'severity_level': WarningLevel.HIGH.value,
                    'title': 'Significant Production Decline Predicted',
                    'description': f'Production is forecasted to decline by {abs(decline_rate):.2%} over the forecast period.',
                    'trigger_conditions': {'decline_rate': decline_rate, 'threshold': thresholds.get('production_decline_threshold', -0.1)},
                    'predicted_occurrence_date': dates[0],
                    'confidence_score': 0.85,
                    'recommended_actions': [
                        'Review well performance data',
                        'Consider artificial lift optimization',
                        'Evaluate reservoir pressure maintenance options'
                    ]
                })
        
        # Low production warning
        min_forecast = min(forecasts)
        if min_forecast < thresholds.get('low_production_threshold', 100):
            warning_date = dates[forecasts.index(min_forecast)]
            warnings.append({
                'warning_type': 'low_production',
                'severity_level': WarningLevel.MEDIUM.value,
                'title': 'Low Production Rate Predicted',
                'description': f'Production rate is forecasted to drop to {min_forecast:.2f} below threshold.',
                'trigger_conditions': {'min_production': min_forecast, 'threshold': thresholds.get('low_production_threshold', 100)},
                'predicted_occurrence_date': warning_date,
                'confidence_score': 0.75,
                'recommended_actions': [
                    'Monitor well conditions closely',
                    'Consider workover operations',
                    'Review reservoir management strategy'
                ]
            })
        
        # High volatility warning
        if len(forecasts) > 5:
            volatility = np.std(forecasts)
            if volatility > thresholds.get('high_volatility_threshold', 50):
                warnings.append({
                    'warning_type': 'high_volatility',
                    'severity_level': WarningLevel.LOW.value,
                    'title': 'High Production Volatility Predicted',
                    'description': f'Production shows high volatility (std: {volatility:.2f}) which may indicate operational issues.',
                    'trigger_conditions': {'volatility': volatility, 'threshold': thresholds.get('high_volatility_threshold', 50)},
                    'predicted_occurrence_date': dates[0],
                    'confidence_score': 0.65,
                    'recommended_actions': [
                        'Investigate equipment stability',
                        'Review operational procedures',
                        'Consider flow assurance measures'
                    ]
                })
        
        return warnings


@celery_app.task(bind=True)
def run_reservoir_simulation(self, simulation_id: str):
    """Background task for running reservoir simulation"""
    db = SessionLocal()
    reservoir_service = ReservoirService(db)
    
    try:
        current_task.update_state(state="PROGRESS", meta={"progress": 0, "status": "Starting simulation"})
        
        # Get simulation record
        simulation = reservoir_service.get_reservoir_simulation(simulation_id)
        if not simulation:
            raise Exception(f"Simulation {simulation_id} not found")
        
        # Mark simulation as started
        reservoir_service.start_simulation(simulation_id)
        
        current_task.update_state(state="PROGRESS", meta={"progress": 10, "status": "Loading reservoir data"})
        
        # Get reservoir data
        reservoir_data = reservoir_service.get_reservoir_data(simulation.reservoir_data_id)
        if not reservoir_data:
            raise Exception("Reservoir data not found")
        
        # Load data from file
        data = load_reservoir_data(reservoir_data.file_path)
        
        current_task.update_state(state="PROGRESS", meta={"progress": 30, "status": "Running simulation"})
        
        # Run simulation based on extraction scenario
        simulation_results = run_extraction_simulation(
            data, 
            simulation.simulation_parameters,
            simulation.extraction_scenario
        )
        
        current_task.update_state(state="PROGRESS", meta={"progress": 70, "status": "Generating visualizations"})
        
        # Generate visualization data
        visualization_data = generate_simulation_visualizations(simulation_results, simulation.extraction_scenario)
        
        current_task.update_state(state="PROGRESS", meta={"progress": 90, "status": "Saving results"})
        
        # Save results
        results_path = save_simulation_results(simulation_id, simulation_results)
        
        # Complete simulation
        reservoir_service.complete_simulation(
            simulation_id,
            simulation_results,
            visualization_data,
            results_path
        )
        
        current_task.update_state(state="SUCCESS", meta={"progress": 100, "status": "Simulation completed"})
        
        logger.info(f"Simulation {simulation_id} completed successfully")
        return {"status": "completed", "results": simulation_results}
        
    except Exception as e:
        logger.error(f"Simulation {simulation_id} failed: {str(e)}")
        logger.error(traceback.format_exc())
        
        # Mark simulation as failed
        reservoir_service.fail_simulation(simulation_id, str(e))
        
        current_task.update_state(state="FAILURE", meta={"error": str(e)})
        raise
    
    finally:
        db.close()


@celery_app.task(bind=True)
def run_predictive_analysis(self, session_id: str, analysis_config: Dict[str, Any]):
    """Background task for running predictive analysis (main flow implementation)"""
    db = SessionLocal()
    reservoir_service = ReservoirService(db)
    ml_processor = ReservoirMLProcessor()
    
    try:
        current_task.update_state(state="PROGRESS", meta={"progress": 0, "status": "Initializing analysis"})
        
        # Get prediction session
        session = reservoir_service.get_prediction_session(session_id)
        if not session:
            raise Exception(f"Prediction session {session_id} not found")
        
        start_time = datetime.now()
        
        current_task.update_state(state="PROGRESS", meta={"progress": 10, "status": "Loading and preprocessing data"})
        
        # Step 2 & 3: Load and preprocess data
        reservoir_data_list = reservoir_service.get_data_for_analysis(session.data_sources)
        if not reservoir_data_list:
            raise Exception("No processed reservoir data found for analysis")
        
        # Combine data from multiple sources
        combined_data = combine_reservoir_data(reservoir_data_list)
        
        # Preprocess data
        preprocessed_data = ml_processor.preprocess_data(combined_data, analysis_config.get('preprocessing', {}))
        
        current_task.update_state(state="PROGRESS", meta={"progress": 30, "status": "Training ML models"})
        
        # Step 4: Apply ML algorithms
        models_config = analysis_config.get('models', {})
        trained_models = {}
        model_metrics = {}
        
        # Prepare data for training
        feature_columns = [col for col in preprocessed_data.columns if col not in ['production_rate', 'timestamp']]
        X = preprocessed_data[feature_columns].values
        y = preprocessed_data['production_rate'].values  # Assuming this is the target
        
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        # Train Random Forest model
        if 'random_forest' in models_config:
            rf_model = ml_processor.train_random_forest(X_train, y_train, models_config['random_forest'])
            trained_models['random_forest'] = rf_model
            model_metrics['random_forest'] = ml_processor.evaluate_model(rf_model, X_test, y_test)
        
        # Train LSTM model
        if 'lstm' in models_config:
            current_task.update_state(state="PROGRESS", meta={"progress": 50, "status": "Training LSTM model"})
            
            # Prepare LSTM data
            lookback = models_config['lstm'].get('lookback', 60)
            X_lstm, y_lstm = ml_processor.prepare_lstm_data(y, lookback)
            
            if len(X_lstm) > 0:
                X_lstm_train, X_lstm_test, y_lstm_train, y_lstm_test = train_test_split(
                    X_lstm, y_lstm, test_size=0.2, random_state=42
                )
                
                lstm_model = ml_processor.create_lstm_model(
                    (X_lstm_train.shape[1], 1), 
                    models_config['lstm']
                )
                
                # Train LSTM
                lstm_model.fit(
                    X_lstm_train.reshape(X_lstm_train.shape[0], X_lstm_train.shape[1], 1),
                    y_lstm_train,
                    epochs=models_config['lstm'].get('epochs', 50),
                    batch_size=models_config['lstm'].get('batch_size', 32),
                    validation_split=0.2,
                    verbose=0
                )
                
                trained_models['lstm'] = lstm_model
                model_metrics['lstm'] = ml_processor.evaluate_model(
                    lstm_model, 
                    X_lstm_test.reshape(X_lstm_test.shape[0], X_lstm_test.shape[1], 1),
                    y_lstm_test
                )
        
        current_task.update_state(state="PROGRESS", meta={"progress": 70, "status": "Generating forecasts"})
        
        # Generate forecasts using the best performing model
        best_model_name = min(model_metrics.keys(), key=lambda k: model_metrics[k]['mse'])
        best_model = trained_models[best_model_name]
        
        forecast_horizon = analysis_config.get('forecast_horizon_days', 365)
        
        if best_model_name == 'lstm':
            last_data = y[-lookback:]
            forecast_data = ml_processor.generate_forecast(best_model, last_data, forecast_horizon, models_config['lstm'])
        else:
            last_data = X[-1]
            forecast_data = ml_processor.generate_forecast(best_model, last_data, forecast_horizon, models_config['random_forest'])
        
        current_task.update_state(state="PROGRESS", meta={"progress": 85, "status": "Detecting issues and generating warnings"})
        
        # Step 5: Generate warnings
        warning_thresholds = analysis_config.get('warning_thresholds', {})
        potential_warnings = ml_processor.detect_anomalies_and_warnings(forecast_data, warning_thresholds)
        
        # Create forecast record
        forecast = reservoir_service.create_reservoir_forecast(
            {
                'name': f"Forecast from {session.session_name}",
                'description': f"ML-generated forecast using {best_model_name} model",
                'simulation_id': session_id,  # Using session_id as placeholder
                'model_type': best_model_name,
                'forecast_horizon_days': forecast_horizon
            },
            session.created_by
        )
        
        # Update forecast with results
        reservoir_service.update_reservoir_forecast(forecast.id, {
            'model_parameters': models_config.get(best_model_name, {}),
            'training_data_info': {
                'training_samples': len(X_train),
                'test_samples': len(X_test),
                'features': feature_columns
            },
            'model_accuracy_metrics': model_metrics[best_model_name],
            'forecast_data': forecast_data,
            'confidence_intervals': forecast_data.get('confidence_intervals'),
            'predicted_production_rate': forecast_data['forecasts'][-1],
            'status': 'published'
        })
        
        # Create warnings
        created_warnings = []
        for warning_data in potential_warnings:
            warning = reservoir_service.create_reservoir_warning({
                'forecast_id': forecast.id,
                **warning_data
            })
            created_warnings.append(warning.id)
        
        current_task.update_state(state="PROGRESS", meta={"progress": 95, "status": "Finalizing session"})
        
        # Complete prediction session
        end_time = datetime.now()
        duration_seconds = int((end_time - start_time).total_seconds())
        
        session_results = {
            'models_trained': list(trained_models.keys()),
            'best_model': best_model_name,
            'model_metrics': model_metrics,
            'forecast_summary': {
                'horizon_days': forecast_horizon,
                'final_prediction': forecast_data['forecasts'][-1],
                'trend': 'declining' if forecast_data['forecasts'][-1] < forecast_data['forecasts'][0] else 'stable/increasing'
            },
            'warnings_generated': len(created_warnings)
        }
        
        reservoir_service.complete_prediction_session(
            session_id,
            session_results,
            [forecast.id],
            created_warnings,
            duration_seconds
        )
        
        # Step 8: Log and notify (simplified)
        logger.info(f"Prediction session {session_id} completed. Generated {len(created_warnings)} warnings.")
        
        current_task.update_state(state="SUCCESS", meta={"progress": 100, "status": "Analysis completed"})
        
        return {
            "status": "completed",
            "session_results": session_results,
            "forecast_id": forecast.id,
            "warnings_count": len(created_warnings)
        }
        
    except Exception as e:
        logger.error(f"Predictive analysis {session_id} failed: {str(e)}")
        logger.error(traceback.format_exc())
        
        current_task.update_state(state="FAILURE", meta={"error": str(e)})
        raise
    
    finally:
        db.close()


def load_reservoir_data(file_path: str) -> pd.DataFrame:
    """Load reservoir data from file"""
    file_path = Path(file_path)
    
    if file_path.suffix.lower() == '.csv':
        return pd.read_csv(file_path)
    elif file_path.suffix.lower() in ['.xlsx', '.xls']:
        return pd.read_excel(file_path)
    elif file_path.suffix.lower() == '.json':
        return pd.read_json(file_path)
    else:
        raise ValueError(f"Unsupported file format: {file_path.suffix}")


def combine_reservoir_data(reservoir_data_list: List) -> pd.DataFrame:
    """Combine multiple reservoir data sources"""
    dataframes = []
    
    for reservoir_data in reservoir_data_list:
        df = load_reservoir_data(reservoir_data.file_path)
        df['data_source'] = reservoir_data.id
        df['data_type'] = reservoir_data.data_type.value
        dataframes.append(df)
    
    if not dataframes:
        raise ValueError("No data to combine")
    
    # Combine all dataframes
    combined_df = pd.concat(dataframes, ignore_index=True)
    
    # Sort by timestamp if available
    if 'timestamp' in combined_df.columns:
        combined_df['timestamp'] = pd.to_datetime(combined_df['timestamp'])
        combined_df = combined_df.sort_values('timestamp')
    
    return combined_df


def run_extraction_simulation(data: pd.DataFrame, parameters: Dict[str, Any], scenario: str) -> Dict[str, Any]:
    """Run reservoir extraction simulation"""
    logger.info(f"Running {scenario} simulation")
    
    # Simplified simulation logic - in reality this would be much more complex
    base_production = data['production_rate'].mean() if 'production_rate' in data.columns else 1000
    
    if scenario.lower() == 'aggressive':
        multiplier = parameters.get('production_multiplier', 1.3)
        decline_rate = parameters.get('decline_rate', 0.15)
    elif scenario.lower() == 'conservative':
        multiplier = parameters.get('production_multiplier', 0.9)
        decline_rate = parameters.get('decline_rate', 0.05)
    else:  # standard
        multiplier = parameters.get('production_multiplier', 1.0)
        decline_rate = parameters.get('decline_rate', 0.10)
    
    # Simulate production over time
    days = parameters.get('simulation_days', 365)
    production_rates = []
    cumulative_production = 0
    
    for day in range(days):
        daily_rate = base_production * multiplier * (1 - decline_rate * day / 365)
        daily_rate = max(daily_rate, 0)  # Ensure non-negative
        production_rates.append(daily_rate)
        cumulative_production += daily_rate
    
    return {
        'scenario': scenario,
        'daily_production_rates': production_rates,
        'cumulative_production': cumulative_production,
        'average_daily_rate': np.mean(production_rates),
        'final_rate': production_rates[-1],
        'recovery_factor': parameters.get('estimated_recovery_factor', 0.35),
        'simulation_parameters': parameters
    }


def generate_simulation_visualizations(results: Dict[str, Any], scenario: str) -> Dict[str, Any]:
    """Generate visualization data for simulation results"""
    
    # Production rate over time
    production_chart = {
        'type': 'line',
        'title': f'Production Rate Over Time - {scenario.title()} Scenario',
        'x_axis': list(range(len(results['daily_production_rates']))),
        'y_axis': results['daily_production_rates'],
        'x_label': 'Days',
        'y_label': 'Production Rate (bbl/day)'
    }
    
    # Cumulative production
    cumulative_data = np.cumsum(results['daily_production_rates'])
    cumulative_chart = {
        'type': 'line',
        'title': f'Cumulative Production - {scenario.title()} Scenario',
        'x_axis': list(range(len(cumulative_data))),
        'y_axis': cumulative_data.tolist(),
        'x_label': 'Days',
        'y_label': 'Cumulative Production (bbl)'
    }
    
    # Summary metrics
    summary_metrics = {
        'total_production': float(results['cumulative_production']),
        'average_rate': float(results['average_daily_rate']),
        'final_rate': float(results['final_rate']),
        'recovery_factor': float(results['recovery_factor'])
    }
    
    return {
        'charts': [production_chart, cumulative_chart],
        'summary_metrics': summary_metrics,
        'scenario': scenario
    }


def save_simulation_results(simulation_id: str, results: Dict[str, Any]) -> str:
    """Save simulation results to file"""
    results_dir = Path("processing/simulation_results")
    results_dir.mkdir(parents=True, exist_ok=True)
    
    results_file = results_dir / f"{simulation_id}_results.json"
    
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    return str(results_file)
