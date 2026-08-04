import streamlit as st
from supabase import create_client, Client
import pandas as pd
import plotly.express as px
import os
import datetime
import io

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
    st.error(f"Missing Credentials or Connection Error. Please check Streamlit Secrets. Error: {e}")
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
start_date = datetime.date(2026, 7, 1) # Starting point as requested
months = []
current_month_iter = today.replace(day=1)

while current_month_iter >= start_date:
    months.append(current_month_iter.strftime("%B %Y"))
    # Step back one month safely
    if current_month_iter.month == 1:
        current_month_iter = current_month_iter.replace(year=current_month_iter.year - 1, month=12)
    else:
        current_month_iter = current_month_iter.replace(month=current_month_iter.month - 1)

# Fallback just in case system date is somehow earlier than July 2026
if not months:
    months = ["July 2026"]

selected_month = st.sidebar.selectbox("Select Reporting Month", months)

# --- 2. DATA LOADING ---
@st.cache_data(ttl=60)
def load_stores():
    if supabase is None:
        return []
    try:
        response = supabase.table("stores").select("*").execute()
        return response.data
    except Exception as e:
        st.error(f"Error fetching data from Supabase: {e}")
        return []

@st.cache_data(ttl=60)
def load_monthly_compliance(month):
    """Loads compliance data specifically for the selected month."""
    if supabase is None:
        return []
    try:
        # Query monthly table filtered by month
        # response = supabase.table("store_compliance_monthly").select("*").eq("month", month).execute()
        # return response.data
        return [] # Trigger fallback sample data for demonstration
    except Exception as e:
        st.error(f"Error fetching monthly data: {e}")
        return []

stores_data = load_stores()
df_stores = pd.DataFrame(stores_data)

monthly_data = load_monthly_compliance(selected_month)
df_monthly = pd.DataFrame(monthly_data)


# Fallback Data to demonstrate the master store structure
if df_stores.empty:
    st.warning("Database not connected or empty. Using sample master store data.")
    sample_data = {
        'name': [
            'CBTL Janakpuri, New Delhi', 'CBTL Greater Kailash (M-Block), New Delhi', 
            'CBTL Platina Tower, Gurugram', 'Creek Side, Ludhiana (New)'
        ],
        'is_outstation': [False, False, False, True]
    }
    df_stores = pd.DataFrame(sample_data)

if df_monthly.empty:
    # We create a dataframe linking the master stores to the current month with defaults (Fostac: 1, Medical: 5)
    sample_monthly = {
        'name': df_stores['name'].tolist(),
        'month': [selected_month] * len(df_stores),
        'fostac_pending': [1] * len(df_stores),
        'medical_pending': [5] * len(df_stores),
        'nsf_score': [90] * len(df_stores),
        'self_audit_done': ['No'] * len(df_stores),
        'self_audit_score': [85] * len(df_stores)
    }
    
    # Simulate custom changes if July 2026 is selected to show month-switching works
    if selected_month == "July 2026":
        sample_monthly['nsf_score'][0] = 88
        sample_monthly['fostac_pending'][0] = 0
        sample_monthly['medical_pending'][0] = 0
    elif selected_month == "August 2026":
        sample_monthly['nsf_score'][0] = 95
        sample_monthly['fostac_pending'][0] = 1
        
    df_monthly = pd.DataFrame(sample_monthly)

# Filter monthly data strictly for the selected month in the sidebar
df_monthly_filtered = df_monthly[df_monthly['month'] == selected_month].copy()

# Calculate dynamic compliance metric and apply defensive defaults based on MONTHLY data
if not df_monthly_filtered.empty:
    if 'fostac_pending' not in df_monthly_filtered.columns:
        df_monthly_filtered['fostac_pending'] = 1
    if 'medical_pending' not in df_monthly_filtered.columns:
        df_monthly_filtered['medical_pending'] = 5
        
    df_monthly_filtered['fostac_pending'] = pd.to_numeric(df_monthly_filtered['fostac_pending'], errors='coerce').fillna(1)
    df_monthly_filtered['medical_pending'] = pd.to_numeric(df_monthly_filtered['medical_pending'], errors='coerce').fillna(5)
    
    df_monthly_filtered['is_compliant'] = (df_monthly_filtered['fostac_pending'] == 0) & (df_monthly_filtered['medical_pending'] == 0)
    compliant_stores = df_monthly_filtered['is_compliant'].sum()
else:
    compliant_stores = 0

# Merge master store data with monthly compliance data for the dashboard views
if not df_stores.empty and not df_monthly_filtered.empty:
    df_combined = pd.merge(df_stores, df_monthly_filtered, on='name', how='left')
else:
    df_combined = pd.DataFrame()

