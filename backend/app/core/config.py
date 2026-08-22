import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    APP_ENV: str = "development"
    DATABASE_URL: str = "sqlite:///./salesforce_etl.db"
    
    # Salesforce
    MOCK_SALESFORCE: bool = True
    SALESFORCE_ENVIRONMENT: str = "sandbox"
    SALESFORCE_USERNAME: Optional[str] = None
    SALESFORCE_PASSWORD: Optional[str] = None
    SALESFORCE_SECURITY_TOKEN: Optional[str] = None
    SALESFORCE_CLIENT_ID: Optional[str] = None
    SALESFORCE_CLIENT_SECRET: Optional[str] = None
    SALESFORCE_LOGIN_URL: str = "https://test.salesforce.com"
    
    # Ingestion
    DRY_RUN: bool = False
    SCHEDULER_ENABLED: bool = True
    
    # SMTP
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USERNAME: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM: str = "no-reply@company.com"
    
    # Paths
    BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    CONFIG_DIR: str = os.path.join(BASE_DIR, "config")
    DATA_DIR: str = os.path.join(BASE_DIR, "data")
    SAMPLE_DATA_DIR: str = os.path.join(BASE_DIR, "sample_data")

    model_config = SettingsConfigDict(
        env_file=os.path.join(BASE_DIR, "backend", ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
