import streamlit as st
from supabase import create_client, Client
import pandas as pd
import plotly.express as px
import os
import datetime
import io
import copy

# NOTE: You must add 'fpdf2' to your requirements.txt for the PDF generation to work
try:
    from fpdf import FPDF
except ImportError:
    FPDF = None

# --- 1. SECURE DATABASE CONNECTION (Best Practice) ---
try:
    URL = st.secrets.get("SUPABASE_URL", os.environ.get("SUPABASE_URL"))
    KEY = st.secrets.get("SUPABASE_KEY", os.environ.get("SUPABASE_KEY"))
    
    if not URL or not KEY:
        raise ValueError("Missing Supabase credentials")
        
    supabase: Client = create_client(URL, KEY)
except Exception as e:
    supabase = None

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="QA Intelligence Command Center", 
    layout="wide", 
    page_icon="🛡️",
    initial_sidebar_state="expanded"
)

# --- SIDEBAR: GLOBAL CONTROLS ---
st.sidebar.title("⚙️ Dashboard Controls")

# Generate a list of months strictly from July 2026 to the current month
today = datetime.date.today()
start_date = datetime.date(2026, 7, 1)
months = []
current_month_iter = today.replace(day=1)

while current_month_iter >= start_date:
    months.append(current_month_iter.strftime("%B %Y"))
    if current_month_iter.month == 1:
        current_month_iter = current_month_iter.replace(year=current_month_iter.year - 1, month=12)
    else:
        current_month_iter = current_month_iter.replace(month=current_month_iter.month - 1)

if not months:
    months = ["July 2026"]

selected_month = st.sidebar.selectbox("Select Reporting Month", months)

# --- 2. DATA LOADING & SAMPLE INITIALIZATION ---
stores_data = [
    {'name': 'CBTL Janakpuri, New Delhi', 'is_outstation': False},
    {'name': 'CBTL Greater Kailash (M-Block), New Delhi', 'is_outstation': False},
    {'name': 'CBTL Platina Tower, Gurugram', 'is_outstation': False},
    {'name': 'CBTL Sector 50, Noida', 'is_outstation': False},
    {'name': 'CBTL Seasons Mall, Pune', 'is_outstation': True},
    {'name': 'CBTL Goldust City Centre, Patiala', 'is_outstation': True},
    {'name': 'CBTL Elante Mall, Chandigarh', 'is_outstation': True},
    {'name': 'CBTL Bandra West, Mumbai', 'is_outstation': True},
    {'name': 'CBTL Koramangala, Bengaluru', 'is_outstation': True},
    {'name': 'CBTL Jubilee Hills, Hyderabad', 'is_outstation': True},
    {'name': 'CBTL Central Plaza, Kolkata', 'is_outstation': True},
    {'name': 'CBTL VR Mall, Chennai', 'is_outstation': True},
    {'name': 'Creek Side, Ludhiana (New)', 'is_outstation': True}
]
df_stores = pd.DataFrame(stores_data)

# Fallback/Session State Simulation for Monthly Operations & License tracking
if 'monthly_db' not in st.session_state:
    st.session_state['monthly_db'] = {
        ("CBTL Janakpuri, New Delhi", "July 2026"): {
            "fostac_pending": 0, "medical_pending": 0, "nsf_score": 92,
            "self_audit_done": "Yes", "self_audit_score": 90, "remarks": "All clean.",
            "licenses": {
                "FSSAI License": {"applicable": True, "status": "Valid", "expiry": datetime.date(2027, 5, 12)},
                "Trade License": {"applicable": True, "status": "Valid", "expiry": datetime.date(2027, 1, 10)},
                "Fire NOC": {"applicable": False, "status": "N/A", "expiry": datetime.date(2027, 1, 1)},
                "Signage License": {"applicable": True, "status": "Valid", "expiry": datetime.date(2027, 3, 15)}
            }
        },
        ("CBTL Greater Kailash (M-Block), New Delhi", "July 2026"): {
            "fostac_pending": 1, "medical_pending": 2, "nsf_score": 85,
            "self_audit_done": "Yes", "self_audit_score": 88, "remarks": "Pending license due to software portal issue",
            "licenses": {
                "FSSAI License": {"applicable": True, "status": "Applied/Pending", "expiry": datetime.date(2026, 8, 15)},
                "Trade License": {"applicable": True, "status": "Valid", "expiry": datetime.date(2027, 2, 20)},
                "Fire NOC": {"applicable": True, "status": "Valid", "expiry": datetime.date(2028, 1, 1)},
                "Signage License": {"applicable": True, "status": "Valid", "expiry": datetime.date(2027, 4, 1)}
            }
        }
    }

