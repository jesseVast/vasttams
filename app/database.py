from sqlalchemy import create_engine, Column, String, Integer, DateTime, Boolean, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from datetime import datetime
import os
from typing import Generator

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./tams.db")

# Create engine
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for models
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Database Models
class SourceModel(Base):
    """Source database model"""
    __tablename__ = "sources"
    
    id = Column(PGUUID, primary_key=True, index=True)
    format = Column(String, nullable=False)
    label = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    created_by = Column(String, nullable=True)
    updated_by = Column(String, nullable=True)
    created = Column(DateTime, default=datetime.utcnow)
    updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    tags = Column(JSON, nullable=True)
    source_collection = Column(JSON, nullable=True)
    collected_by = Column(JSON, nullable=True)


class FlowModel(Base):
    """Flow database model"""
    __tablename__ = "flows"
    
    id = Column(PGUUID, primary_key=True, index=True)
    source_id = Column(PGUUID, nullable=False, index=True)
    format = Column(String, nullable=False)
    codec = Column(String, nullable=False)
    label = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    created_by = Column(String, nullable=True)
    updated_by = Column(String, nullable=True)
    created = Column(DateTime, default=datetime.utcnow)
    updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    tags = Column(JSON, nullable=True)
    container = Column(String, nullable=True)
    read_only = Column(Boolean, default=False)
    
    # Video specific fields
    frame_width = Column(Integer, nullable=True)
    frame_height = Column(Integer, nullable=True)
    frame_rate = Column(String, nullable=True)
    interlace_mode = Column(String, nullable=True)
    color_sampling = Column(String, nullable=True)
    color_space = Column(String, nullable=True)
    transfer_characteristics = Column(String, nullable=True)
    color_primaries = Column(String, nullable=True)
    
    # Audio specific fields
    sample_rate = Column(Integer, nullable=True)
    bits_per_sample = Column(Integer, nullable=True)
    channels = Column(Integer, nullable=True)
    
    # Multi flow specific fields
    flow_collection = Column(JSON, nullable=True)


class FlowSegmentModel(Base):
    """Flow segment database model"""
    __tablename__ = "flow_segments"
    
    id = Column(PGUUID, primary_key=True, index=True)
    flow_id = Column(PGUUID, nullable=False, index=True)
    object_id = Column(String, nullable=False, index=True)
    timerange = Column(String, nullable=False)
    ts_offset = Column(String, nullable=True)
    last_duration = Column(String, nullable=True)
    sample_offset = Column(Integer, nullable=True)
    sample_count = Column(Integer, nullable=True)
    get_urls = Column(JSON, nullable=True)
    key_frame_count = Column(Integer, nullable=True)
    created = Column(DateTime, default=datetime.utcnow)


class WebhookModel(Base):
    """Webhook database model"""
    __tablename__ = "webhooks"
    
    id = Column(PGUUID, primary_key=True, index=True)
    url = Column(String, nullable=False)
    api_key_name = Column(String, nullable=False)
    api_key_value = Column(String, nullable=False)
    events = Column(JSON, nullable=False)
    created = Column(DateTime, default=datetime.utcnow)
    updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class DeletionRequestModel(Base):
    """Deletion request database model"""
    __tablename__ = "deletion_requests"
    
    id = Column(String, primary_key=True, index=True)
    flow_id = Column(PGUUID, nullable=False, index=True)
    timerange = Column(String, nullable=False)
    status = Column(String, nullable=False, default="pending")
    created = Column(DateTime, default=datetime.utcnow)
    updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# Create all tables
def create_tables():
    """Create all database tables"""
    Base.metadata.create_all(bind=engine)