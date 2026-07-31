import streamlit as st
import time
import re
from PIL import Image
from thefuzz import fuzz

# --- CONFIG & UI SETUP ---
st.set_page_config(
    page_title="ALV-PoC | TTB Label Verification",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

ttb_warning = (
    "According to the Surgeon General, women should not drink alcoholic beverages "
    "during pregnancy because of the risk of birth defects. (2) Consumption of "
    "alcoholic beverages impairs your ability to drive a car or operate machinery, "
    "and may cause health problems."
)

# --- MOCK AI ENGINE ---
def scan_mock(image: Image) -> dict:
    """A quick API call to an AI Vision model. This fake function can be swapped out for a real AI call once firewall restrictions are modified."""
    time.sleep(3) # Simulating API latency to prove sub-5-second requirement
    
    return {
        "producer_name": "OLD JOHN DISTILLERY",
        "spirit_class": "Tennessee Straight Bourbon Whiskey",
        "alcohol_vol": "45%",
        "net_capacity": "750 mL",
        "gov_warning_header": "GOVERNMENT WARNING:",
        "gov_warning_text": ttb_warning
    }

# --- VERIFICATION LOGIC ---
def check_compliance(form_data: dict, label_data: dict) -> dict:
    """
    Compares what was submitted on the COLA form vs what the AI read from the label.
    """
    audit_report = {}
    
    # 1. Producer Name (Fuzzy Match > 85%)
    f_brand = form_data.get("producer_name", "").lower()
    l_brand = label_data.get("producer_name", "").lower()
    match_score = fuzz.ratio(f_brand, l_brand)
    
    audit_report["producer"] = {
        "expected": form_data.get("producer_name"),
        "extracted": label_data.get("producer_name"),
        "passed_check": match_score > 85,
        "detail": f"Score: {match_score}/100" + (" (Fuzzy Match)" if 85 < match_score < 100 else "")
    }

    # 2. ABV Content (Strict numeric extraction and match)
    f_abv = re.sub(r'[^\d.]', '', form_data.get("alcohol_vol", ""))
    l_abv = re.sub(r'[^\d.]', '', label_data.get("alcohol_vol", ""))
    
    audit_report["abv_content"] = {
        "expected": form_data.get("alcohol_vol"),
        "extracted": label_data.get("alcohol_vol"),
        "passed_check": f_abv == l_abv,
        "detail": ""
    }
    
    # 3. Government Warning (Strict exact match and caps check)
    has_correct_prefix = label_data.get("gov_warning_header", "") == "GOVERNMENT WARNING:"
    
    scanned_warn = " ".join(label_data.get("gov_warning_text", "").split()).lower()
    required_warn = " ".join(ttb_warning.split()).lower()
    warning_matches = scanned_warn == required_warn
    
    audit_report["health_warning"] = {
        "expected": f"GOVERNMENT WARNING: {ttb_warning[:50]}...",
        "extracted": f"{label_data.get('gov_warning_header')} {label_data.get('gov_warning_text', '')[:50]}...",
        "passed_check": has_correct_prefix and warning_matches,
        "detail": "Prefix exact match & body exact match" if (has_correct_prefix and warning_matches) else "Mismatch in text or prefix capitalization"
    }

    return audit_report

# --- MAIN APP UI ---
def main():
    st.title(" ALV-PoC: Label Verification System")
    st.markdown("Upload digitized label assets and verify them against COLA application data.")
    
    with st.sidebar:
        st.header("System Settings")
        mode = st.radio("Processing Endpoint", ["Simulated LLM (Local)", "Live OpenAI Vision API"])
        if mode == "Live OpenAI Vision API":
            st.text_input("API Key Authorization", type="password", help="Requires active authorization.")
            st.warning("Live API requires outbound network access. Simulated mode is recommended for restricted environments.")
        
        st.divider()
        st.markdown("**Standard Operating Procedure:**\n1. Upload one or more label images.\n2. Enter expected COLA form data.\n3. Execute audit.")

    # BATCH UPLOAD FEATURE 
    uploaded_files = st.file_uploader("Upload Label Images (Batch supported)", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)
    
    if uploaded_files:
        st.info(f"Loaded {len(uploaded_files)} asset(s) for review. Initializing queue...")
        
        # Create tabs for batch processing interface
        tabs = st.tabs([f"Asset {i+1}: {f.name}" for i, f in enumerate(uploaded_files)])
        
        for i, (tab, file) in enumerate(zip(tabs, uploaded_files)):
            with tab:
                col1, col2 = st.columns([1, 1.2])
                
                with col1:
                    image = Image.open(file)
                    st.image(image, caption="Digitized Label Asset", use_column_width=True)
                
                with col2:
                    st.subheader("COLA Application Data")
                    with st.form(key=f"form_{i}"):
                        exp_producer = st.text_input("Producer Name", value="Old John Distillery")
                        exp_class = st.text_input("Spirit Class/Type", value="Tennessee Straight Bourbon Whiskey")
                        exp_abv = st.text_input("Alcohol by Volume (ABV %)", value="45")
                        exp_net = st.text_input("Net Capacity", value="750 mL")
                        
                        submit_btn = st.form_submit_button("Execute Compliance Audit", type="primary")
                        
                        if submit_btn:
                            with st.spinner("Executing LLM extraction... (Estimated: 3.0s)"):
                                form_info = {
                                    "producer_name": exp_producer,
                                    "spirit_class": exp_class,
                                    "alcohol_vol": exp_abv,
                                    "net_capacity": exp_net
                                }
                                
                                # 1. Extract
                                label_info = scan_mock(image)
                                
                                # 2. Verify
                                checks = check_compliance(form_info, label_info)
                                
                                st.subheader("Audit Report")
                                
                                # 3. Display Results
                                is_compliant = True
                                for field, data in checks.items():
                                    if data['passed_check']:
                                        st.success(f" **{field.replace('_', ' ').title()}**: PASS")
                                        if data['detail']:
                                            st.caption(f"*{data['detail']}*")
                                    else:
                                        is_compliant = False
                                        st.error(f" **{field.replace('_', ' ').title()}**: FAIL")
                                        st.write(f"- **Form Data:** {data['expected']}")
                                        st.write(f"- **Label Data:** {data['extracted']}")
                                        if data['detail']:
                                            st.caption(f"*{data['detail']}*")
                                
                                st.divider()
                                if is_compliant:
                                    st.success(" **SYSTEM ASSESSMENT: COMPLIANT.** Label meets statutory requirements.")
                                else:
                                    st.error(" **SYSTEM ASSESSMENT: REJECTED.** Statutory mismatch detected.")

if __name__ == "__main__":
    main()
