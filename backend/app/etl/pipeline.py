import os
import datetime
import shutil
import logging
import uuid
import pandas as pd
from typing import Dict, Any, List, Optional
from app.core.config import settings
from app.core.config_manager import ConfigManager
from app.database.database import SessionLocal
from app.database.models import ETLExecution, ETLRecordLog, SourceFile, MappingError, ValidationError, SalesforceJob
from app.utils.hashing import calculate_file_hash
from app.utils.excel import read_excel_file, write_excel_file
from app.utils.csv import read_csv_file, write_csv_file
from app.forms.normalizer import FormNormalizer
from app.etl.extractor import SalesforceExtractor
from app.etl.enricher import DataEnricher
from app.etl.transformer import DataTransformer
from app.etl.validator import DataValidator
from app.etl.loader import SalesforceLoader

logger = logging.getLogger("salesforce-etl.etl.pipeline")

class ETLPipeline:
    def __init__(self, db_session=None):
        self.db = db_session or SessionLocal()
        self.own_session = db_session is None

    def close(self):
        if self.own_session:
            self.db.close()

    def run(self, filepath: str, source_name: Optional[str] = None, dry_run: bool = False) -> Dict[str, Any]:
        """
        Executes the full Salesforce ETL pipeline for an input form response file.
        """
        start_time = datetime.datetime.utcnow()
        execution_id = f"exec_{uuid.uuid4().hex[:8]}"
        
        # Ensure directories exist
        for folder in ["input", "salesforce_exports", "staging", "output", "errors", "archive"]:
            os.makedirs(os.path.join(settings.DATA_DIR, folder), exist_ok=True)

        filename = os.path.basename(filepath)
        file_size = os.path.getsize(filepath)
        
        logger.info(f"Starting ETL Execution {execution_id} for file '{filename}' (Dry Run: {dry_run})")
        
        # 1. Idempotency Guard: Calculate file hash and check if it already exists
        file_hash = calculate_file_hash(filepath)
        existing_file = self.db.query(SourceFile).filter_by(md5_hash=file_hash).first()
        if existing_file:
            logger.warning(f"File '{filename}' with hash '{file_hash}' has already been processed on {existing_file.uploaded_at}")
            # We will still allow the run but log a warning in execution logs, or abort depending on config.
            # Let's create the execution record now as warning/failed or complete it with skipped.
            # To follow: "If the same source file is processed twice, detect it and warn the user."
            # We will allow it but mark a warning.

        # Create overall ETLExecution log entry
        execution = ETLExecution(
            execution_id=execution_id,
            pipeline_name=source_name or "dynamic_ingestion",
            start_time=start_time,
            status="RECEIVED",
            dry_run=dry_run
        )
        self.db.add(execution)
        self.db.commit()

        # Track file metadata in db
        if not existing_file:
            sf_file = SourceFile(
                file_name=filename,
                file_path=filepath,
                md5_hash=file_hash,
                file_size=file_size
            )
            self.db.add(sf_file)
            self.db.commit()

        # Phase tracks
        raw_records = []
        normalized_data = {}
        valid_records = []
        invalid_records = []
        success_loaded = []
        failed_loaded = []
        
        try:
            # 2. Extract Salesforce reference data
            logger.info("Stage 1/6: Extracting Salesforce reference master data...")
            extractor = SalesforceExtractor()
            extractor.extract_reference_data()
            execution.status = "EXTRACTED"
            self.db.commit()

            # 3. Read input form data based on file extension
            logger.info("Stage 2/6: Ingesting external form responses...")
            if filename.endswith((".xlsx", ".xls")):
                raw_records = read_excel_file(filepath)
            elif filename.endswith(".csv"):
                raw_records = read_csv_file(filepath)
            else:
                raise ValueError("Unsupported file format. Please upload Excel (.xlsx) or CSV (.csv).")
                
            execution.records_received = len(raw_records)
            self.db.commit()
            
            if not raw_records:
                raise ValueError("Source file contains no data rows.")

            # 4. Dynamic schema normalization
            logger.info("Stage 3/6: Running dynamic schema normalization...")
            normalized_data = FormNormalizer.normalize(raw_records, source_name)
            detected_source = normalized_data["source_name"]
            execution.pipeline_name = detected_source
            
            # Record missing and unmapped fields as mapping errors
            report = normalized_data["ingestion_report"]
            for mf in report["missing_fields"]:
                map_err = MappingError(
                    execution_id=execution_id,
                    source_row=0,
                    field=mf,
                    error_message=f"Missing required header mapping: {mf}"
                )
                self.db.add(map_err)
            self.db.commit()
            
            normalized_records = normalized_data["records"]
            
            # Set execution context id on records
            for r in normalized_records:
                r["_execution_id"] = execution_id
                
            # Log raw ingestion status
            for rec in normalized_records:
                r_log = ETLRecordLog(
                    execution_id=execution_id,
                    source_row=rec["_row_number"],
                    record_identifier=rec.get("email"),
                    status="SUCCESS",
                    stage="NORMALIZE"
                )
                self.db.add(r_log)
            self.db.commit()

            # 5. Enrichment & Salesforce Lookup
            logger.info("Stage 4/6: Performing Salesforce reference lookups...")
            enricher = DataEnricher()
            enriched_records = enricher.enrich(normalized_records)
            
            # Log lookup failures
            for rec in enriched_records:
                if rec.get("_lookup_failed", False):
                    for err in rec["_lookup_errors"]:
                        map_err = MappingError(
                            execution_id=execution_id,
                            source_row=rec["_row_number"],
                            field=err["lookup_name"],
                            input_value=str(err["input_value"]),
                            error_message=err["error_reason"]
                        )
                        self.db.add(map_err)
                        
                        r_log = ETLRecordLog(
                            execution_id=execution_id,
                            source_row=rec["_row_number"],
                            record_identifier=rec.get("email"),
                            status="FAILED",
                            stage="ENRICH",
                            error_code="LOOKUP_ERROR",
                            error_message=err["error_reason"]
                        )
                        self.db.add(r_log)
            self.db.commit()

            # 6. Transformation
            logger.info("Stage 5/6: Applying data transformations...")
            transformer = DataTransformer()
            transformed_records = transformer.transform(enriched_records)
            
            # 7. Validation
            logger.info("Stage 6/6: Validating records against rules and duplicates...")
            validator = DataValidator()
            valid_records, invalid_records = validator.validate(transformed_records, detected_source)
            
            # Write validation errors to db
            for rec in invalid_records:
                # If it failed validation phase but didn't fail enrichment (or we separate them)
                if rec.get("_validation_failed", False):
                    for err in rec["_validation_errors"]:
                        val_err = ValidationError(
                            execution_id=execution_id,
                            source_row=rec["_row_number"],
                            field=err["field"],
                            input_value=str(err["input_value"]),
                            rule=err["rule"],
                            error_message=err["error_message"]
                        )
                        self.db.add(val_err)
                        
                        r_log = ETLRecordLog(
                            execution_id=execution_id,
                            source_row=rec["_row_number"],
                            record_identifier=rec.get("email"),
                            status="FAILED",
                            stage="VALIDATE",
                            error_code="VALIDATION_ERROR",
                            error_message=err["error_message"]
                        )
                        self.db.add(r_log)
            self.db.commit()

            # 8. Salesforce Upsert Loader (only load valid records)
            if valid_records:
                logger.info(f"Loading {len(valid_records)} valid records to Salesforce...")
                loader = SalesforceLoader(self.db)
                success_loaded, failed_loaded, job_id = loader.load(valid_records, dry_run=dry_run)
                
                # Update records with upload statuses
                for rec in success_loaded:
                    r_log = ETLRecordLog(
                        execution_id=execution_id,
                        source_row=rec["_row_number"],
                        record_identifier=rec.get("email"),
                        status="SUCCESS",
                        stage="LOAD",
                        salesforce_id=rec.get("salesforce_id")
                    )
                    self.db.add(r_log)
                    
                for rec in failed_loaded:
                    r_log = ETLRecordLog(
                        execution_id=execution_id,
                        source_row=rec["_row_number"],
                        record_identifier=rec.get("email"),
                        status="FAILED",
                        stage="LOAD",
                        error_code="SALESFORCE_ERROR",
                        error_message=rec.get("_load_error", "Unknown Salesforce bulk error")
                    )
                    self.db.add(r_log)
                self.db.commit()
            else:
                logger.warning("No valid records found in batch. Skipping Salesforce push.")
                job_id = "none"

            # 9. Update Execution Metrics
            execution.records_processed = len(raw_records)
            execution.records_successful = len(success_loaded)
            # Fails include validation fails, lookup fails, and Salesforce load fails
            execution.records_failed = len(invalid_records) + len(failed_loaded)
            execution.records_skipped = sum(1 for r in invalid_records if r.get("_is_duplicate", False))
            execution.status = "SUCCESS" if execution.records_failed == 0 else "PARTIAL_SUCCESS"
            
            if existing_file:
                execution.error_summary = f"WARNING: Source file '{filename}' was already processed previously. "
            else:
                execution.error_summary = ""
                
            if execution.records_failed > 0:
                execution.error_summary += f"Encountered {execution.records_failed} errors during execution."
                
            self.db.commit()

            # 10. Generate Error & Execution Reports
            logger.info("Generating spreadsheet execution reports...")
            self._generate_reports(execution_id, raw_records, transformed_records, success_loaded, invalid_records, failed_loaded)

            # 11. Archive successfully processed file (only if not a dry-run and pipeline succeeded or partial succeeded)
            if not dry_run:
                self._archive_file(filepath)

        except Exception as exc:
            logger.exception("ETL execution crashed")
            execution.status = "FAILED"
            execution.error_summary = f"Execution crashed: {str(exc)}"
            self.db.commit()
            
        finally:
            end_time = datetime.datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            execution.end_time = end_time
            execution.execution_duration = duration
            self.db.commit()
            
        summary = {
            "execution_id": execution_id,
            "pipeline_name": execution.pipeline_name,
            "status": execution.status,
            "received": execution.records_received,
            "successful": execution.records_successful,
            "failed": execution.records_failed,
            "skipped": execution.records_skipped,
            "duration_sec": duration,
            "error_summary": execution.error_summary
        }
        
        logger.info(f"ETL pipeline finished. Summary: {summary}")
        
        # Trigger Email notification ifSMTP is configured
        self._send_email_notification(summary)
        
        return summary

    def _generate_reports(self, exec_id: str, raw_records: List[Dict], all_records: List[Dict], successes: List[Dict], val_fails: List[Dict], sfdc_fails: List[Dict]):
        """Generates Excel reports for the execution."""
        out_dir = os.path.join(settings.DATA_DIR, "output")
        err_dir = os.path.join(settings.DATA_DIR, "errors")
        
        # Clean internal keys for reports
        def clean_keys(recs):
            cleaned = []
            for r in recs:
                c = {k: v for k, v in r.items() if not k.startswith("_") and k not in ["record_hash"]}
                cleaned.append(c)
            return cleaned

        # 1. Successful Records
        if successes:
            write_excel_file(os.path.join(out_dir, f"successful_records_{exec_id}.xlsx"), clean_keys(successes))
            
        # 2. Failed Records (both validation + salesforce failures)
        failed_records = []
        for r in val_fails:
            failed_records.append(r)
        for r in sfdc_fails:
            failed_records.append(r)
            
        if failed_records:
            write_excel_file(os.path.join(err_dir, f"failed_records_{exec_id}.xlsx"), clean_keys(failed_records))
            
        # 3. Validation Errors Report
        val_errors_list = []
        for r in val_fails:
            row_num = r.get("_row_number", "?")
            email = r.get("email", "")
            
            # Lookup errors
            if r.get("_lookup_failed"):
                for err in r.get("_lookup_errors", []):
                    val_errors_list.append({
                        "Record ID": email,
                        "Source Row": row_num,
                        "Stage": "ENRICHMENT",
                        "Field": err["lookup_name"],
                        "Input Value": err["input_value"],
                        "Error Code": "LOOKUP_ERROR",
                        "Error Message": err["error_reason"],
                        "Suggested Action": "Verify that this code exists in the Salesforce reference exports"
                    })
            # Core validation errors
            if r.get("_validation_failed"):
                for err in r.get("_validation_errors", []):
                    val_errors_list.append({
                        "Record ID": email,
                        "Source Row": row_num,
                        "Stage": "VALIDATION",
                        "Field": err["field"],
                        "Input Value": err["input_value"],
                        "Error Code": err["rule"],
                        "Error Message": err["error_message"],
                        "Suggested Action": "Correct data format or values according to business schemas"
                    })
        if val_errors_list:
            write_excel_file(os.path.join(err_dir, f"validation_errors_{exec_id}.xlsx"), val_errors_list)

        # 4. Salesforce Errors Report
        sfdc_errors_list = []
        for r in sfdc_fails:
            sfdc_errors_list.append({
                "Record ID": r.get("email", ""),
                "Source Row": r.get("_row_number", "?"),
                "Stage": "LOAD",
                "Field": "Salesforce API",
                "Input Value": "",
                "Error Code": "SALESFORCE_ERROR",
                "Error Message": r.get("_load_error", ""),
                "Suggested Action": "Check field lengths, picklist limits, and validation rules in Salesforce"
            })
        if sfdc_errors_list:
            write_excel_file(os.path.join(err_dir, f"salesforce_errors_{exec_id}.xlsx"), sfdc_errors_list)

        # 5. Execution Summary
        summary_data = [{
            "Execution ID": exec_id,
            "Timestamp": datetime.datetime.utcnow().isoformat(),
            "Total Ingested": len(raw_records),
            "Successful": len(successes),
            "Failed": len(failed_records),
            "Validation Failed": len(val_fails),
            "Salesforce Failed": len(sfdc_fails),
        }]
        write_excel_file(os.path.join(out_dir, f"execution_summary_{exec_id}.xlsx"), summary_data)

    def _archive_file(self, filepath: str):
        """Moves processed input files to partitioned archive directories."""
        try:
            today = datetime.datetime.utcnow()
            archive_path = os.path.join(
                settings.DATA_DIR,
                "archive",
                today.strftime("%Y"),
                today.strftime("%m"),
                today.strftime("%d")
            )
            os.makedirs(archive_path, exist_ok=True)
            
            dest = os.path.join(archive_path, os.path.basename(filepath))
            
            # If destination exists, append timestamp
            if os.path.exists(dest):
                base, ext = os.path.splitext(os.path.basename(filepath))
                dest = os.path.join(archive_path, f"{base}_{int(time.time())}{ext}")
                
            shutil.move(filepath, dest)
            logger.info(f"Archived input file to {dest}")
        except Exception as exc:
            logger.warning(f"Failed to archive file {filepath}: {str(exc)}")

    def _send_email_notification(self, summary: Dict[str, Any]):
        """Simulates sending email notifications for successes and failures."""
        if not settings.SMTP_HOST or not settings.SMTP_USERNAME:
            logger.info("SMTP configuration not supplied. Skipping email notification.")
            return
            
        logger.info(f"Simulating email notification sent to {settings.SMTP_FROM}:")
        email_body = f"""
        Salesforce ETL Execution Summary
        --------------------------------
        Execution ID: {summary['execution_id']}
        Pipeline/Source: {summary['pipeline_name']}
        Status: {summary['status']}
        
        Records Ingested: {summary['received']}
        Successful Upserts: {summary['successful']}
        Failed Records: {summary['failed']}
        Skipped/Duplicates: {summary['skipped']}
        Duration: {summary['duration_sec']:.2f} seconds
        
        Error Summary: {summary['error_summary']}
        
        All detailed failed spreadsheets are saved in data/errors/
        """
        logger.info(email_body)
        # In production this would use smtplib to compile and send a multipart email with attachments.
