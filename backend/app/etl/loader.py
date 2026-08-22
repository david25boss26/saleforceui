import time
import logging
from typing import List, Dict, Any, Tuple
from app.core.config import settings
from app.core.config_manager import ConfigManager
from app.integrations.salesforce.client import get_salesforce_client
from app.utils.hashing import calculate_row_hash

logger = logging.getLogger("salesforce-etl.etl.loader")

class SalesforceLoader:
    def __init__(self, db_session=None):
        self.sf_client = get_salesforce_client()
        self.db = db_session

    def load(self, records: List[Dict[str, Any]], dry_run: bool = False) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], str]:
        """
        Translates records to Salesforce format, generates external ID hashes,
        and pushes to Salesforce via Bulk API 2.0.
        
        Returns:
            Tuple[success_records, failed_records, job_id]
        """
        mappings_cfg = ConfigManager.get_field_mappings()
        target_cfg = mappings_cfg.get("target_mappings", {})
        
        sf_object = target_cfg.get("salesforce_object", "Campaign_Response__c")
        ext_id_field = target_cfg.get("external_id_field", "External_ID__c")
        field_maps = target_cfg.get("mappings", {})
        
        validation_cfg = ConfigManager.get_validation_rules()
        dup_keys = validation_cfg.get("validations", {}).get("duplicate_key", ["email", "product_code", "event"])

        if not records:
            return [], [], "none"

        # Transform canonical records to Salesforce payloads
        sf_payloads = []
        for rec in records:
            # Generate external ID (record hash) using duplicate key fields for idempotency
            rec_hash = calculate_row_hash(rec, dup_keys)
            rec["record_hash"] = rec_hash
            
            sf_rec = {}
            for canonical_key, sf_key in field_maps.items():
                # Read value from record. Support nested fields or fallback
                val = rec.get(canonical_key)
                
                # Format boolean conversions if simple mapping
                if isinstance(val, bool):
                    sf_rec[sf_key] = val
                elif val is not None:
                    sf_rec[sf_key] = str(val)
                else:
                    sf_rec[sf_key] = None
                    
            sf_payloads.append(sf_rec)

        if dry_run:
            logger.info(f"[Dry Run] Prepared {len(sf_payloads)} records for SF object '{sf_object}'")
            successes = []
            for idx, rec in enumerate(records):
                rec["salesforce_id"] = f"dry_run_id_{idx}"
                successes.append(rec)
            return successes, [], "dry_run_job"

        # Start Bulk Upsert Job
        try:
            logger.info(f"Initiating Salesforce Bulk Upsert for {len(sf_payloads)} records on '{sf_object}' using key '{ext_id_field}'")
            job_id = self.sf_client.create_bulk_job(
                object_name=sf_object,
                operation="upsert",
                external_id_field=ext_id_field
            )
            
            # Save job state in database if db is present
            if self.db:
                from app.database.models import SalesforceJob
                sf_job = SalesforceJob(
                    execution_id=records[0].get("_execution_id", "unknown"),
                    job_id=job_id,
                    object_name=sf_object,
                    operation="upsert",
                    state="Open"
                )
                self.db.add(sf_job)
                self.db.commit()
                
            # Upload batch
            self.sf_client.upload_bulk_batch(job_id, sf_payloads)
            self.sf_client.close_bulk_job(job_id)
            
            # Poll status
            state = "UploadComplete"
            poll_count = 0
            while state in ["Open", "UploadComplete", "InProgress"] and poll_count < 30:
                time.sleep(1.5)
                status_info = self.sf_client.get_bulk_job_status(job_id)
                state = status_info.get("state")
                poll_count += 1
                logger.info(f"Bulk Job {job_id} State: {state} (Poll {poll_count})")
                
                if self.db:
                    # Update status in db
                    from app.database.models import SalesforceJob
                    sf_job = self.db.query(SalesforceJob).filter_by(job_id=job_id).first()
                    if sf_job:
                        sf_job.state = state
                        sf_job.records_processed = status_info.get("numberRecordsProcessed", 0)
                        sf_job.records_failed = status_info.get("numberRecordsFailed", 0)
                        self.db.commit()

            # Retrieve results
            results = self.sf_client.get_bulk_job_results(job_id)
            
            success_records = []
            failed_records = []
            
            for idx, res in enumerate(results):
                rec = records[idx]
                if str(res.get("success")).lower() == "true":
                    rec["salesforce_id"] = res.get("sf__Id")
                    success_records.append(rec)
                else:
                    rec["_load_failed"] = True
                    rec["_load_error"] = res.get("sf__Error")
                    failed_records.append(rec)
                    
            logger.info(f"Salesforce upload results: {len(success_records)} successes, {len(failed_records)} failures")
            return success_records, failed_records, job_id

        except Exception as exc:
            logger.exception("Error during Salesforce Bulk loading")
            # If everything failed, treat all as loader failures
            for rec in records:
                rec["_load_failed"] = True
                rec["_load_error"] = str(exc)
            return [], records, "error"
