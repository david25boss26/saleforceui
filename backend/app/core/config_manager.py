import os
import yaml
import logging
from typing import Dict, Any, List
from app.core.config import settings
from app.database.database import SessionLocal
from app.database.models import PipelineConfiguration, Pipeline

logger = logging.getLogger("salesforce-etl.config-manager")

def load_yaml_config(filename: str) -> Dict[str, Any]:
    """Loads a configuration from the yaml folder."""
    path = os.path.join(settings.CONFIG_DIR, filename)
    if not os.path.exists(path):
        logger.warning(f"Config file not found at {path}, returning empty dict")
        return {}
    with open(path, "r", encoding="utf-8") as f:
        try:
            return yaml.safe_load(f) or {}
        except Exception as exc:
            logger.error(f"Error reading YAML file {path}: {str(exc)}")
            raise

class ConfigManager:
    @staticmethod
    def get_salesforce_objects() -> List[Dict[str, Any]]:
        """Gets configured Salesforce extraction objects."""
        db = SessionLocal()
        try:
            # Check db override
            db_config = db.query(PipelineConfiguration).filter_by(config_key="salesforce_objects").first()
            if db_config:
                return yaml.safe_load(db_config.config_value).get("objects", [])
        except Exception as exc:
            logger.warning(f"Could not read salesforce_objects override from DB: {str(exc)}")
        finally:
            db.close()
            
        # Fallback to local file
        return load_yaml_config("salesforce_objects.yaml").get("objects", [])

    @staticmethod
    def get_field_mappings() -> Dict[str, Any]:
        """Gets field mapping rules from YAML or DB override."""
        db = SessionLocal()
        try:
            db_config = db.query(PipelineConfiguration).filter_by(config_key="field_mappings").first()
            if db_config:
                return yaml.safe_load(db_config.config_value)
        except Exception as exc:
            logger.warning(f"Could not read field_mappings override from DB: {str(exc)}")
        finally:
            db.close()
            
        return load_yaml_config("field_mappings.yaml")

    @staticmethod
    def get_validation_rules() -> Dict[str, Any]:
        """Gets validation rules."""
        db = SessionLocal()
        try:
            db_config = db.query(PipelineConfiguration).filter_by(config_key="validation_rules").first()
            if db_config:
                return yaml.safe_load(db_config.config_value)
        except Exception as exc:
            logger.warning(f"Could not read validation_rules override from DB: {str(exc)}")
        finally:
            db.close()
            
        return load_yaml_config("validation_rules.yaml")

    @staticmethod
    def get_transformation_rules() -> Dict[str, Any]:
        """Gets transformation rules."""
        db = SessionLocal()
        try:
            db_config = db.query(PipelineConfiguration).filter_by(config_key="transformation_rules").first()
            if db_config:
                return yaml.safe_load(db_config.config_value)
        except Exception as exc:
            logger.warning(f"Could not read transformation_rules override from DB: {str(exc)}")
        finally:
            db.close()
            
        return load_yaml_config("transformation_rules.yaml")

    @staticmethod
    def get_scheduler_config() -> Dict[str, Any]:
        """Gets scheduler cron configurations."""
        db = SessionLocal()
        try:
            db_config = db.query(PipelineConfiguration).filter_by(config_key="scheduler").first()
            if db_config:
                return yaml.safe_load(db_config.config_value)
        except Exception as exc:
            logger.warning(f"Could not read scheduler override from DB: {str(exc)}")
        finally:
            db.close()
            
        return load_yaml_config("scheduler.yaml")

    @staticmethod
    def save_override(key: str, value_yaml: str):
        """Saves a config override in PostgreSQL/SQLite for the platform."""
        db = SessionLocal()
        try:
            db_config = db.query(PipelineConfiguration).filter_by(config_key=key).first()
            if db_config:
                db_config.config_value = value_yaml
            else:
                # Associate with the default pipeline if exists
                pipeline = db.query(Pipeline).filter_by(name="daily_salesforce_etl").first()
                if not pipeline:
                    pipeline = Pipeline(name="daily_salesforce_etl", description="Daily ETL job", schedule_cron="0 2 * * *")
                    db.add(pipeline)
                    db.commit()
                    db.refresh(pipeline)
                
                db_config = PipelineConfiguration(
                    pipeline_id=pipeline.id,
                    config_key=key,
                    config_value=value_yaml
                )
                db.add(db_config)
            db.commit()
        finally:
            db.close()
