from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

# Database URL from environment variables
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    # Fallback to Supabase connection string format
    SUPABASE_URL = os.getenv("SUPABASE_URL", "")
    SUPABASE_DB_PASSWORD = os.getenv("SUPABASE_DB_PASSWORD", "")
    if SUPABASE_URL and SUPABASE_DB_PASSWORD:
        # Extract database connection details from Supabase URL
        host = SUPABASE_URL.replace("https://", "").replace("http://", "")
        DATABASE_URL = f"postgresql://postgres:{SUPABASE_DB_PASSWORD}@db.{host}:5432/postgres"

# Create engine
engine = create_engine(DATABASE_URL, echo=False)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for models
Base = declarative_base()

# Dependency to get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()