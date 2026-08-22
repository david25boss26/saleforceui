import logging
from typing import List, Dict, Any, Tuple
from app.core.config_manager import ConfigManager

logger = logging.getLogger("salesforce-etl.forms.normalizer")

class FormNormalizer:
    @staticmethod
    def detect_source(headers: List[str]) -> str:
        """
        Attempts to detect which source configuration matches the headers based on the number of alias matches.
        """
        mappings_cfg = ConfigManager.get_field_mappings()
        sources = mappings_cfg.get("sources", [])
        
        best_source = None
        best_match_count = -1
        
        # Clean headers for comparison
        clean_headers = {h.strip().lower() for h in headers if h}
        
        for src in sources:
            match_count = 0
            # For each canonical mapping, check if any alias is in the headers
            for canonical_name, rule in src.get("canonical_mappings", {}).items():
                aliases = [a.lower() for a in rule.get("aliases", [])]
                # If an alias or canonical name matches one of the headers, increment
                if canonical_name.lower() in clean_headers or any(a in clean_headers for a in aliases):
                    match_count += 1
            
            if match_count > best_match_count:
                best_match_count = match_count
                best_source = src.get("name")
                
        # Return best match if we got at least 1 field matched
        if best_match_count > 0:
            logger.info(f"Auto-detected source configuration: {best_source} with {best_match_count} header matches")
            return best_source
            
        # Fallback to the first source if nothing matches
        if sources:
            logger.warning(f"Could not auto-detect source from headers {headers}. Defaulting to {sources[0].get('name')}")
            return sources[0].get("name")
        raise ValueError("No source configurations found in field_mappings.yaml")

    @staticmethod
    def normalize(records: List[Dict[str, Any]], source_name: str = None) -> Dict[str, Any]:
        """
        Normalizes raw records into canonical records using config-driven field aliases.
        
        Returns:
            {
                "records": List[Dict[str, Any]], # Canonicalized records
                "source_name": str,
                "country": str,
                "event": str,
                "ingestion_report": {
                    "mapped_fields": List[str],
                    "unmapped_fields": List[str],
                    "missing_fields": List[str]
                }
            }
        """
        if not records:
            return {
                "records": [],
                "source_name": source_name or "unknown",
                "country": "unknown",
                "event": "unknown",
                "ingestion_report": {"mapped_fields": [], "unmapped_fields": [], "missing_fields": []}
            }

        # Check headers of the first record
        headers = list(records[0].keys())
        
        if not source_name:
            source_name = FormNormalizer.detect_source(headers)
            
        mappings_cfg = ConfigManager.get_field_mappings()
        source_cfg = next((s for s in mappings_cfg.get("sources", []) if s["name"] == source_name), None)
        if not source_cfg:
            raise ValueError(f"Source configuration '{source_name}' not found in field_mappings.yaml")
            
        country = source_cfg.get("country", "Unknown")
        event = source_cfg.get("event", "Unknown")
        canonical_rules = source_cfg.get("canonical_mappings", {})
        
        # Build maps for lookup: Alias (lowercased) -> Canonical Field Name
        alias_to_canonical = {}
        for canonical, rule in canonical_rules.items():
            alias_to_canonical[canonical.lower()] = canonical
            for alias in rule.get("aliases", []):
                alias_to_canonical[alias.strip().lower()] = canonical
                
        mapped_fields = set()
        unmapped_fields = set()
        missing_fields = set()
        
        # Determine missing required fields in schema headers
        input_headers_lower = {h.strip().lower() for h in headers}
        for canonical, rule in canonical_rules.items():
            if rule.get("required", False):
                # Is the required field or any of its aliases present?
                aliases_lower = {a.strip().lower() for a in rule.get("aliases", [])}
                aliases_lower.add(canonical.lower())
                if not aliases_lower.intersection(input_headers_lower):
                    missing_fields.add(canonical)
                    
        normalized_records = []
        for idx, raw_rec in enumerate(records):
            norm_rec = {
                "_row_number": idx + 2, # standard Excel row (1-indexed + header)
                "country": country,
                "event": event,
            }
            
            # Keep track of what we matched in this record
            for raw_key, raw_val in raw_rec.items():
                clean_key = str(raw_key).strip().lower()
                canonical_name = alias_to_canonical.get(clean_key)
                
                if canonical_name:
                    norm_rec[canonical_name] = raw_val
                    mapped_fields.add(canonical_name)
                else:
                    # Save unmapped fields to preserve original data
                    norm_rec[f"_unmapped_{raw_key}"] = raw_val
                    unmapped_fields.add(raw_key)
            
            # Fill missing canonical columns with None if not already populated
            for canonical in canonical_rules.keys():
                if canonical not in norm_rec:
                    norm_rec[canonical] = None
                    
            normalized_records.append(norm_rec)
            
        return {
            "records": normalized_records,
            "source_name": source_name,
            "country": country,
            "event": event,
            "ingestion_report": {
                "mapped_fields": sorted(list(mapped_fields)),
                "unmapped_fields": sorted(list(unmapped_fields)),
                "missing_fields": sorted(list(missing_fields))
            }
        }