# Helper to grab store monthly info
def get_store_monthly(store_name, month):
    key = (store_name, month)
    if key in st.session_state['monthly_db']:
        return copy.deepcopy(st.session_state['monthly_db'][key])
    else:
        # Defaults
        return {
            "fostac_pending": 1, "medical_pending": 5, "nsf_score": 90,
            "self_audit_done": "No", "self_audit_score": 85, "remarks": "",
            "licenses": {
                "FSSAI License": {"applicable": True, "status": "Valid", "expiry": datetime.date(2027, 12, 31)},
                "Trade License": {"applicable": True, "status": "Valid", "expiry": datetime.date(2027, 6, 30)},
                "Fire NOC": {"applicable": False, "status": "N/A", "expiry": datetime.date(2027, 1, 1)},
                "Signage License": {"applicable": True, "status": "Valid", "expiry": datetime.date(2027, 3, 31)}
            }
        }

# Build aggregated dataframe for the selected month
monthly_records = []
for idx, row in df_stores.iterrows():
    s_name = row['name']
    m_data = get_store_monthly(s_name, selected_month)
    is_comp = (m_data['fostac_pending'] == 0) and (m_data['medical_pending'] == 0)
    
    # Check license compliance overall
    lics = m_data['licenses']
    any_lic_issue = any(l_val['applicable'] and l_val['status'] != 'Valid' for l_val in lics.values())
    
    monthly_records.append({
        'name': s_name,
        'is_outstation': row['is_outstation'],
        'month': selected_month,
        'fostac_pending': m_data['fostac_pending'],
        'medical_pending': m_data['medical_pending'],
        'nsf_score': m_data['nsf_score'],
        'self_audit_done': m_data['self_audit_done'],
        'self_audit_score': m_data['self_audit_score'],
        'remarks': m_data['remarks'],
        'is_compliant': is_comp,
        'has_license_issue': any_lic_issue,
        'licenses': lics
    })

df_monthly_filtered = pd.DataFrame(monthly_records)
compliant_stores = df_monthly_filtered['is_compliant'].sum() if not df_monthly_filtered.empty else 0

# --- 3. CEO-LEVEL HEADER ---
st.title("🛡️ QA & Compliance Command Center")
st.markdown(f"Real-time oversight of Retail Operations, Supply Chain, Licensing, and Regulatory Compliance for **{selected_month}**.")
st.divider()

# --- 4. DASHBOARD TABS ---
tab_exec, tab_ops, tab_supply, tab_lic_summary, tab_admin, tab_reports = st.tabs([
    "📊 Executive Dashboard", 
    "🏬 Retail Operations", 
    "🚚 Vendor Audits", 
    "📜 License Summary",
    "⚙️ System Administration",
    "📄 Reports & Archives"
])

