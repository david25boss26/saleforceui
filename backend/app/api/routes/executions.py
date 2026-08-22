import os
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List
from app.database.database import get_db
from app.database.models import ETLExecution, ETLRecordLog, MappingError, ValidationError
from app.core.config import settings

router = APIRouter(prefix="/executions", tags=["Executions"])

@router.get("")
def list_executions(db: Session = Depends(get_db)):
    """Returns execution log history ordered by date."""
    execs = db.query(ETLExecution).order_by(ETLExecution.start_time.desc()).all()
    return execs

@router.get("/{execution_id}")
def get_execution_details(execution_id: str, db: Session = Depends(get_db)):
    """Returns general metrics and row log list for a specific execution."""
    exec_info = db.query(ETLExecution).filter_by(execution_id=execution_id).first()
    if not exec_info:
        raise HTTPException(status_code=404, detail="Execution not found")
        
    logs = db.query(ETLRecordLog).filter_by(execution_id=execution_id).order_by(ETLRecordLog.source_row.asc()).all()
    return {
        "summary": exec_info,
        "logs": logs
    }

@router.get("/{execution_id}/errors")
def get_execution_errors(execution_id: str, db: Session = Depends(get_db)):
    """Returns mapping and validation errors for drill-down tables."""
    map_errs = db.query(MappingError).filter_by(execution_id=execution_id).all()
    val_errs = db.query(ValidationError).filter_by(execution_id=execution_id).all()
    return {
        "mapping_errors": map_errs,
        "validation_errors": val_errs
    }

@router.get("/{execution_id}/download")
def download_execution_report(execution_id: str, type: str = Query(..., description="Report type: successful, failed, validation, salesforce, summary")):
    """Downloads execution spreadsheet files."""
    filename_map = {
        "successful": f"successful_records_{execution_id}.xlsx",
        "failed": f"failed_records_{execution_id}.xlsx",
        "validation": f"validation_errors_{execution_id}.xlsx",
        "salesforce": f"salesforce_errors_{execution_id}.xlsx",
        "summary": f"execution_summary_{execution_id}.xlsx"
    }
    
    if type not in filename_map:
        raise HTTPException(status_code=400, detail=f"Invalid report type. Supported: {list(filename_map.keys())}")
        
    filename = filename_map[type]
    subfolder = "errors" if type in ["failed", "validation", "salesforce"] else "output"
    
    filepath = os.path.join(settings.DATA_DIR, subfolder, filename)
    
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail=f"Report file {filename} not found. Perhaps no records fell into this category.")
        
    return FileResponse(filepath, filename=filename, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
