import time
import logging
from typing import Dict, List, Any
from app.core.config import settings

logger = logging.getLogger("salesforce-etl.salesforce-client")

# Define mock data that mimics Salesforce tables
MOCK_ACCOUNTS = [
    {"Id": "acc_001", "Name": "Acme Corp", "AccountNumber": "ACT100"},
    {"Id": "acc_002", "Name": "Globex Corporation", "AccountNumber": "ACT200"},
    {"Id": "acc_003", "Name": "Initech LLC", "AccountNumber": "ACT300"},
]

MOCK_PRODUCTS = [
    {"Id": "prod_001", "Name": "Solar Panel v1", "ProductCode": "PRD_SLR_01", "Family": "Energy"},
    {"Id": "prod_002", "Name": "Wind Turbine v2", "ProductCode": "PRD_WND_02", "Family": "Energy"},
    {"Id": "prod_003", "Name": "Battery Storage v1", "ProductCode": "PRD_BAT_03", "Family": "Energy"},
]

MOCK_BUDGETS = [
    {"Id": "bud_001", "Name": "Launch Budget India", "Budget_Code__c": "BDG_IND_2026", "Allocated_Amount__c": 50000.0},
    {"Id": "bud_002", "Name": "Launch Budget UAE", "Budget_Code__c": "BDG_UAE_2026", "Allocated_Amount__c": 75000.0},
]

MOCK_CHECKLISTS = [
    {"Id": "chk_001", "Name": "Standard Launch Checklist", "Checklist_Code__c": "CHK_STD_01", "Status__c": "Active"},
    {"Id": "chk_002", "Name": "Alternative Launch Checklist", "Checklist_Code__c": "CHK_ALT_02", "Status__c": "Draft"},
]

MOCK_INVOICES = [
    {
        "attributes": {"type": "OCE__Invoice__c", "url": "/services/data/v59.0/sobjects/OCE__Invoice__c/a001"},
        "Id": "inv_001",
        "OCE__meeting__r": {
            "attributes": {"type": "OCE__Meeting__c"},
            "recordtype": {
                "attributes": {"type": "RecordType"},
                "name": "Medical Advisory Board"
            },
            "OCE__OrganizingCountry__c": "Switzerland"
        },
        "OCE__MeetingMember__r": {
            "attributes": {"type": "OCE__MeetingMember__c"},
            "OCE__Type__c": "Speaker",
            "OCE__Meeting__r": {
                "attributes": {"type": "OCE__Meeting__c"},
                "OCE__Status__c": "Completed"
            }
        },
        "OCE__PaymentStatus__c": "Processed",
        "OCE__InvoiceStatus__c": "Approved"
    },
    {
        "attributes": {"type": "OCE__Invoice__c", "url": "/services/data/v59.0/sobjects/OCE__Invoice__c/a002"},
        "Id": "inv_002",
        "OCE__meeting__r": {
            "attributes": {"type": "OCE__Meeting__c"},
            "recordtype": {
                "attributes": {"type": "RecordType"},
                "name": "Investigator Meeting"
            },
            "OCE__OrganizingCountry__c": "Germany"
        },
        "OCE__MeetingMember__r": {
            "attributes": {"type": "OCE__MeetingMember__c"},
            "OCE__Type__c": "Chairperson",
            "OCE__Meeting__r": {
                "attributes": {"type": "OCE__Meeting__c"},
                "OCE__Status__c": "Closed"
            }
        },
        "OCE__PaymentStatus__c": "Pending",
        "OCE__InvoiceStatus__c": "Submitted"
    }
]

class MockBulkJob:
    def __init__(self, job_id: str, object_name: str, operation: str):
        self.job_id = job_id
        self.object_name = object_name
        self.operation = operation
        self.state = "Open"
        self.records: List[Dict[str, Any]] = []

    def upload_results(self) -> List[Dict[str, Any]]:
        results = []
        for idx, rec in enumerate(self.records):
            # Simulate a Salesforce load failure if email is "fail_sfdc@example.com"
            if rec.get("Email__c") == "fail_sfdc@example.com":
                results.append({
                    "sf__Id": None,
                    "sf__Created": "false",
                    "sf__Error": "REQUIRED_FIELD_MISSING: Campaign__c is required",
                    "success": "false",
                    "row": idx
                })
            else:
                results.append({
                    "sf__Id": f"sf_resp_{idx:04d}",
                    "sf__Created": "true",
                    "sf__Error": "",
                    "success": "true",
                    "row": idx
                })
        return results

