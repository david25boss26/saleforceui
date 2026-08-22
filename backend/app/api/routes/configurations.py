import yaml
from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel
from app.core.config_manager import ConfigManager, load_yaml_config

router = APIRouter(prefix="/config", tags=["Configuration"])

class ConfigUpdate(BaseModel):
    key: str # e.g. "salesforce_objects"
    value: str # YAML content as string

@router.get("")
def get_all_config():
    """Returns YAML content of all configurations."""
    # Try to load current overrides or fallback to yaml files
    return {
        "salesforce_objects": yaml.safe_dump({"objects": ConfigManager.get_salesforce_objects()}),
        "field_mappings": yaml.safe_dump(ConfigManager.get_field_mappings()),
        "validation_rules": yaml.safe_dump(ConfigManager.get_validation_rules()),
        "transformation_rules": yaml.safe_dump(ConfigManager.get_transformation_rules()),
        "scheduler": yaml.safe_dump(ConfigManager.get_scheduler_config())
    }

@router.put("")
def update_config(payload: ConfigUpdate):
    """Saves a configuration override."""
    key = payload.key
    value = payload.value
    
    if key not in ["salesforce_objects", "field_mappings", "validation_rules", "transformation_rules", "scheduler"]:
        raise HTTPException(status_code=400, detail=f"Invalid configuration key: {key}")
        
    try:
        # Validate that it is valid YAML
        parsed = yaml.safe_load(value)
        if parsed is None:
            raise ValueError("YAML content is empty")
            
        ConfigManager.save_override(key, value)
        return {"status": "success", "message": f"Configuration '{key}' updated successfully"}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid YAML format: {str(exc)}")
