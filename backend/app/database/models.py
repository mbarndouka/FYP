from sqlalchemy import Column, Integer, String, Text, DateTime, func
from app.database.config import Base

# Import user models to ensure they're registered with SQLAlchemy
from app.models.user import User, UserSession

# Import data integration models to ensure they're registered with SQLAlchemy
from app.models.data_integration import (
    DataFile, FileMetadata, FileAccessLog, FileShare, DataIntegrationJob
)

# Import seismic models to ensure they're registered with SQLAlchemy
from app.models.seismic import (
    SeismicDataset, SeismicInterpretation, SeismicAnalysis,
    SeismicAttribute, SeismicSession
)

# Import reservoir models to ensure they're registered with SQLAlchemy
from app.models.reservoir import (
    ReservoirData, ReservoirSimulation, ReservoirForecast,
    ReservoirWarning, PredictionSession
)