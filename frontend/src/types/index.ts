export interface Pipeline {
  id: number;
  name: string;
  description: string;
  schedule_cron: string;
  schedule_timezone: string;
  is_enabled: boolean;
  status: string; // IDLE, RUNNING, PAUSED
  created_at: string;
  updated_at: string;
}

export interface ETLExecution {
  id: number;
  execution_id: string;
  pipeline_name: string;
  start_time: string;
  end_time: string | null;
  status: string; // RECEIVED, NORMALIZED, VALIDATED, ENRICHED, READY, UPLOADED, FAILED, SKIPPED, PARTIAL_SUCCESS, SUCCESS
  records_received: number;
  records_processed: number;
  records_successful: number;
  records_failed: number;
  records_skipped: number;
  execution_duration: number;
  error_summary: string | null;
  dry_run: boolean;
  created_at: string;
}

export interface ETLRecordLog {
  id: number;
  execution_id: string;
  source_row: number;
  record_identifier: string | null;
  status: string; // SUCCESS, FAILED
  stage: string; // NORMALIZE, ENRICH, TRANSFORM, VALIDATE, LOAD
  error_code: string | null;
  error_message: string | null;
  salesforce_id: string | null;
  created_at: string;
}

export interface MappingError {
  id: number;
  execution_id: string;
  source_row: number;
  field: string;
  input_value: string | null;
  error_message: string;
  created_at: string;
}

export interface ValidationError {
  id: number;
  execution_id: string;
  source_row: number;
  field: string;
  input_value: string | null;
  rule: string;
  error_message: string;
  created_at: string;
}

export interface ConfigData {
  salesforce_objects: string;
  field_mappings: string;
  validation_rules: string;
  transformation_rules: string;
  scheduler: string;
}
