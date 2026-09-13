import os
import uuid
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Query, Body
from fastapi.responses import FileResponse
from pydantic import BaseModel
from app.core.config import settings
from app.integrations.salesforce.query_importer import SalesforceQueryImporter
from app.integrations.salesforce.client import get_salesforce_client

router = APIRouter(prefix="/salesforce", tags=["Salesforce Queries & Extraction"])


class SOQLQueryRequest(BaseModel):
    query: str
    username: Optional[str] = None
    password: Optional[str] = None
    security_token: Optional[str] = None
    session_id: Optional[str] = None
    domain: Optional[str] = None
    limit: Optional[int] = 100 # For preview


class SOQLExportRequest(BaseModel):
    query: str
    output_filename: Optional[str] = None
    export_format: str = "excel" # 'excel' or 'csv'
    sheet_name: Optional[str] = "Salesforce Data"
    username: Optional[str] = None
    password: Optional[str] = None
    security_token: Optional[str] = None
    session_id: Optional[str] = None
    domain: Optional[str] = None


@router.post("/query")
def run_soql_query(payload: SOQLQueryRequest):
    """
    Executes a custom SOQL query against Salesforce and returns preview data with column definitions.
    Supports relationship queries (e.g. OCE__meeting__r.recordtype.name) with automatic flattening.
    """
    try:
        importer = SalesforceQueryImporter()
        
        # Connect with provided or default credentials
        client = None
        if payload.session_id or (payload.username and payload.password):
            client = importer.get_client(
                username=payload.username,
                password=payload.password,
                security_token=payload.security_token,
                session_id=payload.session_id,
                domain=payload.domain
            )
        
        records = importer.execute_query(payload.query, sf_client=client)
        
        columns = []
        if records:
            # Extract unique list of columns across records
            col_set = set()
            for r in records:
                col_set.update(r.keys())
            columns = sorted(list(col_set))
            
        preview_records = records[:payload.limit] if payload.limit else records

        return {
            "status": "success",
            "total_records": len(records),
            "returned_records": len(preview_records),
            "columns": columns,
            "data": preview_records
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Salesforce query failed: {str(exc)}")


@router.post("/query/export")
def export_soql_query(payload: SOQLExportRequest):
    """
    Executes SOQL query and exports directly to an Excel (.xlsx) or CSV file.
    """
    try:
        importer = SalesforceQueryImporter()
        
        client = None
        if payload.session_id or (payload.username and payload.password):
            client = importer.get_client(
                username=payload.username,
                password=payload.password,
                security_token=payload.security_token,
                session_id=payload.session_id,
                domain=payload.domain
            )
            
        exports_dir = os.path.join(settings.DATA_DIR, "exports")
        os.makedirs(exports_dir, exist_ok=True)
        
        ext = "xlsx" if payload.export_format.lower() == "excel" else "csv"
        fname = payload.output_filename or f"salesforce_export_{uuid.uuid4().hex[:8]}.{ext}"
        if not fname.endswith(f".{ext}"):
            fname = f"{fname}.{ext}"
            
        out_path = os.path.join(exports_dir, fname)
        
        if payload.export_format.lower() == "csv":
            importer.query_to_csv(payload.query, out_path, sf_client=client)
        else:
            importer.query_to_excel(
                payload.query,
                out_path,
                sheet_name=payload.sheet_name or "Salesforce Data",
                sf_client=client
            )
            
        return {
            "status": "success",
            "filename": fname,
            "filepath": out_path,
            "download_url": f"/api/files/download?filepath={out_path}"
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Salesforce export failed: {str(exc)}")