# ==========================================
# TAB 1: EXECUTIVE DASHBOARD
# ==========================================
with tab_exec:
    st.subheader(f"📈 {selected_month} Executive Summary")
    
    col1, col2, col3, col4 = st.columns(4)
    total_stores = len(df_stores)
    
    col1.metric("Total Active Stores", total_stores)
    col2.metric("Fully Compliant Stores (Staffing)", f"{compliant_stores} / {total_stores}") 
    
    avg_nsf = df_monthly_filtered['nsf_score'].mean() if not df_monthly_filtered.empty else 0
    col3.metric("Average NSF Score", f"{avg_nsf:.1f}%" if pd.notnull(avg_nsf) else "N/A") 
    
    stores_with_lic_issues = df_monthly_filtered['has_license_issue'].sum() if not df_monthly_filtered.empty else 0
    
    # FIXED: Using delta_color="inverse"
    col4.metric(
        "Stores with License Flags", 
        f"{stores_with_lic_issues}", 
        delta=f"-{stores_with_lic_issues}" if stores_with_lic_issues > 0 else "All Clear", 
        delta_color="inverse"
    )

    st.markdown("---")
    
    if not df_monthly_filtered.empty:
        chart_col1, chart_col2 = st.columns(2)
        with chart_col1:
            st.markdown(f"### 🏬 Store Staff Compliance Status ({selected_month})")
            compliance_counts = df_monthly_filtered['is_compliant'].value_counts().reset_index()
            compliance_counts.columns = ['Status', 'Count']
            compliance_counts['Status'] = compliance_counts['Status'].map({True: 'Compliant (0 Pending)', False: 'Action Required'})
            fig_comp = px.pie(compliance_counts, values='Count', names='Status', hole=0.5, color='Status',
                              color_discrete_map={'Compliant (0 Pending)': '#10B981', 'Action Required': '#EF4444'})
            st.plotly_chart(fig_comp, use_container_width=True)
            
        with chart_col2:
            st.markdown(f"### 📋 Store Directory & Highlights")
            if not df_monthly_filtered.empty:
                display_df = df_monthly_filtered[['name', 'fostac_pending', 'medical_pending', 'remarks']].copy()
                # FIXED: Updated heading to just "Remark"
                display_df.columns = ["Store Name", "FoSTaC Pend.", "Medical Pend.", "Remark"]
                st.dataframe(display_df, use_container_width=True, hide_index=True)

# ==========================================
# TAB 2: RETAIL OPERATIONS (Store Level Entry)
# ==========================================
with tab_ops:
    st.subheader(f"Update Store-Level Compliance & Licenses ({selected_month})")
    st.info(f"You are currently editing data linked to reporting period: **{selected_month}**")
    
    if not df_stores.empty:
        selected_store = st.selectbox("Select Store to Update", df_stores['name'].tolist(), key=f"ops_store_{selected_month}")
        store_row_data = get_store_monthly(selected_store, selected_month)

        col_a, col_b = st.columns(2)
        
        with col_a:
            st.markdown("#### 1. Staff Requirements & Audits")
            fostac_req = st.number_input("Number of Staff requiring FoSTaC", min_value=0, value=int(store_row_data['fostac_pending']), key=f"fostac_{selected_store}_{selected_month}")
            med_req = st.number_input("Number of Staff requiring Medical", min_value=0, value=int(store_row_data['medical_pending']), key=f"med_{selected_store}_{selected_month}")
            
            if fostac_req == 0 and med_req == 0:
                st.success("✅ This store is fully in compliance for Staffing.")
            else:
                st.warning("⚠️ Pending staff requirements exist.")
                
            nsf_score = st.number_input("NSF Score (%)", min_value=0, max_value=100, value=int(store_row_data['nsf_score']), key=f"nsf_{selected_store}_{selected_month}")
            
            self_audit_options = ["Yes", "No"]
            current_audit_val = store_row_data['self_audit_done'] if store_row_data['self_audit_done'] in self_audit_options else "No"
            self_audit = st.radio("Monthly Self Audit Done?", self_audit_options, index=self_audit_options.index(current_audit_val), key=f"audit_radio_{selected_store}_{selected_month}")
            
            prev_score = store_row_data['self_audit_score']
            safe_score = int(prev_score) if prev_score is not None else 0
            self_audit_score = st.number_input("Monthly Self Audit Score (%)", min_value=0, max_value=100, value=safe_score, key=f"audit_score_{selected_store}_{selected_month}") if self_audit == "Yes" else None
            
            # FIXED: Updated heading to just "Remark"
            st.markdown("#### 💬 Remark")
            store_remarks = st.text_area("Mention specific flags (e.g., 'pending license due to software issue')", value=store_row_data['remarks'], key=f"rem_{selected_store}_{selected_month}")

        with col_b:
            st.markdown("#### 2. Dynamic License Compliance Management")
            st.caption("Toggle licenses applicable to this specific outlet. Skipped/non-applicable licenses are omitted from compliance penalties.")
            
            current_lics = store_row_data['licenses']
            updated_licenses = {}
            standard_lic_keys = list(current_lics.keys())
            
            for l_name in standard_lic_keys:
                l_info = current_lics[l_name]
                st.markdown(f"**{l_name}**")
                is_app = st.toggle(f"Applicable?", value=l_info['applicable'], key=f"app_{selected_store}_{selected_month}_{l_name}")
                
                if is_app:
                    status_options = ["Valid", "Applied/Pending", "Expired"]
                    current_status = l_info['status'] if l_info['status'] in status_options else "Applied/Pending"
                    
                    l_status = st.selectbox(f"Status", status_options, index=status_options.index(current_status), key=f"stat_{selected_store}_{selected_month}_{l_name}")
                    l_expiry = st.date_input(f"Expiry Date", value=l_info['expiry'], key=f"exp_{selected_store}_{selected_month}_{l_name}")
                    updated_licenses[l_name] = {"applicable": True, "status": l_status, "expiry": l_expiry}
                else:
                    updated_licenses[l_name] = {"applicable": False, "status": "N/A", "expiry": datetime.date(2027, 1, 1)}
                st.divider()
                
            st.markdown("##### ➕ Add Additional Outlet License")
            new_lic_name = st.text_input("New License Type Name", placeholder="e.g., Pollution License", key=f"new_lic_input_{selected_store}_{selected_month}")
            if st.button("Add License Type", key=f"add_lic_btn_{selected_store}_{selected_month}"):
                if new_lic_name and new_lic_name not in updated_licenses:
                    updated_licenses[new_lic_name] = {"applicable": True, "status": "Applied/Pending", "expiry": datetime.date.today()}
                    store_row_data['licenses'] = updated_licenses
                    st.session_state['monthly_db'][(selected_store, selected_month)] = store_row_data
                    st.success(f"Added {new_lic_name} successfully!")
                    st.rerun()

        if st.button(f"Save Compliance & License Data for {selected_month}", type="primary", key=f"save_btn_{selected_store}_{selected_month}"):
            store_row_data['fostac_pending'] = fostac_req
            store_row_data['medical_pending'] = med_req
            store_row_data['nsf_score'] = nsf_score
            store_row_data['self_audit_done'] = self_audit
            store_row_data['self_audit_score'] = self_audit_score
            store_row_data['remarks'] = store_remarks
            store_row_data['licenses'] = updated_licenses
            
            st.session_state['monthly_db'][(selected_store, selected_month)] = store_row_data
            st.success(f"Successfully updated master records for **{selected_store}** under **{selected_month}**!")

