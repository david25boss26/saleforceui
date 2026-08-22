from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database.database import get_db
from app.integrations.salesforce.client import get_salesforce_client
from app.core.config import settings

router = APIRouter(prefix="/health", tags=["Health"])

@router.get("")
def health_check(db: Session = Depends(get_db)):
    # Check Database
    db_status = "disconnected"
    try:
        db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception:
        pass

    # Check Salesforce
    sf_status = "disconnected"
    try:
        client = get_salesforce_client()
        if settings.MOCK_SALESFORCE:
            sf_status = "mocked"
        else:
            # Simple ping
            client.query_all("SELECT Id FROM Account LIMIT 1")
            sf_status = "connected"
    except Exception:
        pass

    # Check Scheduler (we assume active if enabled)
    scheduler_status = "running" if settings.SCHEDULER_ENABLED else "stopped"

    is_healthy = (db_status == "connected" and sf_status in ["connected", "mocked"])

    return {
        "status": "healthy" if is_healthy else "unhealthy",
        "database": db_status,
        "salesforce": sf_status,
        "scheduler": scheduler_status
    }
