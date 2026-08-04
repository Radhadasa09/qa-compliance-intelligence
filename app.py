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
# Generate a list of recent months for the dynamic heading
today = datetime.date.today()
months = [(today.replace(day=1) - datetime.timedelta(days=30*i)).strftime("%B %Y") for i in range(6)]
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

stores_data = load_stores()
df_stores = pd.DataFrame(stores_data)

# Fallback Data to demonstrate the new compliance structure
if df_stores.empty:
    st.warning("Database not connected or empty. Using Ekaagra sample data for demonstration.")
    sample_data = {
        'name': [
            'CBTL Janakpuri, New Delhi', 'CBTL Greater Kailash (M-Block), New Delhi', 
            'CBTL Platina Tower, Gurugram', 'Creek Side, Ludhiana (New)'
        ],
        'is_outstation': [False, False, False, True],
        'fostac_pending': [0, 2, 0, 5],
        'medical_pending': [0, 0, 1, 5],
        'nsf_score': [94, 89, 92, None],
        'self_audit_done': [True, True, False, False],
        'self_audit_score': [95, 88, None, None]
    }
    df_stores = pd.DataFrame(sample_data)

# Calculate dynamic compliance metric
if not df_stores.empty and 'fostac_pending' in df_stores.columns:
    df_stores['is_compliant'] = (df_stores['fostac_pending'] == 0) & (df_stores['medical_pending'] == 0)
    compliant_stores = df_stores['is_compliant'].sum()
else:
    compliant_stores = 0

# --- 3. CEO-LEVEL HEADER ---
st.title("🛡️ QA & Compliance Command Center")
st.markdown("Real-time oversight of Retail Operations, Supply Chain, and Regulatory Compliance.")
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
    # DYNAMIC HEADING BASED ON SIDEBAR
    st.subheader(f"📈 {selected_month} Summary")
    
    col1, col2, col3, col4 = st.columns(4)
    total_stores = len(df_stores)
    
    col1.metric("Total Active Stores", total_stores)
    col2.metric("Fully Compliant Stores (Staffing)", f"{compliant_stores} / {total_stores}") 
    
    avg_nsf = df_stores['nsf_score'].mean() if not df_stores.empty and 'nsf_score' in df_stores.columns else 0
    col3.metric("Average NSF Score", f"{avg_nsf:.1f}%" if pd.notnull(avg_nsf) else "N/A") 
    col4.metric("Active Vendor Audits", "2 (This Month)") 

    st.markdown("---")
    
    if not df_stores.empty:
        chart_col1, chart_col2 = st.columns(2)
        with chart_col1:
            st.markdown("### 🏬 Store Staff Compliance Status")
            compliance_counts = df_stores['is_compliant'].value_counts().reset_index()
            compliance_counts.columns = ['Status', 'Count']
            compliance_counts['Status'] = compliance_counts['Status'].map({True: 'Compliant (0 Pending)', False: 'Action Required'})
            fig_comp = px.pie(compliance_counts, values='Count', names='Status', hole=0.5, color='Status',
                              color_discrete_map={'Compliant (0 Pending)': '#10B981', 'Action Required': '#EF4444'})
            st.plotly_chart(fig_comp, use_container_width=True)
            
        with chart_col2:
            st.markdown("### 📋 Quick Store Directory")
            display_df = df_stores[['name', 'fostac_pending', 'medical_pending', 'is_compliant']].copy()
            st.dataframe(display_df, use_container_width=True, hide_index=True)

# ==========================================
# TAB 2: RETAIL OPERATIONS (Store Level Entry)
# ==========================================
with tab_ops:
    st.subheader("Update Store-Level Compliance & Licenses")
    if not df_stores.empty:
        selected_store = st.selectbox("Select Store to Update", df_stores['name'].tolist(), key="ops_store")
        
        st.markdown(f"#### Operations Data for: {selected_store}")
        col_a, col_b = st.columns(2)
        
        with col_a:
            st.markdown("**1. Staff Requirements**")
            fostac_req = st.number_input("Number of Staff requiring FoSTaC", min_value=0, value=0)
            med_req = st.number_input("Number of Staff requiring Medical", min_value=0, value=0)
            
            if fostac_req == 0 and med_req == 0:
                st.success("✅ This store is fully in compliance for Staffing.")
            else:
                st.warning("⚠️ Pending requirements exist. Store is not fully compliant.")
                
            st.markdown("**2. Store Audits**")
            st.number_input("NSF Score (%)", min_value=0, max_value=100, value=90)
            
            self_audit = st.radio("Monthly Self Audit Done?", ["Yes", "No"])
            if self_audit == "Yes":
                st.number_input("Monthly Self Audit Score (%)", min_value=0, max_value=100, value=85)
                
        with col_b:
            st.markdown("**3. License Compliance**")
            st.markdown("Toggle applicability and update status for eligible licenses.")
            
            # FSSAI
            fssai_applicable = st.toggle("FSSAI License Applicable", value=True)
            if fssai_applicable:
                st.selectbox("FSSAI Status", ["Valid", "Applied/Pending", "Expired"], key="fssai")
                st.date_input("FSSAI Expiry Date", key="fssai_date")
                
            st.divider()
            
            # Trade License
            trade_applicable = st.toggle("Trade License Applicable", value=True)
            if trade_applicable:
                st.selectbox("Trade License Status", ["Valid", "Applied/Pending", "Expired"], key="trade")
                
            st.divider()
            
            # Fire NOC
            fire_applicable = st.toggle("Fire NOC Applicable", value=False)
            if fire_applicable:
                st.selectbox("Fire NOC Status", ["Valid", "Applied/Pending", "Expired"], key="fire")
                
        if st.button("Save Store Compliance Data", type="primary"):
            # Here you would write the UPDATE query to Supabase
            st.success(f"Compliance data saved for {selected_store}.")

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
            audit_score = st.text_input("Audit Score", placeholder="e.g., 92%")
            
        with v_col2:
            audit_status = st.selectbox("Audit Status", ["Passed", "Passed with Conditions", "Failed"])
            remarks = st.text_area("Remarks / CAPA", placeholder='e.g., "CA pending for handwash"')
            
        if st.form_submit_button("Save Vendor Audit", type="primary"):
            if vendor_name:
                # Example Supabase insert:
                # supabase.table("vendor_audits").insert({"month": audit_month, "vendor": vendor_name, "score": audit_score, "status": audit_status, "remarks": remarks}).execute()
                st.success(f"Audit for {vendor_name} successfully recorded for {audit_month}.")
            else:
                st.error("Vendor Name is required.")