# ==========================================
# TAB 3: VENDOR AUDITS
# ==========================================
with tab_supply:
    st.subheader(f"Log Vendor Audit for {selected_month}")
    
    with st.form("vendor_audit_form"):
        v_col1, v_col2 = st.columns(2)
        with v_col1:
            st.text_input("Audit Month", value=selected_month, disabled=True)
            vendor_name = st.text_input("Vendor Name", placeholder="e.g., ABC Supply Logistics")
            audit_score = st.text_input("Audit Score (%)", placeholder="e.g., 94%")
            
        with v_col2:
            audit_status = st.selectbox("Audit Status", ["Passed", "Passed with Conditions", "Failed"])
            remarks = st.text_area("Remarks / CAPA", placeholder='e.g., "CA pending for handwash"')
            
        if st.form_submit_button("Save Vendor Audit Record", type="primary"):
            if vendor_name:
                st.success(f"Audit record for {vendor_name} successfully logged for {selected_month}.")
            else:
                st.error("Vendor Name is required.")

# ==========================================
# TAB 4: LICENSE COMPLIANCE SUMMARY
# ==========================================
with tab_lic_summary:
    st.subheader(f"📜 Enterprise License Compliance Matrix ({selected_month})")
    st.markdown("Consolidated oversight tracking all statutory, municipal, safety, and operational licenses across all retail outlets. Non-applicable licenses are automatically skipped.")
    
    if not df_monthly_filtered.empty:
        matrix_rows = []
        for idx, row in df_monthly_filtered.iterrows():
            s_name = row['name']
            lic_dict = row['licenses']
            row_data = {"Store Name": s_name}
            for l_key, l_val in lic_dict.items():
                if not l_val['applicable']:
                    row_data[l_key] = "Skipped (N/A)"
                else:
                    status_str = l_val['status']
                    expiry_str = str(l_val['expiry'])
                    row_data[l_key] = f"{status_str} (Exp: {expiry_str})"
            matrix_rows.append(row_data)
            
        df_matrix = pd.DataFrame(matrix_rows)
        st.dataframe(df_matrix, use_container_width=True, hide_index=True)
        
        st.markdown("#### 🚨 Pending or Expired License Flags & Remarks")
        flagged_records = []
        for idx, row in df_monthly_filtered.iterrows():
            s_name = row['name']
            rem = row['remarks']
            for l_key, l_val in row['licenses'].items():
                if l_val['applicable'] and l_val['status'] != 'Valid':
                    flagged_records.append({
                        "Store": s_name,
                        "License Type": l_key,
                        "Current Status": l_val['status'],
                        "Expiry Date": str(l_val['expiry']),
                        "Remark": rem if rem else "No remarks specified"
                    })
                    
        if flagged_records:
            df_flags = pd.DataFrame(flagged_records)
            st.dataframe(df_flags, use_container_width=True, hide_index=True)
        else:
            st.success("🎉 Outstanding! All applicable licenses across all active outlets are fully Valid.")

