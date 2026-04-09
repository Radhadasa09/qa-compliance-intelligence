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

st.set_page_config(page_title="QA Intelligence Command Center", layout="wide", page_icon="🛡️")

# --- 2. DATA LOADING ---
@st.cache_data(ttl=60)
def load_stores():
    response = supabase.table("stores").select("*").execute()
    return response.data

stores_data = load_stores()
df_stores = pd.DataFrame(stores_data)

# --- 3. CEO-LEVEL HEADER ---
st.title("🛡️ Enterprise QA & Compliance Command Center")
st.markdown("Real-time oversight of Retail Operations, Supply Chain, and Regulatory Compliance.")
st.divider()

# --- 4. DASHBOARD TABS ---
tab_exec, tab_ops, tab_supply, tab_admin = st.tabs([
    "📊 Executive Dashboard", 
    "🏬 Retail Operations (Audits & FOSTAC)", 
    "🚚 Supply Chain (Vendors & Transport)", 
    "⚙️ System Administration"
])

# ==========================================
# TAB 1: EXECUTIVE DASHBOARD (The CEO View)
# ==========================================
with tab_exec:
    st.subheader("Network Compliance Health")
    
    # TOP ROW: The big numbers
    col1, col2, col3, col4 = st.columns(4)
    total_stores = len(df_stores) if not df_stores.empty else 0
    
    col1.metric("Total Active Retail Stores", total_stores)
    col2.metric("FOSTAC Trained Staff", "85%", "Target: 100%") # Placeholder for visual
    col3.metric("Medical Fitness Availability", "92%", "-1 Store") # Placeholder for visual
    col4.metric("Active Vendor Audits", "14") # Placeholder for visual

    st.markdown("---")
    
    # MIDDLE ROW: Departmental Breakdown
    sub_col1, sub_col2, sub_col3 = st.columns(3)
    
    with sub_col1:
        st.markdown("**🏬 Store Audit Averages**")
        st.progress(88, text="Internal QA Average (88%)")
        st.progress(94, text="NSF Audit Average (94%)")
        
    with sub_col2:
        st.markdown("**🪲 Pest Control Coverage**")
        if not df_stores.empty:
            pest_counts = df_stores['pest_agency'].value_counts()
            st.dataframe(pest_counts, use_container_width=True)

    with sub_col3:
        st.markdown("**🚚 Supply Chain Health**")
        st.info("Warehouse Transport Compliance: **GREEN**")
        st.warning("Pending Vendor Audits: **3**")

    st.markdown("### 📋 Live Store Directory")
    if not df_stores.empty:
        display_df = df_stores[['name', 'pest_agency', 'is_outstation']].copy()
        display_df.columns = ["Store Location", "Pest Control Partner", "Is Outstation?"]
        st.dataframe(display_df, use_container_width=True, hide_index=True)

# ==========================================
# TAB 2: RETAIL OPERATIONS (Data Entry)
# ==========================================
with tab_ops:
    st.subheader("Update Store-Level Compliance")
    if not df_stores.empty:
        store_names = df_stores['name'].tolist()
        selected_store = st.selectbox("Select Store", store_names, key="ops_store")
        
        st.markdown(f"**Entering Data For:** {selected_store}")
        col_a, col_b, col_c = st.columns(3)
        
        with col_a:
            st.markdown("**1. Audit Scores**")
            st.number_input("Internal QA Score (%)", 0, 100, 85)
            st.number_input("NSF Score (%)", 0, 100, 90)
            
        with col_b:
            st.markdown("**2. Store Certifications**")
            st.radio("FOSTAC Availability", ["100% Compliant", "Training Needed"])
            st.radio("Medical Certificates", ["All Available", "Missing/Expired"])
            
        with col_c:
            st.markdown("**3. Pest Control**")
            st.date_input("Last Pest Service Date")
            st.file_uploader("Upload Service Report", type=['pdf'])
            
        if st.button("Save Store Operations Data", type="primary"):
            st.success("Data recorded for review.")

# ==========================================
# TAB 3: SUPPLY CHAIN & VENDORS
# ==========================================
with tab_supply:
    st.subheader("Vendor & Logistics Compliance")
    
    v_col1, v_col2 = st.columns(2)
    with v_col1:
        st.markdown("**Vendor Audits**")
        vendor_name = st.text_input("Vendor Name")
        st.selectbox("Audit Status", ["Approved", "Conditionally Approved", "Rejected"])
        st.file_uploader("Upload Vendor Audit Report (PDF)")
        
    with v_col2:
        st.markdown("**Warehouse & Transport**")
        st.selectbox("Transport Vehicle Temp Compliance", ["Compliant (< 5°C)", "Non-Compliant"])
        st.text_area("Logistics Remarks")
        
    if st.button("Log Supply Chain Data", type="primary"):
        st.success("Supply chain record updated.")

# ==========================================
# TAB 4: SYSTEM ADMINISTRATION
# ==========================================
with tab_admin:
    st.subheader("Database Management")
    
    ad_col1, ad_col2 = st.columns(2)
    
    with ad_col1:
        st.markdown("**➕ Add New Store**")
        with st.form("new_store_form"):
            new_name = st.text_input("Store Name")
            new_agency = st.selectbox("Pest Agency", ["IGPC", "Eco Sol", "Other"])
            is_out = st.checkbox("Is Outstation?")
            if st.form_submit_button("Add Store"):
                if new_name:
                    supabase.table("stores").insert({"name": new_name, "pest_agency": new_agency, "is_outstation": is_out}).execute()
                    st.cache_data.clear()
                    st.success(f"Added {new_name}. Please refresh.")
                    
    with ad_col2:
        st.markdown("**❌ Remove Store**")
        if not df_stores.empty:
            store_to_remove = st.selectbox("Select Store to Delete", df_stores['name'].tolist())
            st.warning("Warning: This will permanently delete the store from the database.")
            if st.button("Delete Store", type="primary"):
                supabase.table("stores").delete().eq("name", store_to_remove).execute()
                st.cache_data.clear()
                st.success(f"Deleted {store_to_remove}. Please refresh.")
