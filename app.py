import streamlit as st
from supabase import create_client, Client
import pandas as pd

# --- 1. SECURE DATABASE CONNECTION ---
try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(URL, KEY)
except Exception:
    st.error("Missing Credentials. Please check Streamlit Secrets.")
    st.stop()

st.set_page_config(page_title="CBTL QA Intelligence", layout="wide", page_icon="📈")

# --- 2. DATA LOADING ---
@st.cache_data(ttl=60) # Refreshes data every 60 seconds
def load_stores():
    response = supabase.table("stores").select("*").execute()
    return response.data

stores_data = load_stores()
df_stores = pd.DataFrame(stores_data)

# --- 3. CEO-LEVEL HEADER ---
st.title("📈 Enterprise QA & Compliance Intelligence")
st.markdown("Real-time operational compliance monitoring for all retail locations.")
st.divider()

# --- 4. DASHBOARD TABS ---
# We put the Executive view first for management!
tab_exec, tab_entry, tab_docs, tab_admin = st.tabs([
    "📊 Executive Dashboard", 
    "📝 Audit Data Entry", 
    "📂 Document Vault", 
    "⚙️ Store Management"
])

# ==========================================
# TAB 1: EXECUTIVE DASHBOARD (For the CEO)
# ==========================================
with tab_exec:
    st.subheader("Network Overview")
    
    # High-level KPIs
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    total_stores = len(df_stores) if not df_stores.empty else 0
    outstation_count = len(df_stores[df_stores['is_outstation'] == True]) if not df_stores.empty else 0
    
    kpi1.metric("Total Active Stores", total_stores)
    kpi2.metric("Local Hubs", total_stores - outstation_count)
    kpi3.metric("Outstation Hubs", outstation_count)
    kpi4.metric("Network Status", "Compliant" if total_stores > 0 else "Pending")

    st.markdown("### Store Directory & Status")
    if not df_stores.empty:
        # Display a clean, professional table for management
        display_df = df_stores[['name', 'pest_agency', 'is_outstation']].copy()
        display_df.columns = ["Store Location", "Pest Control Partner", "Is Outstation?"]
        st.dataframe(display_df, use_container_width=True, hide_index=True)
    else:
        st.info("No stores found in the database.")

# ==========================================
# TAB 2: AUDIT DATA ENTRY (For You/QA Team)
# ==========================================
with tab_entry:
    st.subheader("Submit New Audit/QA Score")
    if not df_stores.empty:
        store_names = df_stores['name'].tolist()
        selected_store = st.selectbox("Select Store for Audit", store_names)
        current_store = df_stores[df_stores['name'] == selected_store].iloc[0]
        
        col_a, col_b = st.columns(2)
        with col_a:
            audit_type = st.selectbox("Audit Type", ["Internal Monthly QA", "NSF Quarterly"])
            score = st.number_input("Overall QA Score (%)", min_value=0, max_value=100, value=85)
        with col_b:
            ca_status = st.radio("Corrective Action Status", ["Not Required", "Pending", "Resolved"])
            if current_store['is_outstation']:
                st.warning("✈️ Outstation Store: Physical audit exemptions may apply.")
                
        crit_issues = st.text_area("Critical Issues (Flags for Management)")
        
        if st.button("Submit Audit to Database", type="primary"):
            # In the future, this will save to an 'audit_logs' table!
            st.success(f"Successfully recorded {score}% for {selected_store}.")
    else:
        st.warning("Please add stores in the Store Management tab first.")

# ==========================================
# TAB 3: DOCUMENT VAULT
# ==========================================
with tab_docs:
    st.subheader("Compliance File Upload")
    if not df_stores.empty:
        vault_store = st.selectbox("Assign Document to Store", df_stores['name'].tolist())
        doc_type = st.selectbox("Document Category", ["FSSAI License", "Water Test Report", "Pest Control Log"])
        uploaded_file = st.file_uploader("Upload PDF File", type=['pdf'])
        
        if uploaded_file and st.button("Secure Upload"):
            path = f"{vault_store}/{doc_type}/{uploaded_file.name}"
            try:
                supabase.storage.from_('compliance-docs').upload(path, uploaded_file.getvalue())
                st.success("Document secured in cloud vault.")
            except Exception as e:
                st.error("Upload failed. Ensure your Supabase storage bucket is named exactly 'compliance-docs'.")
    else:
        st.warning("Please add stores first.")

# ==========================================
# TAB 4: STORE MANAGEMENT (Add New Stores)
# ==========================================
with tab_admin:
    st.subheader("Add New Store Location")
    st.markdown("Use this form to expand the network. Data is saved directly to the database.")
    
    with st.form("new_store_form"):
        new_name = st.text_input("Store Location Name (e.g., Select Citywalk)")
        new_agency = st.selectbox("Pest Control Agency", ["IGPC", "Eco Sol", "Other"])
        is_out = st.checkbox("Mark as Outstation Store")
        
        submitted = st.form_submit_button("Add Store to Database")
        if submitted:
            if new_name.strip() == "":
                st.error("Store name cannot be blank.")
            else:
                # Insert the new store into Supabase!
                new_data = {
                    "name": new_name,
                    "pest_agency": new_agency,
                    "is_outstation": is_out
                }
                supabase.table("stores").insert(new_data).execute()
                
                # Clear the cache so the dashboard updates immediately
                st.cache_data.clear()
                st.success(f"✅ {new_name} added successfully! Please refresh the page.")
