import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from app.database.database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="admin") # admin, operator
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Pipeline(Base):
    __tablename__ = "pipelines"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    description = Column(String, nullable=True)
    schedule_cron = Column(String, nullable=True) # e.g. "0 2 * * *"
    schedule_timezone = Column(String, default="UTC")
    is_enabled = Column(Boolean, default=True)
    status = Column(String, default="IDLE") # IDLE, RUNNING, PAUSED
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    configurations = relationship("PipelineConfiguration", back_populates="pipeline", cascade="all, delete-orphan")

class PipelineConfiguration(Base):
    __tablename__ = "pipeline_configurations"
    id = Column(Integer, primary_key=True, index=True)
    pipeline_id = Column(Integer, ForeignKey("pipelines.id"), nullable=False)
    config_key = Column(String, nullable=False) # e.g. "salesforce_objects", "field_mappings"
    config_value = Column(Text, nullable=False) # Store as YAML or JSON string
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    pipeline = relationship("Pipeline", back_populates="configurations")

class ETLExecution(Base):
    __tablename__ = "etl_executions"
    id = Column(Integer, primary_key=True, index=True)
    execution_id = Column(String, unique=True, index=True, nullable=False)
    pipeline_name = Column(String, index=True, nullable=False)
    start_time = Column(DateTime, default=datetime.datetime.utcnow)
    end_time = Column(DateTime, nullable=True)
    status = Column(String, default="RECEIVED") # RECEIVED, NORMALIZED, VALIDATED, ENRICHED, READY, UPLOADED, FAILED, SKIPPED
    records_received = Column(Integer, default=0)
    records_processed = Column(Integer, default=0)
    records_successful = Column(Integer, default=0)
    records_failed = Column(Integer, default=0)
    records_skipped = Column(Integer, default=0)
    execution_duration = Column(Float, default=0.0) # seconds
    error_summary = Column(Text, nullable=True)
    dry_run = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class ETLRecordLog(Base):
    __tablename__ = "etl_record_logs"
    id = Column(Integer, primary_key=True, index=True)
    execution_id = Column(String, ForeignKey("etl_executions.execution_id"), nullable=False)
    source_row = Column(Integer, nullable=False)
    record_identifier = Column(String, nullable=True) # e.g. email or external key
    status = Column(String, nullable=False) # SUCCESS, FAILED, WARNING
    stage = Column(String, nullable=False) # NORMALIZE, ENRICH, TRANSFORM, VALIDATE, LOAD
    error_code = Column(String, nullable=True) # e.g. VALIDATION_ERROR
    error_message = Column(Text, nullable=True)
    salesforce_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class SourceFile(Base):
    __tablename__ = "source_files"
    id = Column(Integer, primary_key=True, index=True)
    file_name = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    md5_hash = Column(String, unique=True, index=True, nullable=False)
    file_size = Column(Integer, nullable=False)
    uploaded_at = Column(DateTime, default=datetime.datetime.utcnow)

class MappingError(Base):
    __tablename__ = "mapping_errors"
    id = Column(Integer, primary_key=True, index=True)
    execution_id = Column(String, ForeignKey("etl_executions.execution_id"), nullable=False)
    source_row = Column(Integer, nullable=False)
    field = Column(String, nullable=False)
    input_value = Column(String, nullable=True)
    error_message = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class ValidationError(Base):
    __tablename__ = "validation_errors"
    id = Column(Integer, primary_key=True, index=True)
    execution_id = Column(String, ForeignKey("etl_executions.execution_id"), nullable=False)
    source_row = Column(Integer, nullable=False)
    field = Column(String, nullable=False)
    input_value = Column(String, nullable=True)
    rule = Column(String, nullable=False)
    error_message = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class SalesforceJob(Base):
    __tablename__ = "salesforce_jobs"
    id = Column(Integer, primary_key=True, index=True)
    execution_id = Column(String, ForeignKey("etl_executions.execution_id"), nullable=False)
    job_id = Column(String, index=True, nullable=False)
    object_name = Column(String, nullable=False)
    operation = Column(String, default="upsert")
    state = Column(String, default="UploadComplete") # Open, UploadComplete, InProgress, JobComplete, Failed, Aborted
    records_processed = Column(Integer, default=0)
    records_failed = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, index=True, nullable=False)
    action = Column(String, nullable=False)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
