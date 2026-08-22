import os
import shutil
import logging
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.orm import Session
from app.core.config import settings
from app.database.database import get_db
from app.database.models import SourceFile
from app.utils.hashing import calculate_file_hash

logger = logging.getLogger("salesforce-etl.api.files")
router = APIRouter(prefix="/files", tags=["Files"])

@router.post("/upload")
async def upload_file(file: UploadFile = File(...), db: Session = Depends(get_db)):
    # Validate filename extension
    filename = file.filename
    if not filename.endswith((".xlsx", ".xls", ".csv")):
        raise HTTPException(status_code=400, detail="Only Excel (.xlsx, .xls) and CSV (.csv) files are supported.")

    input_dir = os.path.join(settings.DATA_DIR, "input")
    os.makedirs(input_dir, exist_ok=True)
    
    filepath = os.path.join(input_dir, filename)
    
    # Save file temporarily
    try:
        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as exc:
        logger.exception("Failed to write uploaded file")
        raise HTTPException(status_code=500, detail=f"Could not save file: {str(exc)}")

    # Calculate hash
    file_hash = calculate_file_hash(filepath)
    
    # Check if duplicate
    existing_file = db.query(SourceFile).filter_by(md5_hash=file_hash).first()
    is_duplicate = existing_file is not None

    return {
        "filename": filename,
        "filepath": filepath,
        "hash": file_hash,
        "is_duplicate": is_duplicate,
        "message": "File uploaded successfully. Note: This file has already been processed before." if is_duplicate else "File uploaded successfully."
    }
