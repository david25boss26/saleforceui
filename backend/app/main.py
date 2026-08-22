import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.logging import setup_logging
from app.database.database import init_db
from app.scheduler.scheduler import start_scheduler, shutdown_scheduler

# Import API routers
from app.api.routes.health import router as health_router
from app.api.routes.files import router as files_router
from app.api.routes.configurations import router as config_router
from app.api.routes.executions import router as exec_router
from app.api.routes.jobs import router as jobs_router

setup_logging()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup actions
    init_db()
    start_scheduler()
    yield
    # Shutdown actions
    shutdown_scheduler()

app = FastAPI(
    title="Automated Salesforce ETL & Data Integration Service",
    description="Backend API for scheduling, running, and auditing Salesforce ETL integrations.",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for local React development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict to dashboard host
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(health_router, prefix="/api")
app.include_router(files_router, prefix="/api")
app.include_router(config_router, prefix="/api")
app.include_router(exec_router, prefix="/api")
app.include_router(jobs_router, prefix="/api")

@app.get("/")
def read_root():
    return {
        "app": "Salesforce ETL Service",
        "status": "online",
        "docs": "/docs"
    }
