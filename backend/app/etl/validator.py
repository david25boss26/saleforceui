import re
import logging
from typing import List, Dict, Any, Tuple
from app.core.config_manager import ConfigManager

logger = logging.getLogger("salesforce-etl.etl.validator")

class DataValidator:
    EMAIL_REGEX = re.compile(r'^[\w\.-]+@[\w\.-]+\.\w+$')

    def __init__(self):
        self.validation_config = ConfigManager.get_validation_rules()
        self.mappings_config = ConfigManager.get_field_mappings()

    def validate(self, records: List[Dict[str, Any]], source_name: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Validates canonicalized records against data types, business rules, and duplicate constraints.
        
        Returns:
            Tuple[valid_records, invalid_records]
        """
        # Load rules
        rules = self.validation_config.get("validations", {})
        type_rules = rules.get("types", {})
        business_rules = rules.get("business_rules", [])
        dup_keys = rules.get("duplicate_key", ["email", "product_code", "event"])
        
        # Load source-specific required fields
        sources = self.mappings_config.get("sources", [])
        source_cfg = next((s for s in sources if s["name"] == source_name), None)
        required_fields = []
        if source_cfg:
            required_fields = [
                field for field, rule in source_cfg.get("canonical_mappings", {}).items()
                if rule.get("required", False)
            ]

        seen_keys = set()
        valid_records = []
        invalid_records = []

        for rec in records:
            if "_validation_errors" not in rec:
                rec["_validation_errors"] = []
            rec["_validation_failed"] = False
            rec["_is_duplicate"] = False

            row_num = rec.get("_row_number", "?")

            # 1. Required fields validation
            for req_field in required_fields:
                val = rec.get(req_field)
                if val is None or str(val).strip() == "":
                    rec["_validation_failed"] = True
                    rec["_validation_errors"].append({
                        "field": req_field,
                        "input_value": val,
                        "rule": "required",
                        "error_message": f"Required field '{req_field}' is missing"
                    })

            # 2. Data type validation
            for field, expected_type in type_rules.items():
                val = rec.get(field)
                if val is None or str(val).strip() == "":
                    continue # Skip empty fields here (required checks handled it if needed)
                    
                if expected_type == "email":
                    if not self.EMAIL_REGEX.match(str(val).strip()):
                        rec["_validation_failed"] = True
                        rec["_validation_errors"].append({
                            "field": field,
                            "input_value": val,
                            "rule": "email_format",
                            "error_message": f"Field '{field}' must be a valid email format"
                        })
                elif expected_type == "numeric":
                    try:
                        float(str(val).replace(",", "").strip())
                    except ValueError:
                        rec["_validation_failed"] = True
                        rec["_validation_errors"].append({
                            "field": field,
                            "input_value": val,
                            "rule": "numeric_format",
                            "error_message": f"Field '{field}' must be a numeric value"
                        })

            # 3. Business rule validation
            for br in business_rules:
                field = br.get("field")
                op = br.get("operator")
                target_val = br.get("value")
                msg = br.get("message", f"Business rule failed: {field} {op} {target_val}")
                
                val = rec.get(field)
                if val is None or str(val).strip() == "":
                    continue
                    
                # Try to parse as numbers
                try:
                    num_val = float(str(val).replace(",", "").strip())
                    num_target = float(target_val)
                    
                    rule_failed = False
                    if op == ">=" and not (num_val >= num_target):
                        rule_failed = True
                    elif op == ">" and not (num_val > num_target):
                        rule_failed = True
                    elif op == "<=" and not (num_val <= num_target):
                        rule_failed = True
                    elif op == "<" and not (num_val < num_target):
                        rule_failed = True
                    elif op == "==" and not (num_val == num_target):
                        rule_failed = True
                    elif op == "!=" and not (num_val != num_target):
                        rule_failed = True
                        
                    if rule_failed:
                        rec["_validation_failed"] = True
                        rec["_validation_errors"].append({
                            "field": field,
                            "input_value": val,
                            "rule": f"business_rule_{op}",
                            "error_message": msg
                        })
                except ValueError:
                    # Non-numeric values skip numeric business rules or fail them if they should be numbers
                    pass

            # 4. Duplicate checks (internal to this batch)
            # Create duplicate key string
            dup_vals = []
            for k in dup_keys:
                val = rec.get(k)
                dup_vals.append(str(val).strip().lower() if val is not None else "")
            dup_hash = "|".join(dup_vals)
            
            # If all dup key values are empty, we don't treat it as a duplicate group
            if any(v != "" for v in dup_vals):
                if dup_hash in seen_keys:
                    rec["_validation_failed"] = True
                    rec["_is_duplicate"] = True
                    rec["_validation_errors"].append({
                        "field": "+".join(dup_keys),
                        "input_value": dup_hash,
                        "rule": "duplicate_check",
                        "error_message": f"Duplicate record detected in batch based on key: {dict(zip(dup_keys, [rec.get(k) for k in dup_keys]))}"
                    })
                else:
                    seen_keys.add(dup_hash)

            # Separate records
            # If lookup failed, or validation failed, or it's a duplicate, we mark it as invalid
            if rec.get("_lookup_failed", False) or rec["_validation_failed"]:
                invalid_records.append(rec)
            else:
                valid_records.append(rec)
                
        return valid_records, invalid_records
