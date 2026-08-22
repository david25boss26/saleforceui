import os
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from app.database.database import get_db
from app.database.models import Pipeline
from app.core.config_manager import ConfigManager
from app.etl.pipeline import ETLPipeline

router = APIRouter(prefix="/pipelines", tags=["Pipelines"])

class RunPayload(BaseModel):
    filepath: str # Absolute path of the uploaded file on disk

@router.get("")
def list_pipelines(db: Session = Depends(get_db)):
    """Lists defined pipelines from DB sync with YAML sources configuration."""
    # Synchronize YAML config sources with database Pipeline table
    yaml_cfg = ConfigManager.get_field_mappings()
    sources = yaml_cfg.get("sources", [])
    
    pipelines = []
    for src in sources:
        name = src["name"]
        country = src.get("country", "")
        event = src.get("event", "")
        
        db_pipe = db.query(Pipeline).filter_by(name=name).first()
        if not db_pipe:
            # Create pipeline record
            db_pipe = Pipeline(
                name=name,
                description=f"ETL pipeline for {country} - {event}",
                schedule_cron="0 2 * * *", # default cron
                schedule_timezone="UTC",
                is_enabled=True,
                status="IDLE"
            )
            db.add(db_pipe)
            db.commit()
            db.refresh(db_pipe)
            
        pipelines.append(db_pipe)
        
    return pipelines

@router.post("/{pipeline_name}/run")
def run_pipeline_api(pipeline_name: str, payload: RunPayload, db: Session = Depends(get_db)):
    """Runs a pipeline manually with the specified source file."""
    filepath = payload.filepath
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail=f"Source file not found at path: {filepath}")
        
    # Get pipeline model
    db_pipe = db.query(Pipeline).filter_by(name=pipeline_name).first()
    if db_pipe:
        db_pipe.status = "RUNNING"
        db.commit()

    try:
        pipeline = ETLPipeline(db)
        summary = pipeline.run(filepath=filepath, source_name=pipeline_name, dry_run=False)
        
        if db_pipe:
            db_pipe.status = "IDLE"
            db.commit()
            
        return summary
    except Exception as exc:
        if db_pipe:
            db_pipe.status = "IDLE"
            db.commit()
        raise HTTPException(status_code=500, detail=str(exc))

@router.post("/{pipeline_name}/dry-run")
def dry_run_pipeline_api(pipeline_name: str, payload: RunPayload, db: Session = Depends(get_db)):
    """Runs a pipeline in Dry-Run mode with the specified source file."""
    filepath = payload.filepath
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail=f"Source file not found at path: {filepath}")

    try:
        pipeline = ETLPipeline(db)
        summary = pipeline.run(filepath=filepath, source_name=pipeline_name, dry_run=True)
        return summary
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@router.post("/{pipeline_name}/pause")
def pause_pipeline(pipeline_name: str, db: Session = Depends(get_db)):
    """Pauses scheduling for a pipeline."""
    db_pipe = db.query(Pipeline).filter_by(name=pipeline_name).first()
    if not db_pipe:
        raise HTTPException(status_code=404, detail="Pipeline not found")
        
    db_pipe.is_enabled = False
    db_pipe.status = "PAUSED"
    db.commit()
    return {"status": "success", "message": f"Pipeline '{pipeline_name}' paused."}

@router.post("/{pipeline_name}/resume")
def resume_pipeline(pipeline_name: str, db: Session = Depends(get_db)):
    """Resumes scheduling for a pipeline."""
    db_pipe = db.query(Pipeline).filter_by(name=pipeline_name).first()
    if not db_pipe:
        raise HTTPException(status_code=404, detail="Pipeline not found")
        
    db_pipe.is_enabled = True
    db_pipe.status = "IDLE"
    db.commit()
    return {"status": "success", "message": f"Pipeline '{pipeline_name}' resumed."}
