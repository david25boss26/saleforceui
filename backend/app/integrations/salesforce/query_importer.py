import os
import logging
from typing import Dict, List, Any, Optional, Union
import pandas as pd
from app.core.config import settings

logger = logging.getLogger("salesforce-etl.query_importer")


def flatten_salesforce_record(record: Dict[str, Any], parent_key: str = "", sep: str = ".") -> Dict[str, Any]:
    """
    Recursively flattens a nested Salesforce record dictionary (including parent-relationship objects)
    and removes all Salesforce internal 'attributes' metadata blocks.
    
    Example:
        Input: {
            "attributes": {...},
            "Id": "001xx",
            "OCE__meeting__r": {
                "attributes": {...},
                "recordtype": {
                    "attributes": {...},
                    "name": "Advisory Board"
                },
                "OCE__OrganizingCountry__c": "US"
            }
        }
        Output: {
            "Id": "001xx",
            "OCE__meeting__r.recordtype.name": "Advisory Board",
            "OCE__meeting__r.OCE__OrganizingCountry__c": "US"
        }
    """
    items: Dict[str, Any] = {}

    for key, value in record.items():
        # Ignore Salesforce metadata
        if key == "attributes":
            continue

        new_key = f"{parent_key}{sep}{key}" if parent_key else key

        if isinstance(value, dict):
            # Nested relationship dictionary (e.g. Account.CreatedBy or CustomField__r)
            flattened_sub = flatten_salesforce_record(value, parent_key=new_key, sep=sep)
            items.update(flattened_sub)
        elif isinstance(value, list):
            # Child subqueries (e.g. SELECT (SELECT Id FROM Contacts) FROM Account)
            # Flatten records list if present
            cleaned_list = []
            for item in value:
                if isinstance(item, dict):
                    cleaned_list.append(flatten_salesforce_record(item, parent_key="", sep=sep))
                else:
                    cleaned_list.append(item)
            items[new_key] = cleaned_list
        else:
            items[new_key] = value

    return items


def extract_records_to_list(raw_records: List[Dict[str, Any]], sep: str = ".") -> List[Dict[str, Any]]:
    """
    Cleans and flattens a list of Salesforce records returned by simple-salesforce.
    """
    flattened_list = []
    for rec in raw_records:
        if isinstance(rec, dict):
            flattened_list.append(flatten_salesforce_record(rec, sep=sep))
    return flattened_list


class SalesforceQueryImporter:
    """
    Production-ready Salesforce SOQL Data Importer.
    Supports querying custom objects, deep parent-child relationships,
    automatic pagination, record flattening, and exporting to DataFrame/Excel/CSV/DB.
    """

    def __init__(self, sf_client=None):
        self.sf_client = sf_client

    def get_client(
        self,
        username: Optional[str] = None,
        password: Optional[str] = None,
        security_token: Optional[str] = None,
        domain: Optional[str] = None,
        instance_url: Optional[str] = None,
        session_id: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
    ):
        """
        Retrieves or initializes a Salesforce connection.
        Supports standard login, sandbox, custom MyDomains, and OAuth.
        """
        if self.sf_client is not None:
            return self.sf_client

        from app.integrations.salesforce.client import get_salesforce_client
        
        # If specific credentials passed, initialize a dedicated client
        if username and password:
            from simple_salesforce import Salesforce
            kwargs = {
                "username": username,
                "password": password,
            }
            if security_token is not None:
                kwargs["security_token"] = security_token
            if domain:
                kwargs["domain"] = domain
            if instance_url:
                kwargs["instance_url"] = instance_url
            if client_id and client_secret:
                kwargs["client_id"] = client_id
                kwargs["client_secret"] = client_secret
            
            logger.info(f"Connecting to Salesforce via custom domain/credentials: domain={domain}")
            self.sf_client = Salesforce(**kwargs)
            return self.sf_client
        
        # Fallback to configured global client
        self.sf_client = get_salesforce_client()
        return self.sf_client

    def execute_query(self, soql_query: str, sf_client=None) -> List[Dict[str, Any]]:
        """
        Executes a SOQL query using query_all (handles pagination automatically)
        and returns flattened records.
        """
        client = sf_client or self.get_client()
        logger.info(f"Executing SOQL query: {soql_query.strip()[:120]}...")
        
        # Use query_all to fetch all pages of records
        result = client.query_all(soql_query)
        raw_records = result.get("records", [])
        total_size = result.get("totalSize", len(raw_records))
        logger.info(f"Retrieved {len(raw_records)} records (Total size reported by Salesforce: {total_size})")

        # Flatten records
        flattened_records = extract_records_to_list(raw_records)
        return flattened_records

    def query_to_dataframe(self, soql_query: str, sf_client=None) -> pd.DataFrame:
        """
        Executes SOQL query and returns a pandas DataFrame with clean flattened column names.
        """
        records = self.execute_query(soql_query, sf_client=sf_client)
        if not records:
            logger.warning("SOQL query returned 0 records. Returning empty DataFrame.")
            return pd.DataFrame()

        df = pd.DataFrame(records)
        return df

    def query_to_excel(
        self,
        soql_query: str,
        output_filepath: str,
        sheet_name: str = "Salesforce Data",
        sf_client=None,
        index: bool = False
    ) -> str:
        """
        Executes SOQL query, flattens records, and saves the output to an Excel (.xlsx) file.
        """
        df = self.query_to_dataframe(soql_query, sf_client=sf_client)
        
        output_dir = os.path.dirname(os.path.abspath(output_filepath))
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            
        with pd.ExcelWriter(output_filepath, engine="openpyxl") as writer:
            df.to_excel(writer, index=index, sheet_name=sheet_name[:31]) # Excel sheet name limit is 31 chars
            
        logger.info(f"Successfully exported {len(df)} records to Excel: {output_filepath}")
        return output_filepath

    def query_to_csv(
        self,
        soql_query: str,
        output_filepath: str,
        sf_client=None,
        index: bool = False,
        encoding: str = "utf-8"
    ) -> str:
        """
        Executes SOQL query, flattens records, and saves to CSV file.
        """
        df = self.query_to_dataframe(soql_query, sf_client=sf_client)
        
        output_dir = os.path.dirname(os.path.abspath(output_filepath))
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            
        df.to_csv(output_filepath, index=index, encoding=encoding)
        logger.info(f"Successfully exported {len(df)} records to CSV: {output_filepath}")
        return output_filepath
