import os
import pandas as pd
from app.core.config import settings

def generate_all_mock_data():
    sample_dir = settings.SAMPLE_DATA_DIR
    export_dir = os.path.join(settings.DATA_DIR, "salesforce_exports")
    input_dir = os.path.join(settings.DATA_DIR, "input")
    
    for d in [sample_dir, export_dir, input_dir]:
        os.makedirs(d, exist_ok=True)
        
    print("Generating Salesforce Reference exports...")
    
    # 01_accounts
    accounts = [
        {"Id": "acc_001", "Name": "Acme Corp", "AccountNumber": "ACT100"},
        {"Id": "acc_002", "Name": "Globex Corporation", "AccountNumber": "ACT200"},
        {"Id": "acc_003", "Name": "Initech LLC", "AccountNumber": "ACT300"},
    ]
    pd.DataFrame(accounts).to_excel(os.path.join(export_dir, "01_accounts.xlsx"), index=False)
    pd.DataFrame(accounts).to_excel(os.path.join(sample_dir, "01_accounts.xlsx"), index=False)
    
    # 02_products
    products = [
        {"Id": "prod_001", "Name": "Solar Panel v1", "ProductCode": "PRD_SLR_01", "Family": "Energy"},
        {"Id": "prod_002", "Name": "Wind Turbine v2", "ProductCode": "PRD_WND_02", "Family": "Energy"},
        {"Id": "prod_003", "Name": "Battery Storage v1", "ProductCode": "PRD_BAT_03", "Family": "Energy"},
    ]
    pd.DataFrame(products).to_excel(os.path.join(export_dir, "02_products.xlsx"), index=False)
    pd.DataFrame(products).to_excel(os.path.join(sample_dir, "02_products.xlsx"), index=False)
    
    # 03_budgets
    budgets = [
        {"Id": "bud_001", "Name": "Launch Budget India", "Budget_Code__c": "BDG_IND_2026", "Allocated_Amount__c": 50000.0},
        {"Id": "bud_002", "Name": "Launch Budget UAE", "Budget_Code__c": "BDG_UAE_2026", "Allocated_Amount__c": 75000.0},
    ]
    pd.DataFrame(budgets).to_excel(os.path.join(export_dir, "03_budgets.xlsx"), index=False)
    pd.DataFrame(budgets).to_excel(os.path.join(sample_dir, "03_budgets.xlsx"), index=False)
    
    # 04_checklists
    checklists = [
        {"Id": "chk_001", "Name": "Standard Launch Checklist", "Checklist_Code__c": "CHK_STD_01", "Status__c": "Active"},
        {"Id": "chk_002", "Name": "Alternative Launch Checklist", "Checklist_Code__c": "CHK_ALT_02", "Status__c": "Draft"},
    ]
    pd.DataFrame(checklists).to_excel(os.path.join(export_dir, "04_checklists.xlsx"), index=False)
    pd.DataFrame(checklists).to_excel(os.path.join(sample_dir, "04_checklists.xlsx"), index=False)
    
    print("Generating Sample forms...")
    
    # India form
    # Columns: Name, Email, Product, Budget_Code, Budget, Checklist, CRM_ID
    india_data = [
        # Successful row
        {"Name": "John Doe", "Email": "john@example.com", "Product": "PRD_SLR_01", "Budget_Code": "BDG_IND_2026", "Budget": "10000", "Checklist": "CHK_STD_01", "CRM_ID": "camp_india_01"},
        # Lookup failure row (non-existent product code)
        {"Name": "Jane Smith", "Email": "jane@example.com", "Product": "INVALID_PROD_CODE", "Budget_Code": "BDG_IND_2026", "Budget": "5000", "Checklist": "CHK_STD_01", "CRM_ID": "camp_india_02"},
        # Validation failure row (invalid email, negative budget)
        {"Name": "Bob Johnson", "Email": "bob-invalid-email", "Product": "PRD_WND_02", "Budget_Code": "BDG_IND_2026", "Budget": "-200", "Checklist": "CHK_STD_01", "CRM_ID": "camp_india_03"},
        # Duplicate row (same email, product, event as row 1)
        {"Name": "John Doe", "Email": "john@example.com", "Product": "PRD_SLR_01", "Budget_Code": "BDG_IND_2026", "Budget": "10000", "Checklist": "CHK_STD_01", "CRM_ID": "camp_india_01"},
        # Salesforce push failure row (triggered by email)
        {"Name": "Sfdc Failer", "Email": "fail_sfdc@example.com", "Product": "PRD_SLR_01", "Budget_Code": "BDG_IND_2026", "Budget": "12000", "Checklist": "CHK_STD_01", "CRM_ID": "camp_india_01"},
    ]
    pd.DataFrame(india_data).to_excel(os.path.join(sample_dir, "sample_form_india.xlsx"), index=False)
    pd.DataFrame(india_data).to_excel(os.path.join(input_dir, "sample_form_india.xlsx"), index=False)
    
    # UAE form
    # Columns: Full_Name, Email_Address, Product_Code, Budget_Code, Allocated_Budget, Checklist_Status, CRM_ID
    uae_data = [
        {"Full_Name": "Mohammed Ali", "Email_Address": "mohammed@example.ae", "Product_Code": "PRD_WND_02", "Budget_Code": "BDG_UAE_2026", "Allocated_Budget": "15000", "Checklist_Status": "CHK_STD_01", "CRM_ID": "camp_uae_01"},
        {"Full_Name": "Sarah Connor", "Email_Address": "sarah@example.ae", "Product_Code": "PRD_BAT_03", "Budget_Code": "BDG_UAE_2026", "Allocated_Budget": "20000", "Checklist_Status": "CHK_ALT_02", "CRM_ID": "camp_uae_02"},
    ]
    pd.DataFrame(uae_data).to_excel(os.path.join(sample_dir, "sample_form_uae.xlsx"), index=False)
    pd.DataFrame(uae_data).to_excel(os.path.join(input_dir, "sample_form_uae.xlsx"), index=False)
    
    print("Mock data generation complete.")

if __name__ == "__main__":
    generate_all_mock_data()
