import os
import logging
import pandas as pd
from typing import List, Dict, Any
from app.core.config import settings
from app.core.config_manager import ConfigManager
from app.integrations.salesforce.client import get_salesforce_client
from app.integrations.salesforce.query_importer import extract_records_to_list
from app.utils.excel import write_excel_file

logger = logging.getLogger("salesforce-etl.etl.extractor")

class SalesforceExtractor:
    def __init__(self):
        self.sf_client = get_salesforce_client()

    def extract_reference_data(self) -> Dict[str, str]:
        """
        Executes SOQL queries configured in salesforce_objects.yaml,
        retrieves records, flattens them (including relationship fields), and saves to Excel files.
        
        Returns:
            Dict[object_name, filepath]
        """
        objects = ConfigManager.get_salesforce_objects()
        exports_dir = os.path.join(settings.DATA_DIR, "salesforce_exports")
        os.makedirs(exports_dir, exist_ok=True)
        
        extracted_files = {}

        for obj in objects:
            name = obj["name"]
            sf_obj_name = obj["salesforce_object"]
            soql = obj["soql"]
            filename = obj["output_file"]
            filepath = os.path.join(exports_dir, filename)
            
            logger.info(f"Extracting reference data for '{name}' ({sf_obj_name}) using SOQL query...")
            
            try:
                # Query Salesforce
                result = self.sf_client.query_all(soql)
                records = result.get("records", [])
                
                # Recursively flatten records (removing attributes and unrolling relationship dicts)
                flattened_records = extract_records_to_list(records)
                    
                # If records is empty, write empty DataFrame with expected columns if possible
                if not flattened_records:
                    logger.warning(f"No records found for query on '{sf_obj_name}'. Creating empty reference file.")
                    # Write empty Excel sheet
                    write_excel_file(filepath, [{"Id": None}])
                else:
                    write_excel_file(filepath, flattened_records)
                    
                logger.info(f"Saved {len(flattened_records)} records to {filepath}")
                extracted_files[name] = filepath
                
            except Exception as exc:
                logger.exception(f"Failed to extract reference data for '{name}'")
                raise RuntimeError(f"Extraction failed for {name}: {str(exc)}") from exc
                
        return extracted_files
