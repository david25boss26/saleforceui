import pandas as pd
import logging
from typing import List, Dict, Any

logger = logging.getLogger("salesforce-etl.utils.excel")

def read_excel_file(filepath: str) -> List[Dict[str, Any]]:
    """Reads an Excel file and returns it as a list of dictionaries (rows)."""
    try:
        df = pd.read_excel(filepath, dtype=str) # read everything as string first for safety
        # Replace NaN with None
        df = df.where(pd.notnull(df), None)
        return df.to_dict(orient="records")
    except Exception as exc:
        logger.error(f"Error reading Excel file {filepath}: {str(exc)}")
        raise

def write_excel_file(filepath: str, data: List[Dict[str, Any]]):
    """Writes a list of dictionaries to an Excel file."""
    try:
        df = pd.DataFrame(data)
        df.to_excel(filepath, index=False, engine="openpyxl")
    except Exception as exc:
        logger.error(f"Error writing Excel file {filepath}: {str(exc)}")
        raise
