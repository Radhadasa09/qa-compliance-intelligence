import streamlit as st
from supabase import create_client, Client
import pandas as pd
import plotly.express as px

# --- 1. SECURE DATABASE CONNECTION ---
try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(URL, KEY)
except Exception:
    st.error("Missing Credentials. Please check Streamlit Secrets.")
    st.stop()

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="QA Intelligence Command Center", 
    layout="wide", 
    page_icon="🛡️",
    initial_sidebar_state="collapsed"
)

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
    "🏬 Retail Operations", 
    "🚚 Supply Chain", 
    "⚙️ System Administration"
])

# ==========================================
# TAB 1: EXECUTIVE DASHBOARD (The CEO View)
# ==========================================
with tab_exec:
    st.subheader("Network Compliance Health")
    
    # TOP ROW: Key Performance Indicators (KPIs)
    col1, col2, col3, col4 = st.columns(4)
    total_stores = len(df_stores) if not df_stores.empty else 0
    outstation_count = len(df_stores[df_stores['is_outstation'] == True]) if not df_stores.empty else 0
    
    col1.metric("Total Active Retail Stores", total_stores)
    col2.metric("FOSTAC Trained Staff", "85%", "Target: 100%") 
    col3.metric("Medical Fitness Availability", "92%", "-1 Store") 
    col4.metric("Active Vendor Audits", "14") 

    st.markdown("---")
    
    # MIDDLE ROW: Interactive Data Visualizations
    if not df_stores.empty:
        chart_col1, chart_col2, chart_col3 = st.columns([1.5, 1.5, 1])
        
        with chart_col1:
            # Interactive Donut Chart for Pest Control
            pest_counts = df_stores['pest_agency'].value_counts().reset_index()
            pest_counts.columns = ['Agency', 'Count']
            fig_pest = px.pie(
                pest_counts, values='Count', names='Agency', hole=0.6, 
                title="Pest Control Vendor Distribution",
                color_discrete_sequence=['#1E3A8A', '#3B82F6', '#93C5FD']
            )
            fig_pest.update_traces(textposition='inside', textinfo='percent+label')
            fig_pest.update_layout(showlegend=False, margin=dict(t=40, b=0, l=0, r=0))
            st.plotly_chart(fig_pest, use_container_width=True)

        with chart_col2:
            # Interactive Bar Chart for Region Types
            outstation_counts = df_stores['is_outstation'].value_counts().reset_index()
            outstation_counts['is_outstation'] = outstation_counts['is_outstation'].map({True: 'Outstation', False: 'Local Hub'})
            outstation_counts.columns = ['Region', 'Count']
            fig_region = px.bar(
                outstation_counts, x='Region', y='Count', text='Count',
                title="Retail Hub Distribution",
                color='Region', color_discrete_sequence=['#10B981', '#6366F1']
            )
            fig_region.update_traces(textposition='outside')
            fig_region.update_layout(showlegend=False, margin=dict(t=40, b=0, l=0, r=0))
            st.plotly_chart(fig_region, use_container_width=True)
            
        with chart_col3:
            # Quick Text Callouts
            st.markdown("**🏬 Store Audit Averages**")
            st.progress(88, text="Internal QA Average (88%)")
            st.progress(94, text="NSF Audit Average (94%)")
            st.write("")
            st.markdown("**🚚 Supply Chain Health**")
            st.info("Warehouse Transport: **GREEN**")
            st.warning("Pending Vendor Audits: **3**")

    st.divider()

    # BOTTOM ROW: Clean Data Table
    st.markdown("### 📋 Live Store Directory")
    if not df_stores.empty:
        display_df = df_stores[['name', 'pest_agency', 'is_outstation']].copy()
        display_df.columns = ["Store Location", "Pest Control Partner", "Is Outstation?"]
        st.dataframe(display_df, use_container_width=True, hide_index=True)
    else:
        st.info("No stores found in the database. Please add them in System Administration.")

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
    st.markdown("Use these tools to configure the core network. Changes reflect immediately across the dashboard.")
    
    # Using Expanders to hide the forms and make it look cleaner
    with st.expander("➕ Add a New Store Location", expanded=False):
        with st.form("new_store_form"):
            new_name = st.text_input("Store Name")
            new_agency = st.selectbox("Pest Agency", ["IGPC", "Eco Sol", "Other"])
            is_out = st.checkbox("Is Outstation?")
            if st.form_submit_button("Add Store to Database"):
                if new_name:
                    supabase.table("stores").insert({"name": new_name, "pest_agency": new_agency, "is_outstation": is_out}).execute()
                    st.cache_data.clear()
                    st.success(f"Added {new_name}. Please refresh the page.")
                    
    with st.expander("❌ Remove an Existing Store", expanded=False):
        if not df_stores.empty:
            store_to_remove = st.selectbox("Select Store to Delete", df_stores['name'].tolist())
            st.warning("⚠️ Warning: This will permanently delete the store from the database.")
            if st.button("Delete Store", type="primary"):
                supabase.table("stores").delete().eq("name", store_to_remove).execute()
                st.cache_data.clear()
                st.success(f"Deleted {store_to_remove}. Please refresh the page.")
