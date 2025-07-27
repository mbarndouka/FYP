from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean, JSON, ForeignKey, func, LargeBinary
from sqlalchemy.orm import relationship
from app.database.config import Base

class SeismicDataset(Base):
    __tablename__ = "seismic_datasets"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text)
    file_path = Column(String(500), nullable=False)
    file_format = Column(String(50), nullable=False)  # SEG-Y, HDF5, etc.
    file_size = Column(Integer)  # in bytes
    acquisition_date = Column(DateTime)
    processing_status = Column(String(50), default="raw")  # raw, processed, analyzed
    
    # Spatial coordinates
    min_inline = Column(Integer)
    max_inline = Column(Integer)
    min_crossline = Column(Integer)
    max_crossline = Column(Integer)
    min_time = Column(Float)  # in milliseconds
    max_time = Column(Float)
    
    # Metadata
    sample_rate = Column(Float)  # sample interval in ms
    trace_count = Column(Integer)
    inline_increment = Column(Integer, default=1)
    crossline_increment = Column(Integer, default=1)
    
    # Coordinate reference system
    crs = Column(String(100))  # WGS84, UTM, etc.
    
    # Upload information
    uploaded_by = Column(Integer, ForeignKey("users.id"))
    uploaded_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    uploader = relationship("User", back_populates="seismic_datasets")
    interpretations = relationship("SeismicInterpretation", back_populates="dataset")
    analyses = relationship("SeismicAnalysis", back_populates="dataset")
    
class SeismicInterpretation(Base):
    __tablename__ = "seismic_interpretations"
    
    id = Column(Integer, primary_key=True, index=True)
    dataset_id = Column(Integer, ForeignKey("seismic_datasets.id"))
    name = Column(String(255), nullable=False)
    description = Column(Text)
    interpretation_type = Column(String(50), nullable=False)  # horizon, fault, salt_body, etc.
    
    # Geometric data stored as JSON
    geometry_data = Column(JSON)  # Store coordinates, points, lines, surfaces
    
    # Interpretation properties
    color = Column(String(7), default="#FF0000")  # hex color code
    opacity = Column(Float, default=1.0)
    thickness = Column(Float, default=1.0)
    
    # Confidence and quality
    confidence_level = Column(Float, default=0.5)  # 0-1 scale
    quality_score = Column(Float)
    
    # Metadata
    interpreter_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    is_active = Column(Boolean, default=True)
    
    # Relationships
    dataset = relationship("SeismicDataset", back_populates="interpretations")
    interpreter = relationship("User", back_populates="seismic_interpretations")
    
class SeismicAnalysis(Base):
    __tablename__ = "seismic_analyses"
    
    id = Column(Integer, primary_key=True, index=True)
    dataset_id = Column(Integer, ForeignKey("seismic_datasets.id"))
    name = Column(String(255), nullable=False)
    description = Column(Text)
    analysis_type = Column(String(100), nullable=False)  # noise_reduction, migration, attribute_analysis, etc.
    
    # Processing parameters
    parameters = Column(JSON)  # Store algorithm parameters
    
    # Results
    result_file_path = Column(String(500))
    result_metadata = Column(JSON)
    
    # Processing information
    algorithm_version = Column(String(50))
    processing_time = Column(Float)  # in seconds
    cpu_usage = Column(Float)
    memory_usage = Column(Float)
    
    # Status
    status = Column(String(50), default="pending")  # pending, running, completed, failed
    progress = Column(Float, default=0.0)  # 0-100
    error_message = Column(Text)
    
    # Metadata
    analyst_id = Column(Integer, ForeignKey("users.id"))
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    dataset = relationship("SeismicDataset", back_populates="analyses")
    analyst = relationship("User", back_populates="seismic_analyses")

class SeismicAttribute(Base):
    __tablename__ = "seismic_attributes"
    
    id = Column(Integer, primary_key=True, index=True)
    dataset_id = Column(Integer, ForeignKey("seismic_datasets.id"))
    name = Column(String(255), nullable=False)
    attribute_type = Column(String(100), nullable=False)  # amplitude, frequency, phase, coherence, etc.
    
    # Attribute data
    data_file_path = Column(String(500))
    computation_parameters = Column(JSON)
    
    # Statistics
    min_value = Column(Float)
    max_value = Column(Float)
    mean_value = Column(Float)
    std_deviation = Column(Float)
    
    # Metadata
    computed_by = Column(Integer, ForeignKey("users.id"))
    computed_at = Column(DateTime, default=func.now())
    
    # Relationships
    dataset = relationship("SeismicDataset")
    computer = relationship("User")

class SeismicSession(Base):
    __tablename__ = "seismic_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    session_name = Column(String(255), nullable=False)
    description = Column(Text)
    
    # Session data
    datasets = Column(JSON)  # List of dataset IDs in session
    viewport_settings = Column(JSON)  # Camera position, zoom, etc.
    display_settings = Column(JSON)  # Color maps, opacity, filters
    
    # Session metadata
    created_at = Column(DateTime, default=func.now())
    last_accessed = Column(DateTime, default=func.now())
    is_shared = Column(Boolean, default=False)
    shared_with = Column(JSON)  # List of user IDs with access
    
    # Relationships
    user = relationship("User", back_populates="seismic_sessions")

# Add relationships to User model (this would be added to user.py)
"""
Add these to the User model:
seismic_datasets = relationship("SeismicDataset", back_populates="uploader")
seismic_interpretations = relationship("SeismicInterpretation", back_populates="interpreter")
seismic_analyses = relationship("SeismicAnalysis", back_populates="analyst")
seismic_sessions = relationship("SeismicSession", back_populates="user")
"""
