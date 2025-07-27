from sqlalchemy import Column, String, DateTime, Boolean, Enum, func, Text
from sqlalchemy.orm import relationship
from app.database.config import Base
import enum


class UserRole(enum.Enum):
    ADMIN = "admin"
    FIELD_TEAM = "field_team"
    GEOSCIENTIST = "geoscientist"
    RESERVOIR_ENGINEER = "reservoir_engineer"
    ENVIRONMENTAL_OFFICER = "environmental_officer"
    MANAGER = "manager"
    NEW_EMPLOYEE = "new_employee"


class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, index=True)  # Supabase user ID
    email = Column(String(255), unique=True, index=True, nullable=False)
    full_name = Column(String(255), nullable=True)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.NEW_EMPLOYEE)
    is_active = Column(Boolean, default=True)
    profile_image_url = Column(String(500), nullable=True)
    department = Column(String(100), nullable=True)
    phone_number = Column(String(20), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)
    
    # Seismic relationships
    seismic_datasets = relationship("SeismicDataset", back_populates="uploader")
    seismic_interpretations = relationship("SeismicInterpretation", back_populates="interpreter")
    seismic_analyses = relationship("SeismicAnalysis", back_populates="analyst")
    seismic_sessions = relationship("SeismicSession", back_populates="user")
    
    # Reservoir relationships
    reservoir_data = relationship("ReservoirData", back_populates="uploader")
    reservoir_simulations = relationship("ReservoirSimulation", back_populates="creator")
    reservoir_forecasts = relationship("ReservoirForecast", back_populates="creator")
    acknowledged_warnings = relationship("ReservoirWarning", back_populates="acknowledger")
    prediction_sessions = relationship("PredictionSession", back_populates="creator")
    
    def __repr__(self):
        return f"<User(id='{self.id}', email='{self.email}', role='{self.role.value}')>"


class UserSession(Base):
    __tablename__ = "user_sessions"
    
    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, nullable=False, index=True)
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text, nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_revoked = Column(Boolean, default=False)
    
    def __repr__(self):
        return f"<UserSession(id='{self.id}', user_id='{self.user_id}')>"
