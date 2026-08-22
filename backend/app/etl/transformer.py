import logging
from typing import List, Dict, Any
from app.core.config_manager import ConfigManager

logger = logging.getLogger("salesforce-etl.etl.transformer")

class DataTransformer:
    def __init__(self):
        self.trans_config = ConfigManager.get_transformation_rules()

    def transform(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Applies configured field operations on records.
        """
        rules = self.trans_config.get("transformations", {})
        
        for rec in records:
            # We don't want to transform internal fields or fields of rows that have already failed key phases
            for field, rule in rules.items():
                if field not in rec:
                    # Apply default if configured
                    if "default" in rule:
                        rec[field] = rule["default"]
                    continue
                    
                val = rec[field]
                if val is None:
                    if "default" in rule:
                        rec[field] = rule["default"]
                    continue
                    
                op = rule.get("operation")
                val_str = str(val).strip()
                
                if op == "trim":
                    rec[field] = val_str
                elif op == "lowercase":
                    rec[field] = val_str.lower()
                elif op == "uppercase":
                    rec[field] = val_str.upper()
                elif op == "title_case":
                    rec[field] = val_str.title()
                elif op == "decimal":
                    try:
                        rec[field] = float(val_str.replace(",", ""))
                    except ValueError:
                        # Keep original so validator reports data type error
                        pass
                elif op == "map":
                    mapping_values = rule.get("values", {})
                    # Exact or case-insensitive string match mapping
                    matched = False
                    for k, mapped_val in mapping_values.items():
                        if str(k).strip().lower() == val_str.lower():
                            rec[field] = mapped_val
                            matched = True
                            break
                    if not matched and "default" in rule:
                        rec[field] = rule["default"]
                        
        return records
