import os
import logging
from typing import List, Dict, Any
from app.core.config import settings
from app.core.config_manager import ConfigManager
from app.utils.excel import read_excel_file

logger = logging.getLogger("salesforce-etl.etl.enricher")

class DataEnricher:
    def __init__(self):
        self.reference_cache: Dict[str, List[Dict[str, Any]]] = {}

    def _load_reference_data(self, reference_name: str) -> List[Dict[str, Any]]:
        """Loads and caches reference data from Salesforce exports."""
        if reference_name in self.reference_cache:
            return self.reference_cache[reference_name]
            
        objects_cfg = ConfigManager.get_salesforce_objects()
        obj_info = next((o for o in objects_cfg if o["name"] == reference_name), None)
        
        if not obj_info:
            logger.error(f"Reference '{reference_name}' not defined in salesforce_objects.yaml")
            return []
            
        filename = obj_info["output_file"]
        filepath = os.path.join(settings.DATA_DIR, "salesforce_exports", filename)
        
        if not os.path.exists(filepath):
            logger.warning(f"Reference file not found at {filepath}. Attempting to load from sample data as fallback.")
            fallback_path = os.path.join(settings.SAMPLE_DATA_DIR, filename)
            if os.path.exists(fallback_path):
                filepath = fallback_path
            else:
                logger.error(f"Reference file not found at fallback {fallback_path}")
                return []
                
        try:
            records = read_excel_file(filepath)
            self.reference_cache[reference_name] = records
            logger.info(f"Loaded {len(records)} reference records for '{reference_name}' from {filepath}")
            return records
        except Exception as exc:
            logger.error(f"Failed to load reference {reference_name}: {str(exc)}")
            return []

    def enrich(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Enriches canonical records with Salesforce IDs by looking up fields against Salesforce reference datasets.
        """
        mappings_cfg = ConfigManager.get_field_mappings()
        
        # Default configuration-driven lookup definition
        lookups = mappings_cfg.get("lookups", [
            {
                "name": "product_lookup",
                "source_field": "product_code",
                "reference": "products",
                "reference_key": "ProductCode",
                "output_field": "product_sfdc_id"
            },
            {
                "name": "budget_lookup",
                "source_field": "budget_code",
                "reference": "budgets",
                "reference_key": "Budget_Code__c",
                "output_field": "budget_sfdc_id"
            },
            {
                "name": "checklist_lookup",
                "source_field": "checklist_code",
                "reference": "checklists",
                "reference_key": "Checklist_Code__c",
                "output_field": "checklist_sfdc_id"
            }
        ])

        for rec in records:
            if "_lookup_errors" not in rec:
                rec["_lookup_errors"] = []
            rec["_lookup_failed"] = False
            
            for lk in lookups:
                name = lk["name"]
                src_field = lk["source_field"]
                ref_name = lk["reference"]
                ref_key = lk["reference_key"]
                out_field = lk["output_field"]
                
                input_value = rec.get(src_field)
                
                # If there's no input value, check if required in field mappings.
                # If not required, we can skip lookup and output None.
                if input_value is None or str(input_value).strip() == "":
                    rec[out_field] = None
                    continue
                    
                input_val_str = str(input_value).strip().lower()
                
                # Fetch reference data
                ref_data = self._load_reference_data(ref_name)
                
                matched_id = None
                for ref_rec in ref_data:
                    ref_val = ref_rec.get(ref_key)
                    if ref_val is not None:
                        ref_val_str = str(ref_val).strip().lower()
                        if input_val_str == ref_val_str:
                            matched_id = ref_rec.get("Id")
                            break
                            
                if matched_id:
                    rec[out_field] = matched_id
                else:
                    rec[out_field] = None
                    rec["_lookup_failed"] = True
                    rec["_lookup_errors"].append({
                        "lookup_name": name,
                        "input_value": input_value,
                        "expected_match": f"'{ref_key}' in '{ref_name}'",
                        "error_reason": f"Value '{input_value}' could not be resolved to a Salesforce ID"
                    })
                    
        return records