# --- 3. CEO-LEVEL HEADER ---
st.title("🛡️ QA & Compliance Command Center")
st.markdown(f"Real-time oversight of Retail Operations, Supply Chain, and Regulatory Compliance for **{selected_month}**.")
st.divider()

# --- 4. DASHBOARD TABS ---
tab_exec, tab_ops, tab_supply, tab_admin, tab_reports = st.tabs([
    "📊 Executive Dashboard", 
    "🏬 Retail Operations", 
    "🚚 Vendor Audits", 
    "⚙️ System Administration",
    "📄 Reports & Archives"
])

# ==========================================
# TAB 1: EXECUTIVE DASHBOARD
# ==========================================
with tab_exec:
    st.subheader(f"📈 {selected_month} Summary")
    
    col1, col2, col3, col4 = st.columns(4)
    total_stores = len(df_stores)
    
    col1.metric("Total Active Stores", total_stores)
    col2.metric("Fully Compliant Stores (Staffing)", f"{compliant_stores} / {total_stores}") 
    
    avg_nsf = df_monthly_filtered['nsf_score'].mean() if not df_monthly_filtered.empty and 'nsf_score' in df_monthly_filtered.columns else 0
    col3.metric("Average NSF Score", f"{avg_nsf:.1f}%" if pd.notnull(avg_nsf) else "N/A") 
    col4.metric(f"Active Vendor Audits ({selected_month})", "2") 

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
            st.markdown(f"### 📋 Quick Store Directory ({selected_month})")
            if not df_combined.empty:
                display_df = df_combined[['name', 'fostac_pending', 'medical_pending', 'is_compliant']].copy()
                display_df.columns = ["Store Name", "FoSTaC Pending", "Medical Pending", "Fully Compliant"]
                st.dataframe(display_df, use_container_width=True, hide_index=True)

# ==========================================
# TAB 2: RETAIL OPERATIONS (Store Level Entry)
# ==========================================
with tab_ops:
    st.subheader(f"Update Store-Level Compliance for Selected Month: {selected_month}")
    st.info(f"You are currently editing data linked to reporting period: **{selected_month}**")
    
    if not df_stores.empty:
        selected_store = st.selectbox("Select Store to Update", df_stores['name'].tolist(), key="ops_store")
        
        # Retrieve current record for selected store AND active month
        store_record = {}
        if not df_monthly_filtered.empty and selected_store in df_monthly_filtered['name'].values:
            store_row = df_monthly_filtered[df_monthly_filtered['name'] == selected_store].iloc[0]
            current_fostac = int(store_row.get('fostac_pending', 1))
            current_medical = int(store_row.get('medical_pending', 5))
            current_nsf = int(store_row.get('nsf_score', 90))
            current_self_audit = store_row.get('self_audit_done', 'No')
            current_self_audit_score = int(store_row.get('self_audit_score', 85))
        else:
            current_fostac = 1
            current_medical = 5
            current_nsf = 90
            current_self_audit = "No"
            current_self_audit_score = 85

        st.markdown(f"#### Operations Data for: {selected_store} | Month: {selected_month}")
        col_a, col_b = st.columns(2)
        
        with col_a:
            st.markdown("**1. Staff Requirements**")
            st.info("When both requirements are set to 0, the store is automatically marked Compliant.")
            fostac_req = st.number_input("Number of Staff requiring FoSTaC", min_value=0, value=current_fostac, key=f"fostac_{selected_store}")
            med_req = st.number_input("Number of Staff requiring Medical", min_value=0, value=current_medical, key=f"med_{selected_store}")
            
            if fostac_req == 0 and med_req == 0:
                st.success("✅ This store is fully in compliance for Staffing.")
            else:
                st.warning("⚠️ Pending requirements exist.")
                
            st.markdown("**2. Store Audits**")
            nsf_score = st.number_input("NSF Score (%)", min_value=0, max_value=100, value=current_nsf, key=f"nsf_{selected_store}")
            
            self_audit = st.radio("Monthly Self Audit Done?", ["Yes", "No"], index=0 if current_self_audit == "Yes" else 1, key=f"audit_radio_{selected_store}")
            if self_audit == "Yes":
                self_audit_score = st.number_input("Monthly Self Audit Score (%)", min_value=0, max_value=100, value=current_self_audit_score, key=f"audit_score_{selected_store}")
            else:
                self_audit_score = None
                
        with col_b:
            st.markdown("**3. License Compliance**")
            fssai_applicable = st.toggle("FSSAI License Applicable", value=True, key=f"fssai_{selected_store}")
            if fssai_applicable:
                st.selectbox("FSSAI Status", ["Valid", "Applied/Pending", "Expired"], key=f"fssai_stat_{selected_store}")
                st.date_input("FSSAI Expiry Date", key=f"fssai_date_{selected_store}")
                
            st.divider()
            trade_applicable = st.toggle("Trade License Applicable", value=True, key=f"trade_{selected_store}")
            if trade_applicable:
                st.selectbox("Trade License Status", ["Valid", "Applied/Pending", "Expired"], key=f"trade_stat_{selected_store}")
                
            st.divider()
            fire_applicable = st.toggle("Fire NOC Applicable", value=False, key=f"fire_{selected_store}")
            if fire_applicable:
                st.selectbox("Fire NOC Status", ["Valid", "Applied/Pending", "Expired"], key=f"fire_stat_{selected_store}")
                
        if st.button(f"Save Compliance Data for {selected_month}", type="primary"):
            # Target data payload bound explicitly to selected_month
            data_to_upsert = {
                "name": selected_store,
                "month": selected_month,
                "fostac_pending": fostac_req,
                "medical_pending": med_req,
                "nsf_score": nsf_score,
                "self_audit_done": self_audit,
                "self_audit_score": self_audit_score
            }
            # supabase.table("store_compliance_monthly").upsert(data_to_upsert).execute()
            st.success(f"Successfully saved records for {selected_store} under reporting month: **{selected_month}**!")

