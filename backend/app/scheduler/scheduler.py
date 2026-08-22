import os
import logging
import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from app.core.config import settings
from app.core.config_manager import ConfigManager
from app.database.database import SessionLocal
from app.database.models import Pipeline
from app.etl.pipeline import ETLPipeline

logger = logging.getLogger("salesforce-etl.scheduler")

scheduler = BackgroundScheduler()

def scan_and_run_scheduled_jobs():
    """
    Scheduled task that scans data/input/ for excel/csv files,
    matches them to an enabled pipeline, and triggers ETL processing.
    """
    logger.info("Scanning data/input/ for scheduled integration files...")
    
    input_dir = os.path.join(settings.DATA_DIR, "input")
    if not os.path.exists(input_dir):
        return
        
    db = SessionLocal()
    try:
        # Get active pipelines
        active_pipelines = db.query(Pipeline).filter_by(is_enabled=True).all()
        active_names = [p.name for p in active_pipelines]
        
        if not active_names:
            logger.info("No active scheduled pipelines found in database.")
            return

        files = [f for f in os.listdir(input_dir) if f.endswith((".xlsx", ".xls", ".csv"))]
        if not files:
            logger.info("No new files found in data/input/.")
            return
            
        for filename in files:
            filepath = os.path.join(input_dir, filename)
            logger.info(f"Scheduled scan detected file: {filename}")
            
            # Match file to pipeline (e.g. if name contains "india", match to "india_launch")
            matched_pipeline = None
            filename_lower = filename.lower()
            
            for p_name in active_names:
                # Simple naming match, e.g. "india" in "sample_form_india.xlsx" matches "india_launch"
                prefix = p_name.split("_")[0]
                if prefix in filename_lower:
                    matched_pipeline = p_name
                    break
                    
            if not matched_pipeline:
                # Default to first active pipeline as fallback
                matched_pipeline = active_names[0]
                logger.warning(f"Could not cleanly match file '{filename}' to active pipelines {active_names}. Fallback to '{matched_pipeline}'.")
                
            logger.info(f"Triggering scheduled execution for '{matched_pipeline}' using file '{filename}'")
            
            # Execute pipeline
            pipeline_runner = ETLPipeline(db)
            summary = pipeline_runner.run(filepath=filepath, source_name=matched_pipeline, dry_run=False)
            logger.info(f"Scheduled execution summary: {summary}")
            
    except Exception as exc:
        logger.exception("Error in scheduled ETL scanner")
    finally:
        db.close()

def start_scheduler():
    """Initializes and starts the background scheduler."""
    if not settings.SCHEDULER_ENABLED:
        logger.info("Background scheduler is disabled in configuration.")
        return

    # Load scheduler rules
    cfg = ConfigManager.get_scheduler_config().get("scheduler", {})
    if not cfg.get("enabled", True):
        logger.info("Background scheduler is disabled in scheduler.yaml.")
        return

    # Clear previous jobs
    scheduler.remove_all_jobs()
    
    # Register scanner job
    jobs = cfg.get("jobs", [])
    for job_cfg in jobs:
        name = job_cfg.get("name", "salesforce_etl")
        cron_expr = job_cfg.get("cron", "0 2 * * *")
        tz = job_cfg.get("timezone", "UTC")
        
        # Parse cron fields
        fields = cron_expr.split()
        if len(fields) == 5:
            minute, hour, dom, month, dow = fields
            trigger = CronTrigger(
                minute=minute,
                hour=hour,
                day=dom,
                month=month,
                day_of_week=dow,
                timezone=tz
            )
            
            scheduler.add_job(
                scan_and_run_scheduled_jobs,
                trigger=trigger,
                id=name,
                replace_existing=True
            )
            logger.info(f"Scheduled cron job '{name}' with trigger '{cron_expr}' ({tz})")
            
    if not scheduler.running:
        scheduler.start()
        logger.info("APScheduler started successfully in background.")

def shutdown_scheduler():
    """Stops the background scheduler."""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("APScheduler shutdown successfully.")
