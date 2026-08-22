import pandas as pd
import logging
from typing import List, Dict, Any

logger = logging.getLogger("salesforce-etl.utils.csv")

def read_csv_file(filepath: str) -> List[Dict[str, Any]]:
    """Reads a CSV file and returns it as a list of dictionaries (rows)."""
    try:
        df = pd.read_csv(filepath, dtype=str)
        # Replace NaN with None
        df = df.where(pd.notnull(df), None)
        return df.to_dict(orient="records")
    except Exception as exc:
        logger.error(f"Error reading CSV file {filepath}: {str(exc)}")
        raise

def write_csv_file(filepath: str, data: List[Dict[str, Any]]):
    """Writes a list of dictionaries to a CSV file."""
    try:
        df = pd.DataFrame(data)
        df.to_csv(filepath, index=False)
    except Exception as exc:
        logger.error(f"Error writing CSV file {filepath}: {str(exc)}")
        raise