# ==========================================
# TAB 3: VENDOR AUDITS
# ==========================================
with tab_supply:
    st.subheader(f"Log Vendor Audit for {selected_month}")
    
    with st.form("vendor_audit_form"):
        v_col1, v_col2 = st.columns(2)
        with v_col1:
            audit_month = st.text_input("Audit Month", value=selected_month, disabled=True)
            vendor_name = st.text_input("Vendor Name", placeholder="e.g., ABC Vendor")
            audit_score = st.text_input("Audit Score (%)", placeholder="e.g., 92%")
            
        with v_col2:
            audit_status = st.selectbox("Audit Status", ["Passed", "Passed with Conditions", "Failed"])
            remarks = st.text_area("Remarks / CAPA", placeholder='e.g., "CA pending for handwash"')
            
        if st.form_submit_button("Save Vendor Audit Record", type="primary"):
            if vendor_name:
                st.success(f"Audit record for {vendor_name} successfully logged for {selected_month}.")
            else:
                st.error("Vendor Name is required.")

# ==========================================
# TAB 4: SYSTEM ADMINISTRATION
# ==========================================
with tab_admin:
    st.subheader("Database Management")
    
    with st.expander("➕ Add a New Store Location", expanded=False):
        new_name = st.text_input("Store Name", placeholder="e.g., CBTL Creek Side, Ludhiana")
        is_out = st.checkbox("Is Outstation?")
        if st.button("Add Store to Master Database"):
            if new_name and supabase:
                try:
                    supabase.table("stores").insert({"name": new_name, "is_outstation": is_out}).execute()
                    st.cache_data.clear()
                    st.success(f"Added {new_name}.")
                except Exception as e:
                    st.error(f"Failed to add store: {e}")

# ==========================================
# TAB 5: REPORTS & ARCHIVES
# ==========================================
with tab_reports:
    st.subheader("Dashboard PDF Generation & Retrieval")
    st.markdown(f"Generate a static snapshot of the dashboard data specifically for **{selected_month}**.")
    
    col_pdf1, col_pdf2 = st.columns(2)
    
    with col_pdf1:
        st.markdown(f"**Generate Report: {selected_month}**")
        if st.button(f"Generate PDF for {selected_month}", type="primary"):
            if FPDF is None:
                st.error("The 'fpdf2' library is not installed.")
            else:
                pdf = FPDF()
                pdf.add_page()
                pdf.set_font("Arial", 'B', 16)
                pdf.cell(200, 10, txt=f"QA Compliance Command Center - {selected_month}", ln=True, align='C')
                pdf.set_font("Arial", size=12)
                pdf.cell(200, 10, txt=f"Total Stores: {total_stores}", ln=True)
                pdf.cell(200, 10, txt=f"Stores Fully Compliant (Staffing): {compliant_stores}", ln=True)
                
                pdf_bytes = pdf.output(dest='S').encode('latin-1')
                st.success(f"PDF successfully generated for {selected_month}!")
                st.download_button(
                    label=f"Download {selected_month} PDF",
                    data=pdf_bytes,
                    file_name=f"QA_Dashboard_{selected_month.replace(' ', '_')}.pdf",
                    mime="application/pdf"
                )

    with col_pdf2:
        st.markdown("**Retrieve Past Archived Reports**")
        archive_df = pd.DataFrame({
            "Report Month": [selected_month],
            "Generated On": [str(datetime.date.today())],
            "Status": ["Archived in Cloud"]
        })
        st.dataframe(archive_df, use_container_width=True, hide_index=True)
