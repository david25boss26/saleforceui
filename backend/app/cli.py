import argparse
import sys
import logging
from app.core.logging import setup_logging
from app.database.database import init_db, SessionLocal
from app.etl.extractor import SalesforceExtractor
from app.integrations.salesforce.query_importer import SalesforceQueryImporter
from app.etl.pipeline import ETLPipeline

setup_logging()
logger = logging.getLogger("salesforce-etl.cli")

def main():
    parser = argparse.ArgumentParser(description="Salesforce ETL Command Line Interface")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # extract subcommand
    subparsers.add_parser("extract", help="Extract reference master data from Salesforce")

    # query subcommand
    query_parser = subparsers.add_parser("query", help="Execute an arbitrary SOQL query and export results")
    query_parser.add_argument("--soql", type=str, required=True, help="SOQL query string")
    query_parser.add_argument("--output", type=str, default="salesforce_extract.xlsx", help="Output file path (.xlsx or .csv)")
    query_parser.add_argument("--format", type=str, choices=["excel", "csv"], default="excel", help="Output format")
    query_parser.add_argument("--sheet", type=str, default="Salesforce Data", help="Excel sheet name")

    # run subcommand
    run_parser = subparsers.add_parser("run", help="Run full ETL pipeline")
    run_parser.add_argument("--pipeline", type=str, required=False, help="Pipeline name matching field_mappings.yaml (e.g., india_launch)")
    run_parser.add_argument("--file", type=str, required=True, help="Path to input Excel/CSV file")

    # dry-run subcommand
    dry_parser = subparsers.add_parser("dry-run", help="Run ETL pipeline in dry-run mode (no Salesforce upload)")
    dry_parser.add_argument("--pipeline", type=str, required=False, help="Pipeline name matching field_mappings.yaml")
    dry_parser.add_argument("--file", type=str, required=True, help="Path to input Excel/CSV file")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Initialize DB (creates sqlite tables locally)
    init_db()

    db = SessionLocal()
    try:
        if args.command == "extract":
            logger.info("Starting master data extraction...")
            extractor = SalesforceExtractor()
            extractor.extract_reference_data()
            logger.info("Extraction complete.")

        elif args.command == "query":
            logger.info(f"Executing custom SOQL Query: {args.soql}")
            importer = SalesforceQueryImporter()
            if args.format == "csv" or args.output.endswith(".csv"):
                importer.query_to_csv(args.soql, args.output)
            else:
                importer.query_to_excel(args.soql, args.output, sheet_name=args.sheet)
            logger.info(f"Query exported successfully to {args.output}")

        elif args.command in ["run", "dry-run"]:
            is_dry_run = (args.command == "dry-run")
            logger.info(f"Starting pipeline execution (Dry Run: {is_dry_run})...")
            
            pipeline = ETLPipeline(db)
            summary = pipeline.run(
                filepath=args.file,
                source_name=args.pipeline,
                dry_run=is_dry_run
            )
            
            print("\n--- EXECUTION SUMMARY ---")
            for k, v in summary.items():
                print(f"{k:18}: {v}")
            print("-------------------------\n")
            
            if summary["status"] == "FAILED":
                sys.exit(1)
                
    except Exception as exc:
        logger.exception("CLI execution failed")
        sys.exit(2)
    finally:
        db.close()

if __name__ == "__main__":
    main()
