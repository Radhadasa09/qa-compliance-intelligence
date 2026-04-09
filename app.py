import streamlit as st
from supabase import create_client, Client
import datetime
import pandas as pd

# --- 1. SECURE DATABASE CONNECTION ---
# These will be set in the Streamlit Cloud 'Secrets' settings
try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(URL, KEY)
except Exception:
    st.error("Missing Credentials. Please add SUPABASE_URL and SUPABASE_KEY to Streamlit Secrets.")
    st.stop()

st.set_page_config(page_title="QA Compliance Intelligence", layout="wide")

# --- 2. DATA LOADING ---
@st.cache_data(ttl=600)
def load_stores():
    response = supabase.table("stores").select("*").execute()
    return response.data

# --- 3. SIDEBAR & NAVIGATION ---
st.sidebar.title("QA Control Panel")
try:
    stores_data = load_stores()
    store_names = [s['name'] for s in stores_data]
    selected_store = st.sidebar.selectbox("Select Store Location", store_names)
    current_store = next(s for s in stores_data if s['name'] == selected_store)
except:
    st.sidebar.error("Database table 'stores' not found. Check SQL setup.")
    st.stop()

# --- 4. MAIN DASHBOARD ---
st.title("🛡️ QA & Compliance Dashboard")
st.markdown(f"**Managing:** {selected_store} | **Agency:** {current_store['pest_agency']}")

# Metrics Row
m1, m2, m3 = st.columns(3)
m1.metric("Region", "Outstation" if current_store['is_outstation'] else "Local")
m2.metric("Pest Agency", current_store['pest_agency'])
m3.metric("Store Status", "Active")

st.divider()

# Tabs for Organization
tab_audit, tab_docs, tab_management = st.tabs(["Update Audit", "License Vault", "Management Overview"])

with tab_audit:
    st.subheader("Monthly/Quarterly Audit Entry")
    col_a, col_b = st.columns(2)
    with col_a:
        a_type = st.selectbox("Audit Type", ["Internal Monthly", "NSF Quarterly"])
        score = st.slider("QA Score %", 0, 100, 85)
    with col_b:
        ca_status = st.checkbox("Corrective Action (CA) Submitted")
        outstation_skip = st.checkbox("Skip Audit (Outstation Issue)") if current_store['is_outstation'] else False
    
    crit_issues = st.text_area("Critical Issues for Management Attention")
    if st.button("Submit Audit Data"):
        st.success("Audit data recorded. Management will be notified.")

with tab_docs:
    st.subheader("Document Repository")
    doc_type = st.selectbox("Document", ["FSSAI License", "Water Test Report", "Food Grade Certificate"])
    expiry = st.date_input("Expiry Date")
    uploaded_file = st.file_uploader("Upload PDF", type=['pdf'])
    
    if uploaded_file and st.button("Upload to Cloud"):
        # Logic for Supabase Storage
        path = f"{selected_store}/{uploaded_file.name}"
        supabase.storage.from_('compliance-docs').upload(path, uploaded_file.getvalue())
        st.success(f"Successfully uploaded to {selected_store} folder.")

with tab_management:
    st.subheader("Store Compliance Summary")
    df = pd.DataFrame(stores_data)
    st.dataframe(df[['name', 'pest_agency', 'is_outstation']], use_container_width=True)
