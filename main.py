import os
import time
import re
from thefuzz import fuzz

# --- CONFIG ---
ttb_warning = (
    "According to the Surgeon General, women should not drink alcoholic beverages "
    "during pregnancy because of the risk of birth defects. (2) Consumption of "
    "alcoholic beverages impairs your ability to drive a car or operate machinery, "
    "and may cause health problems."
)

# --- MOCK AI ENGINE ---
def scan_mock(filepath):
    """A quick API call to an AI Vision model. This fake function can be swapped out for a real AI call once firewall restrictions are modified"""
    print(f"    [AI] Scanning '{filepath}'...")
    time.sleep(3) 
    
    return {
        "producer_name": "OLD JOHN DISTILLERY",
        "spirit_class": "Tennessee Straight Bourbon Whiskey",
        "alcohol_vol": "45%",
        "net_capacity": "750 mL",
        "gov_warning_header": "GOVERNMENT WARNING:",
        "gov_warning_text": ttb_warning
    }

# --- VERIFICATION LOGIC ---
def check_compliance(form_data, label_data):
    """
    Compares what was submitted on the COLA form vs what the AI read from the label.
    """
    audit_report = {}
    
    # 1. Brand Name (Fuzzy Match > 85%)
    f_brand = form_data.get("producer_name", "").lower()
    l_brand = label_data.get("producer_name", "").lower()
    match_score = fuzz.ratio(f_brand, l_brand)
    
    audit_report["producer"] = {
        "passed_check": match_score > 85,
        "detail": f"Score: {match_score}/100" + (" (Fuzzy Match)" if 85 < match_score < 100 else "")
    }

    # 2. ABV (Strict numeric extraction and match)
    f_abv = re.sub(r'[^\d.]', '', form_data.get("alcohol_vol", ""))
    l_abv = re.sub(r'[^\d.]', '', label_data.get("alcohol_vol", ""))
    
    audit_report["abv_content"] = {
        "passed_check": f_abv == l_abv,
        "detail": f"Expected: {f_abv} | Found: {l_abv}"
    }
    
    # 3. Government Warning (Strict exact match and caps check)
    has_correct_prefix = label_data.get("gov_warning_header", "") == "GOVERNMENT WARNING:"
    
    scanned_warn = " ".join(label_data.get("gov_warning_text", "").split()).lower()
    required_warn = " ".join(ttb_warning.split()).lower()
    warning_matches = scanned_warn == required_warn
    
    audit_report["health_warning"] = {
        "passed_check": has_correct_prefix and warning_matches,
        "detail": "Prefix exact match & body exact match" if (has_correct_prefix and warning_matches) else "Mismatch in text or prefix capitalization"
    }

    return audit_report

# --- BATCH PROCESSOR ---
def run_batch_job(db_records, upload_queue):
    """Processes a list of image files against the pending COLA database."""
    print("==================================================")
    print(" TTB BATCH LABEL VERIFICATION SYSTEM")
    print("==================================================\n")
    
    for img in upload_queue:
        print(f" Processing: {img}")
        
        # Look up expected data
        form_info = db_records.get(img)
        if not form_info:
            print(f"     Error: No COLA application found for {img}\n")
            continue
            
        # Extract & Verify
        label_info = scan_mock(img)
        checks = check_compliance(form_info, label_info)
        
        # Report
        is_compliant = all(result['passed_check'] for result in checks.values())
        
        for key, result in checks.items():
            icon = " PASS" if result['passed_check'] else " FAIL"
            print(f"    {icon} - {key.upper()}: {result['detail']}")
            
        if is_compliant:
            print("     RESULT: LABEL COMPLIANT\n")
        else:
            print("     RESULT: COMPLIANCE FAILURE - REJECT LABEL\n")

if __name__ == "__main__":
    # Dummy DB mapping filenames to their submitted COLA form data
    dummy_db = {
        "batch_folder/old_john_front.jpg": {
            "producer_name": "Old John Distillery", 
            "spirit_class": "Tennessee Straight Bourbon Whiskey",
            "alcohol_vol": "45%",
            "net_capacity": "750 mL"
        },
        "batch_folder/old_john_typo.jpg": {
            "producer_name": "Old John Distillery", 
            "spirit_class": "Tennessee Straight Bourbon Whiskey",
            "alcohol_vol": "45%",
            "net_capacity": "750 mL"
        }
    }
    
    # Files uploaded by an agent
    test_files = [
        "batch_folder/old_john_front.jpg",
        "batch_folder/old_john_typo.jpg"
    ]
    
    run_batch_job(dummy_db, test_files)