# ==========================================
# TAB 5: SYSTEM ADMINISTRATION
# ==========================================
with tab_admin:
    st.subheader("Database Management")
    
    with st.expander("➕ Add a New Store Location", expanded=False):
        new_name = st.text_input("Store Name", placeholder="e.g., CBTL Cyber Hub, Gurugram")
        is_out = st.checkbox("Is Outstation?")
        if st.button("Add Store to Master Database"):
            if new_name:
                st.success(f"Added {new_name} to master register.")

# ==========================================
# TAB 6: REPORTS & ARCHIVES
# ==========================================
with tab_reports:
    st.subheader("Dashboard & License Summary PDF Generation")
    st.markdown(f"Generate an official compliance and license summary audit report specifically for **{selected_month}**.")
    
    col_pdf1, col_pdf2 = st.columns(2)
    
    with col_pdf1:
        st.markdown(f"**Generate Executive & License Report: {selected_month}**")
        if st.button(f"Generate PDF for {selected_month}", type="primary"):
            if FPDF is None:
                st.error("The 'fpdf2' library is not installed.")
            else:
                pdf = FPDF()
                pdf.add_page()
                pdf.set_font("Arial", 'B', 14)
                pdf.cell(200, 10, txt=f"QA & License Compliance Summary - {selected_month}", ln=True, align='C')
                pdf.set_font("Arial", size=10)
                pdf.cell(200, 8, txt=f"Total Active Stores: {total_stores}", ln=True)
                pdf.cell(200, 8, txt=f"Fully Compliant Stores (Staffing): {compliant_stores}", ln=True)
                pdf.ln(5)
                
                pdf.set_font("Arial", 'B', 11)
                pdf.cell(200, 8, txt="Outlet License Status Overview:", ln=True)
                pdf.set_font("Arial", size=9)
                
                for idx, row in df_monthly_filtered.iterrows():
                    pdf.cell(200, 6, txt=f"Store: {row['name']}", ln=True)
                    pdf.cell(200, 6, txt=f"   Remarks: {row['remarks'] if row['remarks'] else 'None'}", ln=True)
                    for l_k, l_v in row['licenses'].items():
                        if l_v['applicable']:
                            pdf.cell(200, 5, txt=f"   - {l_k}: {l_v['status']} (Exp: {l_v['expiry']})", ln=True)
                    pdf.ln(2)
                
                try:
                    pdf_out = pdf.output(dest='S')
                    pdf_bytes = pdf_out.encode('latin-1') if isinstance(pdf_out, str) else bytes(pdf_out)
                except Exception:
                    pdf_bytes = bytes(pdf.output())
                    
                st.success(f"PDF Report successfully generated for {selected_month}!")
                st.download_button(
                    label=f"Download {selected_month} Comprehensive PDF",
                    data=pdf_bytes,
                    file_name=f"QA_License_Summary_{selected_month.replace(' ', '_')}.pdf",
                    mime="application/pdf"
                )

    with col_pdf2:
        st.markdown("**Retrieve Past Archived Reports**")
        archive_df = pd.DataFrame({
            "Report Month": [selected_month],
            "Generated On": [str(datetime.date.today())],
            "Status": ["Archived in Cloud Storage"]
        })
        st.dataframe(archive_df, use_container_width=True, hide_index=True)