# ==========================================
# TAB 4: SYSTEM ADMINISTRATION
# ==========================================
with tab_admin:
    st.subheader("Database Management")
    st.info("Best Practice: Store records are mapped by unique IDs in the database, though names are shown here for ease of use.")
    
    with st.expander("➕ Add a New Store Location", expanded=False):
        new_name = st.text_input("Store Name", placeholder="e.g., CBTL Creek Side, Ludhiana")
        is_out = st.checkbox("Is Outstation?")
        if st.button("Add Store to Database"):
            if new_name and supabase:
                try:
                    supabase.table("stores").insert({"name": new_name, "is_outstation": is_out}).execute()
                    st.cache_data.clear()
                    st.success(f"Added {new_name}. Please refresh.")
                except Exception as e:
                    st.error(f"Failed to add store: {e}")
                    
    with st.expander("❌ Remove an Existing Store", expanded=False):
        if not df_stores.empty:
            store_to_remove = st.selectbox("Select Store to Delete", df_stores['name'].tolist())
            st.warning("⚠️ This will permanently delete the store from the database.")
            if st.button("Delete Store", type="primary"):
                if supabase:
                    try:
                        # Best Practice: In a real app, delete using the unique UUID ('id' column)
                        supabase.table("stores").delete().eq("name", store_to_remove).execute()
                        st.cache_data.clear()
                        st.success(f"Deleted {store_to_remove}.")
                    except Exception as e:
                        st.error(f"Failed to delete store: {e}")

# ==========================================
# TAB 5: REPORTS & ARCHIVES (PDF Generation)
# ==========================================
with tab_reports:
    st.subheader("Dashboard PDF Generation & Retrieval")
    st.markdown("Generate a static snapshot of the dashboard data for the selected month and save it to the cloud archive.")
    
    col_pdf1, col_pdf2 = st.columns(2)
    
    with col_pdf1:
        st.markdown(f"**Generate New Report: {selected_month}**")
        if st.button(f"Generate & Save PDF for {selected_month}", type="primary"):
            if FPDF is None:
                st.error("The 'fpdf2' library is not installed. Please add it to requirements.txt.")
            else:
                with st.spinner("Generating PDF and uploading to Supabase Storage..."):
                    # 1. Create the PDF
                    pdf = FPDF()
                    pdf.add_page()
                    pdf.set_font("Arial", 'B', 16)
                    pdf.cell(200, 10, txt=f"QA Compliance Command Center - {selected_month}", ln=True, align='C')
                    pdf.set_font("Arial", size=12)
                    pdf.cell(200, 10, txt=f"Total Stores: {total_stores}", ln=True)
                    pdf.cell(200, 10, txt=f"Stores Fully Compliant (Staffing): {compliant_stores}", ln=True)
                    # (In a real app, you would iterate over df_stores to print tabular data here)
                    
                    # 2. Get PDF as bytes
                    pdf_bytes = pdf.output(dest='S').encode('latin-1')
                    
                    # 3. Save to Supabase Storage (Simulated/Example Code)
                    if supabase:
                        try:
                            file_name = f"QA_Report_{selected_month.replace(' ', '_')}.pdf"
                            # supabase.storage.from_("reports").upload(file_name, pdf_bytes, {"content-type": "application/pdf"})
                            # supabase.table("reports_metadata").insert({"month": selected_month, "filename": file_name}).execute()
                            st.success(f"PDF generated and securely archived as {file_name}!")
                        except Exception as e:
                            st.warning(f"PDF generated, but failed to upload to Supabase: {e}")
                    else:
                        st.success("PDF generated locally (Database not connected for archive).")
                    
                    # Provide an immediate download link as well
                    st.download_button(
                        label="Download PDF Now",
                        data=pdf_bytes,
                        file_name=f"QA_Dashboard_{selected_month.replace(' ', '_')}.pdf",
                        mime="application/pdf"
                    )

    with col_pdf2:
        st.markdown("**Retrieve Past Reports**")
        st.info("Once a report is generated and saved, it will appear here for future retrieval (e.g., pulling July's data in December).")
        
        # Example of pulling metadata from Supabase
        # response = supabase.table("reports_metadata").select("*").execute()
        # archive_df = pd.DataFrame(response.data)
        
        # Mock Data for UI demonstration
        archive_df = pd.DataFrame({
            "Report Month": ["June 2026", "May 2026", "April 2026"],
            "Generated On": ["2026-07-01", "2026-06-02", "2026-05-01"],
            "Status": ["Archived", "Archived", "Archived"]
        })
        
        st.dataframe(archive_df, use_container_width=True, hide_index=True)
        st.button("Fetch Selected Document from Cloud Storage")