class MockSalesforceClient:
    def __init__(self):
        logger.info("Initializing Mock Salesforce Client")
        self.jobs: Dict[str, MockBulkJob] = {}
        self.job_counter = 0

    def query_all(self, soql: str) -> Dict[str, Any]:
        logger.info(f"Mock Query: {soql}")
        query_lower = soql.lower()
        
        records = []
        if "from account" in query_lower:
            records = MOCK_ACCOUNTS
        elif "from product2" in query_lower:
            records = MOCK_PRODUCTS
        elif "from budget__c" in query_lower:
            records = MOCK_BUDGETS
        elif "from checklist__c" in query_lower:
            records = MOCK_CHECKLISTS
        elif "from oce__invoice__c" in query_lower or "oce__invoice" in query_lower:
            records = MOCK_INVOICES
        else:
            logger.warning(f"Unknown mock table query: {soql}")
            # Fallback mock records
            records = [
                {"Id": "mock_rec_001", "Name": "Mock Dynamic Record 1"},
                {"Id": "mock_rec_002", "Name": "Mock Dynamic Record 2"},
            ]
            
        return {"totalSize": len(records), "done": True, "records": records}

    def create_bulk_job(self, object_name: str, operation: str, external_id_field: str = None) -> str:
        self.job_counter += 1
        job_id = f"mock_job_{self.job_counter:04d}"
        self.jobs[job_id] = MockBulkJob(job_id, object_name, operation)
        logger.info(f"Mock Created Bulk Job {job_id} for {object_name} ({operation})")
        return job_id

    def upload_bulk_batch(self, job_id: str, records: List[Dict[str, Any]]):
        if job_id not in self.jobs:
            raise ValueError(f"Job {job_id} not found")
        self.jobs[job_id].records.extend(records)
        logger.info(f"Mock Uploaded {len(records)} records to Bulk Job {job_id}")

    def close_bulk_job(self, job_id: str):
        if job_id not in self.jobs:
            raise ValueError(f"Job {job_id} not found")
        self.jobs[job_id].state = "UploadComplete"
        logger.info(f"Mock Closed Bulk Job {job_id}")

    def get_bulk_job_status(self, job_id: str) -> Dict[str, Any]:
        if job_id not in self.jobs:
            raise ValueError(f"Job {job_id} not found")
        job = self.jobs[job_id]
        # Simulate quick processing
        job.state = "JobComplete"
        return {
            "id": job_id,
            "object": job.object_name,
            "operation": job.operation,
            "state": job.state,
            "numberRecordsProcessed": len(job.records),
            "numberRecordsFailed": sum(1 for r in job.upload_results() if r["success"] == "false")
        }

    def get_bulk_job_results(self, job_id: str) -> List[Dict[str, Any]]:
        if job_id not in self.jobs:
            raise ValueError(f"Job {job_id} not found")
        return self.jobs[job_id].upload_results()


def get_salesforce_client(
    username: str = None,
    password: str = None,
    security_token: str = None,
    domain: str = None,
    instance_url: str = None,
    client_id: str = None,
    client_secret: str = None,
    force_mock: bool = False
):
    """
    Returns simple-salesforce Salesforce instance or MockSalesforceClient based on configuration.
    Accepts optional credential/domain overrides.
    """
    if force_mock or settings.MOCK_SALESFORCE:
        return MockSalesforceClient()
        
    try:
        from simple_salesforce import Salesforce
        
        user = username or settings.SALESFORCE_USERNAME
        pwd = password or settings.SALESFORCE_PASSWORD
        token = security_token or settings.SALESFORCE_SECURITY_TOKEN
        cid = client_id or settings.SALESFORCE_CLIENT_ID
        csec = client_secret or settings.SALESFORCE_CLIENT_SECRET
        inst_url = instance_url or settings.SALESFORCE_INSTANCE_URL
        
        # Determine domain
        dom = domain or settings.SALESFORCE_DOMAIN
        if not dom:
            dom = "test" if settings.SALESFORCE_ENVIRONMENT == "sandbox" else "login"

        if not user or not pwd:
            logger.warning("Salesforce credentials missing, falling back to MockSalesforceClient")
            return MockSalesforceClient()
            
        kwargs: Dict[str, Any] = {
            "username": user,
            "password": pwd,
        }
        
        if dom:
            kwargs["domain"] = dom
        if inst_url:
            kwargs["instance_url"] = inst_url
        if token:
            kwargs["security_token"] = token
        if cid and csec:
            kwargs["client_id"] = cid
            kwargs["client_secret"] = csec
            
        logger.info(f"Authenticating with Salesforce (Domain: {dom})")
        return Salesforce(**kwargs)
        
    except Exception as exc:
        logger.exception("Failed to initialize real simple-salesforce client. Falling back to Mock.")
        return MockSalesforceClient()
