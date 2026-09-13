#!/usr/bin/env python3
"""
Salesforce Data Extraction & SOQL Importer Script

Features:
- Connects to Salesforce (Production, Sandbox, or Custom MyDomain like 'novartis-events-oce--qa.sandbox.my')
- Executes SOQL queries with automatic pagination via query_all()
- Recursively flattens multi-level relationship fields (e.g. OCE__meeting__r.recordtype.name)
- Strips Salesforce metadata attributes at all nesting depths
- Exports clean tabular data to Excel (.xlsx) and CSV
- Can be configured via Environment Variables or CLI Arguments
"""

import os
import sys
import argparse
import logging
from typing import Dict, List, Any
import pandas as pd
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv(os.path.join(os.path.dirname(__file__), "backend", ".env"))
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("SalesforceImporter")


def flatten_record(record: Dict[str, Any], parent_key: str = "", sep: str = ".") -> Dict[str, Any]:
    """
    Recursively flattens nested Salesforce record dictionaries and removes 'attributes'.
    Handles deep relationship queries like OCE__meeting__r.recordtype.name.
    """
    items: Dict[str, Any] = {}
    for key, value in record.items():
        if key == "attributes":
            continue

        new_key = f"{parent_key}{sep}{key}" if parent_key else key

        if isinstance(value, dict):
            flattened_sub = flatten_record(value, parent_key=new_key, sep=sep)
            items.update(flattened_sub)
        elif isinstance(value, list):
            cleaned_list = []
            for item in value:
                if isinstance(item, dict):
                    cleaned_list.append(flatten_record(item, parent_key="", sep=sep))
                else:
                    cleaned_list.append(item)
            items[new_key] = cleaned_list
        else:
            items[new_key] = value

    return items


def query_salesforce(
    query: str,
    username: str = None,
    password: str = None,
    security_token: str = None,
    session_id: str = None,
    domain: str = None,
    instance_url: str = None,
    client_id: str = None,
    client_secret: str = None
) -> pd.DataFrame:
    """
    Connects to Salesforce, runs the SOQL query, and returns a Pandas DataFrame.
    Supports session_id direct auth, OAuth2, and username/password.
    """
    from simple_salesforce import Salesforce

    # Gather credentials from args or env
    sess_id = session_id or os.getenv("SALESFORCE_SESSION_ID")
    user = username or os.getenv("SALESFORCE_USERNAME")
    pwd = password or os.getenv("SALESFORCE_PASSWORD")
    token = security_token or os.getenv("SALESFORCE_SECURITY_TOKEN", "")
    dom = domain or os.getenv("SALESFORCE_DOMAIN", "novartis-events-oce--qa.sandbox.my")
    cid = client_id or os.getenv("SALESFORCE_CLIENT_ID")
    csec = client_secret or os.getenv("SALESFORCE_CLIENT_SECRET")
    inst_url = instance_url or os.getenv("SALESFORCE_INSTANCE_URL")

    # If session_id is provided, connect directly without username/password
    if sess_id:
        logger.info("Connecting to Salesforce using direct Session ID / Access Token...")
        inst = inst_url
        if not inst and dom:
            if not dom.startswith("http"):
                inst = f"https://{dom}.salesforce.com" if not dom.endswith(".com") else f"https://{dom}"
            else:
                inst = dom
        sf = Salesforce(session_id=sess_id, instance_url=inst)
    else:
        if not user or not pwd:
            raise ValueError(
                "Salesforce credentials missing! Please provide --session-id OR (--username and --password), "
                "or set them in your environment / .env file."
            )

        logger.info(f"Connecting to Salesforce (User: {user}, Domain: {dom})...")

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

        sf = Salesforce(**kwargs)

    logger.info("Connected successfully to Salesforce.")

    logger.info(f"Executing SOQL query:\n{query.strip()}")
    result = sf.query_all(query)

    records = result.get("records", [])
    total_size = result.get("totalSize", len(records))
    logger.info(f"Query returned {len(records)} records (Salesforce total size: {total_size}).")

    if not records:
        logger.warning("No records returned from Salesforce query.")
        return pd.DataFrame()

    # Flatten nested dictionaries
    flattened_records = [flatten_record(r) for r in records if isinstance(r, dict)]
    df = pd.DataFrame(flattened_records)
    return df


def main():
    default_query = """
SELECT id, 
       OCE__meeting__r.recordtype.name, 
       OCE__MeetingMember__r.OCE__Type__c, 
       OCE__Meeting__r.OCE__OrganizingCountry__c, 
       OCE__MeetingMember__r.OCE__Meeting__r.OCE__Status__c, 
       OCE__PaymentStatus__c, 
       OCE__InvoiceStatus__c
FROM OCE__Invoice__c
""".strip()

    parser = argparse.ArgumentParser(description="Extract data from Salesforce via SOQL queries to Excel/CSV.")
    parser.add_argument("--query", "-q", type=str, default=default_query, help="SOQL query string")
    parser.add_argument("--output", "-o", type=str, default="salesforce_extract.xlsx", help="Output file path (.xlsx or .csv)")
    parser.add_argument("--sheet", "-s", type=str, default="Salesforce Data", help="Excel worksheet name")
    parser.add_argument("--session-id", "--sid", type=str, default=None, help="Active Salesforce Session ID / Access Token (Bypasses password & token)")
    parser.add_argument("--username", "-u", type=str, default=None, help="Salesforce Username")
    parser.add_argument("--password", "-p", type=str, default=None, help="Salesforce Password")
    parser.add_argument("--token", "-t", type=str, default=None, help="Salesforce Security Token")
    parser.add_argument("--domain", "-d", type=str, default="novartis-events-oce--qa.sandbox.my", help="Salesforce Domain (e.g. login, test, or custom sandbox domain)")

    args = parser.parse_args()

    try:
        df = query_salesforce(
            query=args.query,
            session_id=args.session_id,
            username=args.username,
            password=args.password,
            security_token=args.token,
            domain=args.domain
        )

        out_path = os.path.abspath(args.output)
        out_dir = os.path.dirname(out_path)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)

        if args.output.lower().endswith(".csv"):
            df.to_csv(out_path, index=False, encoding="utf-8")
        else:
            with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
                df.to_excel(writer, index=False, sheet_name=args.sheet[:31])

        logger.info(f"Successfully extracted {len(df)} rows and {len(df.columns)} columns to {out_path}")
        print(f"\n[SUCCESS] Salesforce data extracted successfully and saved to: {out_path}")
        print(f"Columns extracted: {list(df.columns)}")

    except Exception as exc:
        logger.error(f"Failed to extract Salesforce data: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
