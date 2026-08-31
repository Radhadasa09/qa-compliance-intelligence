import streamlit as st
from supabase import create_client, Client
import pandas as pd
import plotly.express as px
import os
import datetime
import io
import copy
import cloudinary
import cloudinary.uploader

# --- CLOUDINARY CONFIGURATION & HELPER ---
try:
    cloudinary.config(
        cloud_name=st.secrets.get("CLOUDINARY_CLOUD_NAME", os.environ.get("CLOUDINARY_CLOUD_NAME")),
        api_key=st.secrets.get("CLOUDINARY_API_KEY", os.environ.get("CLOUDINARY_API_KEY")),
        api_secret=st.secrets.get("CLOUDINARY_API_SECRET", os.environ.get("CLOUDINARY_API_SECRET")),
        secure=True
    )
except Exception:
    pass

def upload_photo(file_buffer, folder_name, sub_folder):
    """Uploads file to Cloudinary and returns the secure URL"""
    try:
        res = cloudinary.uploader.upload(file_buffer, folder=f"cbtl/{folder_name}/{sub_folder}")
        return res.get("secure_url")
    except Exception as e:
        st.error(f"Upload failed: {e}")
        return None
try:
    from fpdf import FPDF
except ImportError:
    FPDF = None

st.set_page_config(
    page_title="QA Intelligence Command Center", 
    layout="wide", 
    page_icon="🛡️",
    initial_sidebar_state="expanded"
)
# --- HIDE STREAMLIT BRANDING & GITHUB LINK ---
hide_streamlit_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)
# --- HIDE STREAMLIT BRANDING & FIX TOP SPACING ---
hide_streamlit_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Reduces the awkward top gap left by the hidden header */
    .block-container {
        padding-top: 1.5rem; 
        padding-bottom: 2rem;
        max-width: 1200px;
    }
    </style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)
# --- CBTL CORPORATE UI THEME ---
st.markdown("""
    <style>
        /* Main background and font */
        .stApp {
            background-color: #F5F7FA;
            font-family: 'Arial', sans-serif;
        }
        
        /* Style the tabs to match the solid underline active state */
        .stTabs [data-baseweb="tab-list"] {
            gap: 15px;
            border-bottom: 2px solid #E2E8F0;
        }
        .stTabs [data-baseweb="tab"] {
            border: none;
            background-color: transparent;
            padding-bottom: 10px;
        }
        .stTabs [aria-selected="true"] {
            background-color: transparent;
            border-bottom: 3px solid #003366 !important; /* Dark blue underline */
            color: #003366;
            font-weight: 800;
        }
        
        /* Light Blue Informational Cards (matching the Checklist Info card) */
        div[data-testid="stExpander"] {
            background-color: #EAF2F8; /* Light blue */
            border-radius: 10px;
            border: 1px solid #D6EAF8;
        }
        div[data-testid="stExpander"] summary {
            background-color: #EAF2F8;
            border-radius: 10px;
        }
        
        /* Metric Cards / Score Badges */
        [data-testid="stMetric"] {
            background-color: #EAF2F8;
            border-radius: 8px;
            padding: 10px 15px;
            box-shadow: none;
            border: none;
        }
        
        /* Special Green Gradient for Scores (matching the "Score / Grade" blocks) */
        [data-testid="stMetric"]:has(label:contains("Score")), 
        [data-testid="stMetric"]:has(label:contains("Grade")) {
            background: linear-gradient(135deg, #E0F8E9 0%, #C8F0D6 100%);
            border-left: 4px solid #2ECC71;
        }
        
        /* Blue Status Badges */
        .status-badge {
            background-color: #63B3ED;
            color: white;
            padding: 4px 10px;
            border-radius: 5px;
            font-weight: bold;
            font-size: 0.9em;
        }
    </style>
""", unsafe_allow_html=True)
# --- 1. SECURE DATABASE CONNECTION ---
try:
    URL = st.secrets.get("SUPABASE_URL", os.environ.get("SUPABASE_URL"))
    KEY = st.secrets.get("SUPABASE_KEY", os.environ.get("SUPABASE_KEY"))
    
    if not URL or not KEY:
        raise ValueError("Missing Supabase credentials")
        
    supabase: Client = create_client(URL, KEY)
except Exception as e:
    supabase = None

# Fetch daily operational shift checklists submitted by stores
@st.cache_data(ttl=30)
def load_daily_audits():
    if supabase is None:
        return pd.DataFrame()
    try:
        response = supabase.table("daily_audits").select("*").order("id", desc=True).execute()
        return pd.DataFrame(response.data)
    except Exception:
        return pd.DataFrame()

df_daily_live = load_daily_audits()

# --- 2. DATA FETCHING (From Cloud) ---
@st.cache_data(ttl=60)
def load_nsf_audits():
    if supabase is None:
        return pd.DataFrame()
    try:
        response = supabase.table("nsf_audits").select("*").execute()
        return pd.DataFrame(response.data)
    except Exception:
        return pd.DataFrame()

df_db = load_nsf_audits()

@st.cache_data(ttl=60)
def load_vendor_audits():
    if supabase is None:
        return pd.DataFrame()
    try:
        response = supabase.table("vendor_audits").select("*").execute()
        return pd.DataFrame(response.data)
    except Exception:
        return pd.DataFrame()

df_vendors_live = load_vendor_audits()

# Process dynamic categorizations for Ekaagra Direct (189 series) vs Sub Franchise
if not df_db.empty and 'site_code' in df_db.columns:
    df_db['site_code'] = df_db['site_code'].astype(str)
    df_db['Type'] = df_db['site_code'].apply(lambda x: "Ekaagra Direct" if x.startswith("189") else "Sub Franchise")
    ekaagra_df = df_db[df_db['Type'] == "Ekaagra Direct"]
    subfranchise_df = df_db[df_db['Type'] == "Sub Franchise"]
else:
    ekaagra_df = pd.DataFrame()
    subfranchise_df = pd.DataFrame()

selected_month = "Live Data"

# --- 4. DATA LOADING (Local Session State for non-Supabase data) ---
if 'master_stores' not in st.session_state:
    st.session_state['master_stores'] = [
        {'name': 'Janakpuri, Delhi', 'is_outstation': False},
        {'name': 'GK1, Delhi', 'is_outstation': False},
        {'name': 'Oberoi SkyCity, Mumbai', 'is_outstation': True},
        {'name': 'M3M Atrium, Gurgoan', 'is_outstation': True},
        {'name': 'Secor 50 Noida, Noida', 'is_outstation': False},
        {'name': 'Malcha, Delhi', 'is_outstation': False},
        {'name': 'Platina, Gurgoan', 'is_outstation': True},
        {'name': 'Season Mall Pune, Pune', 'is_outstation': True},
        {'name': 'BRS Nagar Ludhiana, Ludhiana', 'is_outstation': True},
        {'name': 'DLF Moti Nagar, Delhi', 'is_outstation': False},
        {'name': 'Goldust Patiala, Patiala', 'is_outstation': True},
        {'name': 'Warehouse, Delhi', 'is_outstation': False},
        {'name': 'Creek Side, Ludhiana', 'is_outstation': True},
        {'name': 'Chembur, Mumbai', 'is_outstation': True}
    ]
df_stores = pd.DataFrame(st.session_state['master_stores'])

if 'monthly_db' not in st.session_state:
    st.session_state['monthly_db'] = {}

if 'vendor_db' not in st.session_state:
    st.session_state['vendor_db'] = {
        "July 2026": [
            {"vendor": "ABC Pest Control", "category": "Pest Control", "score": "95%", "status": "Passed", "remark": "All guidelines met"},
            {"vendor": "FreshFoods Logistics", "category": "Supply Chain", "score": "88%", "status": "Conditionally Approved", "remark": "CA pending for handwash procedures"}
        ]
    }


if 'pdf_archive' not in st.session_state:
    st.session_state['pdf_archive'] = {}

def get_store_monthly(store_name, month):
    key = (store_name, month)
    if key in st.session_state['monthly_db']:
        return copy.deepcopy(st.session_state['monthly_db'][key])
    else:
        return {
            "fostac_pending": 0, "medical_pending": 0, "nsf_score": 0,
            "self_audit_done": "No", "self_audit_score": 0, "remark": "",
            "licenses": {
                "FSSAI": {"applicable": True, "status": "Valid", "expiry": datetime.date(2027, 12, 31)},
                "Trade License": {"applicable": True, "status": "Valid", "expiry": datetime.date(2027, 6, 30)},
                "Fire NOC": {"applicable": False, "status": "N/A", "expiry": datetime.date(2027, 1, 1)},
                "Pollution CTO": {"applicable": False, "status": "N/A", "expiry": datetime.date(2027, 1, 1)},
                "Signage License": {"applicable": False, "status": "N/A", "expiry": datetime.date(2027, 1, 1)}
            }
        }

monthly_records = []
for idx, row in df_stores.iterrows():
    s_name = row['name']
    m_data = get_store_monthly(s_name, selected_month)
    is_comp = (m_data['fostac_pending'] == 0) and (m_data['medical_pending'] == 0)
    lics = m_data['licenses']
    any_lic_issue = any(l_val['applicable'] and l_val['status'] != 'Valid' for l_val in lics.values())
    
    monthly_records.append({
        'name': s_name, 'is_outstation': row['is_outstation'], 'month': selected_month,
        'fostac_pending': m_data['fostac_pending'], 'medical_pending': m_data['medical_pending'],
        'is_compliant': is_comp, 'nsf_score': m_data['nsf_score'], 'self_audit_done': m_data['self_audit_done'],
        'self_audit_score': m_data['self_audit_score'], 'remark': m_data['remark'],
        'has_license_issue': any_lic_issue, 'licenses': lics
    })

df_monthly_filtered = pd.DataFrame(monthly_records)

# --- CEO-LEVEL HEADER ---
st.title("🛡️ QA & Compliance Leadership Briefing — Live Status")
st.markdown("**Command Center Admin:** Girish Kumar")
st.markdown("Real-time oversight of Ekaagra Master Franchise Operations, Licensing, Supply Chain, and Sub Franchise compliance.")
st.divider()

# Add "📚 Resources Vault" to your main executive tabs list:
tab_exec, tab_ops, tab_supply, tab_lic_summary, tab_nsf, tab_reports, tab_res, tab_admin = st.tabs([
    "📊 Executive Dashboard",
    "🏬 Retail Operations",
    "🚚 Vendor & Supply Chain",
    "📜 License Summary",
    "📈 NSF Audit Intelligence",
    "📑 Reports & Archive",
    "📚 Resources Vault",
    "⚙️ System Administration"
])

# ==========================================
# TAB 1: EXECUTIVE DASHBOARD
# ==========================================
with tab_exec:
    st.subheader(f"📈 Cloud Database Summary ({selected_month})")
    
    col1, col2, col3, col4 = st.columns(4)
    total_db_audits = len(df_db) if not df_db.empty else 0
    ekaagra_avg = ekaagra_df['score'].mean() if not ekaagra_df.empty and 'score' in ekaagra_df else 0
    sub_avg = subfranchise_df['score'].mean() if not subfranchise_df.empty and 'score' in subfranchise_df else 0
    
    col1.metric("Total Network Audits (Cloud)", total_db_audits)
    col2.metric("Ekaagra Direct Avg Score", f"{ekaagra_avg:.1f}%" if ekaagra_avg > 0 else "N/A")
    col3.metric("Sub Franchise Avg Score", f"{sub_avg:.1f}%" if sub_avg > 0 else "N/A")
    
    stores_with_lic_issues = int(df_monthly_filtered['has_license_issue'].sum()) if not df_monthly_filtered.empty else 0
    col4.metric("Stores with License Flags", f"{stores_with_lic_issues}", delta=f"{stores_with_lic_issues} Flags", delta_color="inverse")

    st.markdown("---")

    if not ekaagra_df.empty and 'score' in ekaagra_df.columns and 'store_name' in ekaagra_df.columns:
        st.markdown("### 🏬 Ekaagra Direct Operations (189 Series)")
        fig_nsf = px.bar(
            ekaagra_df, x='store_name', y='score', text='score',
            title=f"Ekaagra Direct Outlets NSF Scores",
            color='result' if 'result' in ekaagra_df.columns else 'score', 
            color_discrete_map={'PASS': '#10B981', 'FAIL': '#EF4444'}
        )
        fig_nsf.update_traces(textposition='outside')
        fig_nsf.update_layout(xaxis_tickangle=-35, showlegend=True, margin=dict(t=40, b=40, l=0, r=0))
        st.plotly_chart(fig_nsf, use_container_width=True)
    else:
        st.info("No Ekaagra Direct NSF data available in the cloud database yet.")

    st.markdown("### 👥 Store-by-Store Staff Compliance Status")
    
    try:
        if supabase is not None:
            # Fetch the live compliance data from Supabase
            comp_response = supabase.table("store_monthly_compliance").select("*").execute()
            
            if comp_response.data:
                df_comp = pd.DataFrame(comp_response.data)
                
                # Sort to show the most recently added records at the top
                df_comp = df_comp.sort_values(by='id', ascending=False)
                
                # High-end data grid with formatted columns
                st.dataframe(
                    df_comp[['store_name', 'month_year', 'fostac_pending', 'medical_pending', 'fully_compliant', 'self_audit_done', 'self_audit_score', 'remark']],
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "store_name": st.column_config.TextColumn("Store Name", width="medium"),
                        "month_year": st.column_config.TextColumn("Audit Month"),
                        "fostac_pending": st.column_config.NumberColumn("FoSTaC Pending", format="%d ⚠️"),
                        "medical_pending": st.column_config.NumberColumn("Medical Pending", format="%d ⚠️"),
                        "fully_compliant": st.column_config.CheckboxColumn("Fully Compliant?", default=False),
                        "self_audit_done": st.column_config.TextColumn("Self Audit Done?"),
                        "self_audit_score": st.column_config.NumberColumn("Self Audit Score (%)"),
                        "remark": st.column_config.TextColumn("Remarks")
                    }
                )
            else:
                st.info("📂 No compliance data found. Store Managers need to submit data in the Retail Operations tab.")
    except Exception as e:
        st.error(f"❌ Could not load compliance data from the cloud: {e}")

# ==========================================
# TAB 2: RETAIL OPERATIONS 
# ==========================================
with tab_ops:
    st.header("🏪 Retail Operations & Logistics")
    
  # ==========================================
    # --- 🏆 QA EXCELLENCE LEADERBOARD ---
    # ==========================================
    st.markdown("---")
    try:
        if supabase is not None:
            # Fetch audits WITH timestamps, ordered newest first
            leader_res = supabase.table("daily_audits").select("store_id, created_at").order("created_at", desc=True).execute()
            
            if leader_res.data:
                df_leader = pd.DataFrame(leader_res.data)
                df_leader['created_at'] = pd.to_datetime(df_leader['created_at'])
                df_leader['date_only'] = df_leader['created_at'].dt.date
                
                # Keep latest submission per store per day
                df_unique_days = df_leader.drop_duplicates(subset=['store_id', 'date_only'], keep='first')
                
                submission_counts = df_unique_days['store_id'].value_counts()
                
                if not submission_counts.empty:
                    max_score = submission_counts.max()
                    
                    # Find ALL store IDs that share the top score (handles ties perfectly!)
                    top_store_ids = submission_counts[submission_counts == max_score].index.tolist()
                    
                    champion_names = []
                    for s_id in top_store_ids:
                        store_info = supabase.table("stores").select("store_name").eq("store_id", s_id).execute()
                        if store_info.data:
                            champion_names.append(store_info.data[0]['store_name'])
                        else:
                            champion_names.append(f"Store {s_id}")
                    
                    # Format names nicely for the banner (e.g., "Store A & Store B")
                    champions_display = " &amp; ".join(champion_names)
                    
                    st.markdown(
                        f"""
                        <div style="background: linear-gradient(135deg, #FFD700 0%, #DAA520 100%); padding: 20px; border-radius: 12px; text-align: center; border: 2px solid #B8860B; box-shadow: 0 4px 15px rgba(218, 165, 32, 0.4); margin-bottom: 25px;">
                            <h2 style="color: #1A110A; margin: 0; font-weight: 800;">🏆 QA Shield of Excellence</h2>
                            <h4 style="color: #1A110A; margin: 5px 0 0 0;">Current Monthly Champions: <b>{champions_display}</b></h4>
                            <p style="color: #1A110A; margin: 5px 0 0 0; font-size: 14px;">Total Compliant Days: <b>{max_score}</b></p>
                        </div>
                        """, 
                        unsafe_allow_html=True
                    )
    except Exception as e:
        st.caption("Leaderboard calculating...")
    # ==========================================
    # --- 📊 LIVE ANALYTICS & DATA FEED ---
    # ==========================================
    st.subheader("📡 Live Store Analytics Feed")
    
    view_audit, view_recv, view_waste = st.tabs(["📋 Daily Audits", "📦 Receiving", "🗑️ Wastage"])
    
# --- 1. DAILY AUDITS GRAPH & DATA ---
    with view_audit:
        try:
            if supabase is not None:
                # I increased the limit to 200 so it captures more history before filtering
                audit_res = supabase.table("daily_audits").select("*").order("created_at", desc=True).limit(200).execute()
                if audit_res.data:
                    df_audits = pd.DataFrame(audit_res.data)
                    df_audits['created_at'] = pd.to_datetime(df_audits['created_at'])
                    
                    # 1. Filter for the LATEST submission per day per store
                    df_audits['date_only'] = df_audits['created_at'].dt.date
                    df_latest_audits = df_audits.drop_duplicates(subset=['store_id', 'date_only'], keep='first').copy()
                    
                    # 2. Map raw IDs to actual Store Names based on your master list
                    store_name_map = {
                        "189001": "Janakpuri, Delhi",
                        "189002": "GK1, Delhi",
                        "189003": "Oberoi SkyCity, Mumbai",
                        "189004": "M3M Atrium, Gurgaon",
                        "189005": "Secor 50 Noida, Noida",
                        "189006": "Malcha, Delhi",
                        "189007": "Platina, Gurgaon",
                        "189008": "Season Mall Pune, Pune",
                        "189009": "BRS Nagar Ludhiana, Ludhiana",
                        "189010": "DLF Moti Nagar, Delhi",
                        "189011": "Goldust Patiala, Patiala",
                        "189012": "Warehouse, Delhi",
                        "189013": "Creek Side, Ludhiana",
                        "189014": "Chembur, Mumbai"
                    }
                    
                    df_latest_audits['store_id_str'] = df_latest_audits['store_id'].astype(str)
                    df_latest_audits['Store Name'] = df_latest_audits['store_id_str'].map(store_name_map).fillna(df_latest_audits['store_id_str'])
                    
                    # 3. Graph: Group by the new 'Store Name' column using only latest daily data
                    audit_counts = df_latest_audits['Store Name'].value_counts().reset_index()
                    audit_counts.columns = ['Store Name', 'Total Valid Submissions']
                    
                    fig_audit = px.bar(
                        audit_counts, x='Store Name', y='Total Valid Submissions', 
                        title="Valid Daily Audits by Store", text_auto=True, 
                        color='Total Valid Submissions', color_continuous_scale='Blues'
                    )
                    fig_audit.update_layout(xaxis_type='category') 
                    st.plotly_chart(fig_audit, use_container_width=True)
                    
                    # Detailed Data Expander
                    with st.expander("🔍 View & Download Detailed Audit Reports"):
                        df_display = df_latest_audits.copy()
                        df_display['created_at'] = df_display['created_at'].dt.strftime('%Y-%m-%d %H:%M')
                        
                        cols_to_show = [
                            'created_at', 'Store Name', 'manager_name', 'shift', 
                            'admin_proof_url', 'hygiene_proof_url', 'sanitation_proof_url', 
                            'product_proof_url', 'facility_proof_url'
                        ]
                        
                        valid_cols = [c for c in cols_to_show if c in df_display.columns]
                        
                        st.dataframe(
                            df_display[valid_cols], 
                            column_config={
                                "admin_proof_url": st.column_config.LinkColumn("Admin Photo", display_text="🔗 View"),
                                "hygiene_proof_url": st.column_config.LinkColumn("Hygiene Photo", display_text="🔗 View"),
                                "sanitation_proof_url": st.column_config.LinkColumn("Sanitizer Photo", display_text="🔗 View"),
                                "product_proof_url": st.column_config.LinkColumn("Product Photo", display_text="🔗 View"),
                                "facility_proof_url": st.column_config.LinkColumn("Facility Photo", display_text="🔗 View")
                            },
                            use_container_width=True, 
                            hide_index=True
                        )
                        
                        st.download_button("📥 Download Raw Audit CSV", data=df_display.to_csv(index=False).encode('utf-8'), file_name="audits.csv", mime="text/csv")
                else:
                    st.info("No audit data available for graphs.")
        except Exception as e:
            st.error(f"Error loading audits: {e}")    # --- 2. RECEIVING LOGS GRAPH & DATA ---
    with view_recv:
        try:
            if supabase is not None:
                recv_res = supabase.table("store_receiving_logs").select("*").order("created_at", desc=True).limit(100).execute()
                if recv_res.data:
                    df_recv = pd.DataFrame(recv_res.data)
                    
                    # Graph: Receiving Temps
                    fig_recv = px.scatter(df_recv, x='created_at', y='received_temp', color='store_id', title="Vendor Delivery Temperatures (°C)", size_max=10, hover_data=['vendor_name', 'invoice_number'])
                    # Add a red line for max acceptable temp (e.g., 5°C)
                    fig_recv.add_hline(y=5.0, line_dash="dot", annotation_text="Max Acceptable Temp (5°C)", annotation_position="bottom right", line_color="red")
                    st.plotly_chart(fig_recv, use_container_width=True)
                    
                    # Detailed Data Expander
                    with st.expander("🔍 View Detailed Receiving Logs"):
                        st.dataframe(df_recv[['created_at', 'store_id', 'vendor_name', 'invoice_number', 'received_temp']], use_container_width=True, hide_index=True)
                else:
                    st.info("No receiving data available for graphs.")
        except Exception as e:
            st.error(f"Error loading receiving logs: {e}")

    # --- 3. WASTAGE GRAPH & DATA ---
    with view_waste:
        try:
            if supabase is not None:
                waste_res = supabase.table("store_wastage").select("*").order("created_at", desc=True).limit(100).execute()
                if waste_res.data:
                    df_waste = pd.DataFrame(waste_res.data)
                    
                    # Graph: Wastage by Reason
                    waste_counts = df_waste['reason'].value_counts().reset_index()
                    waste_counts.columns = ['Reason', 'Count']
                    fig_waste = px.pie(waste_counts, names='Reason', values='Count', title="Wastage Breakdown by Reason", hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
                    st.plotly_chart(fig_waste, use_container_width=True)
                    
                    # Detailed Data Expander
                    with st.expander("🔍 View Detailed Wastage Records"):
                        st.dataframe(df_waste[['created_at', 'store_id', 'item_name', 'quantity', 'reason']], use_container_width=True, hide_index=True)
                else:
                    st.info("No wastage data available for graphs.")
        except Exception as e:
            st.error(f"Error loading wastage logs: {e}")
            
    st.markdown("---")

    # ==========================================
    # --- ORIGINAL COMPLIANCE ENTRY ---
    # ==========================================
    st.subheader("📋 Store Staff Compliance Entry")
    
    FULL_STORE_LIST = [
        "DLF Mid Town Plaza, Moti Nagar", 
        "Janakpuri, Delhi", 
        "GK1, Delhi",
        "Oberoi SkyCity, Mumbai",
        "M3M Atrium, Gurgaon",
        "Sector 50 Noida, Noida",
        "Malcha, Delhi",
        "Platina, Gurgaon",
        "Season Mall Pune, Pune",
        "BRS Nagar Ludhiana, Ludhiana"
    ]
    
    with st.expander("📝 Enter New Compliance Record", expanded=False):
        with st.form("compliance_entry_form"):
            selected_store = st.selectbox("Select Store Location", FULL_STORE_LIST)
            current_month = st.selectbox("Select Audit Month", ["August 2026", "September 2026", "October 2026", "November 2026"])
            
            st.markdown("---")
            
            col1, col2 = st.columns(2)
            with col1:
                input_fostac = st.number_input("FoSTaC Pending (Count)", min_value=0, step=1)
                self_audit_done = st.selectbox("Self Audit Completed?", ["Yes", "No"])
            with col2:
                input_medical = st.number_input("Medical Pending (Count)", min_value=0, step=1)
                self_audit_score = st.number_input("Self Audit Score (%)", min_value=0.0, max_value=100.0, step=0.1, help="Leave at 0 if no audit was done.")
                
            is_compliant = st.checkbox("✅ Mark as Fully Compliant (No pending FoSTaC/Medical)")
            remark = st.text_area("Additional Remarks / Action Plan")

            if st.form_submit_button("🚀 Save Store Compliance Data", type="primary"):
                with st.spinner("Saving to cloud database..."):
                    try:
                        compliance_data = {
                            "store_name": selected_store,
                            "fostac_pending": input_fostac,
                            "medical_pending": input_medical,
                            "fully_compliant": is_compliant,
                            "self_audit_done": self_audit_done,
                            "self_audit_score": self_audit_score,
                            "remark": remark,
                            "month_year": current_month
                        }
                        
                        if supabase is not None:
                            supabase.table("store_monthly_compliance").insert(compliance_data).execute()
                            st.success(f"✅ Compliance data for {selected_store} successfully saved to the cloud!")
                        else:
                            st.error("Database connection is not active.")
                            
                    except Exception as e:
                        st.error(f"❌ Failed to save data: {e}")

    st.markdown("---")
    
    # ==========================================
    # --- LOGISTICS & FDU MONITORING ---
    # ==========================================
    st.subheader("🔄 Real-Time Logistics & FDU Compliance")
    
    col3, col4 = st.columns(2)
    
    with col3:
        st.markdown("### Inter-Store Dispatches")
        try:
            if supabase is not None:
                transfers_res = supabase.table("store_transfers").select("*").order("created_at", desc=True).limit(50).execute()
                if transfers_res.data:
                    df_transfers = pd.DataFrame(transfers_res.data)
                    df_transfers['created_at'] = pd.to_datetime(df_transfers['created_at']).dt.strftime('%Y-%m-%d %H:%M')
                    st.dataframe(df_transfers[['created_at', 'store_id', 'destination', 'dispatch_temp', 'items']], use_container_width=True, hide_index=True)
                else:
                    st.info("No inter-store dispatches logged.")
        except Exception as e:
            st.error(f"Error loading dispatch data: {e}")
            
    with col4:
        st.markdown("### FDU Thaw Compliance (MRD Matrix)")
        try:
            if supabase is not None:
                fdu_res = supabase.table("store_fdu_transfers").select("*").order("created_at", desc=True).limit(50).execute()
                if fdu_res.data:
                    df_fdu = pd.DataFrame(fdu_res.data)
                    st.dataframe(df_fdu[['store_id', 'store_name', 'quantity', 'thaw_start_time', 'discard_time']], use_container_width=True, hide_index=True)
                else:
                    st.info("No FDU transfers logged.")
        except Exception as e:
            st.error(f"Error loading FDU compliance data: {e}")

# ==========================================
# TAB 3: VENDOR & SUPPLY CHAIN (Nested Sub-Tabs)
# ==========================================
with tab_supply:
    st.subheader(f"Vendor Audit Management — {selected_month}")
    
    # Nested Sub-Tabs to keep the interface organized
    sub_tab_view, sub_tab_create = st.tabs(["📋 Recorded Audits", "📝 New Manufacturing Audit Checklist"])
    
    # ------------------------------------------
    # SUB-TAB 1: RECORDED AUDITS
    # ------------------------------------------
    with sub_tab_view:
        if not df_vendors_live.empty and 'audit_month' in df_vendors_live.columns:
            month_vendors = df_vendors_live[df_vendors_live['audit_month'] == selected_month]
            if not month_vendors.empty:
                st.markdown("### 📋 Recorded Vendor Audits for this Period")
                for _, row in month_vendors.iterrows():
                    with st.expander(f"🏢 {row['vendor_name']} — Status: {row.get('status', 'N/A')} (Score: {row.get('score', 'N/A')})"):
                        st.write(f"**Category:** {row.get('category', 'N/A')}")
                        st.write(f"**Remark:** {row.get('remark', 'None')}")
                        
                        proof = row.get('proof_url')
                        if proof and isinstance(proof, str):
                            urls = [u.strip() for u in proof.split(",")]
                            for idx, u in enumerate(urls):
                                if "http" in u:
                                    st.markdown(f"🔗 [Open Photo Proof {idx+1}]({u})", unsafe_allow_html=True)
                        
                        st.markdown("---")
                        if st.button(f"🗑️ Delete Audit Record ({row['vendor_name']})", key=f"del_audit_{row.get('id', _)}"):
                            try:
                                if supabase is not None:
                                    supabase.table("vendor_audits").delete().eq("id", row['id']).execute()
                                st.success("✅ Audit record deleted successfully!")
                                st.cache_data.clear()
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ Failed to delete record: {e}")
            else:
                st.info(f"No vendor audits recorded for {selected_month} yet.")
        else:
            st.info("No vendor audit records found in the database.")

    # ------------------------------------------
    # SUB-TAB 2: NEW AUDIT CHECKLIST FORM
    # ------------------------------------------
    with sub_tab_create:
        st.markdown("### 📝 General Manufacturing Vendor Audit Tool")
        st.caption("Evaluate vendors across the 40-point checklist. Point deduction comment boxes appear automatically when compliance is compromised.")
        
        with st.form("manufacturing_audit_form"):
            col_v1, col_v2 = st.columns(2)
            with col_v1:
                audit_vendor_name = st.text_input("Vendor / FBO Name")
                audit_fso = st.text_input("Food Safety Officer / Auditor Name")
                audit_date = st.date_input("Actual Audit Date", value=datetime.date.today())
            with col_v2:
                audit_lic_no = st.text_input("FBO License No.")
                audit_address = st.text_input("Facility Address")
                
            st.markdown("---")
            
            audit_responses = {}
            
            def render_checklist_section(section_title, questions_list):
                st.markdown(f"#### {section_title}")
                section_data = {}
                for q_text, points, is_star in questions_list:
                    label = f"⭐ {q_text} ({points} pts)" if is_star else f"{q_text} ({points} pts)"
                    
                    c1, c2 = st.columns([2, 1])
                    with c1:
                        status = st.selectbox(label, ["Compliance (C)", "Noncompliance (NC)", "Partial Compliance (PC)", "Not Applicable (NA)"], key=f"status_{q_text}")
                    
                    with c2:
                        # ALWAYS render the text input so it's available inside the st.form
                        comment = st.text_input("Deduction Note (If NC/PC)", key=f"comm_{q_text}", placeholder="Brief reason...")
                    
                    section_data[q_text] = {"status": status, "points": points, "is_star": is_star, "comment": comment}
                return section_data

            # Section 1
            design_questions = [
                ("Q1: Updated FSSAI license displayed prominently", 2, True),
                ("Q2: Adequate working space & clean premises design", 2, False),
                ("Q3: Internal structures made of non-toxic, impermeable material", 2, False),
                ("Q4: Walls, ceilings & doors free from flaking paint or plaster", 2, False),
                ("Q5: Floors non-slippery & sloped appropriately", 2, False),
                ("Q6: Windows fitted with insect-proof screens", 2, False),
                ("Q7: Doors close-fitted to avoid pest entry", 2, False),
                ("Q8: Equipment made of non-toxic, impervious material", 2, False),
                ("Q9: Sufficient lighting provided", 2, False),
                ("Q10: Adequate ventilation provided", 2, False),
                ("Q11: Adequate storage facility for food, chemicals, packaging", 2, False),
                ("Q12: Personnel hygiene facilities available", 2, False)
            ]
            q_design = render_checklist_section("1. Design & Facilities (Q1 - Q12)", design_questions)

            # Section 2
            ops_questions = [
                ("Q13: Potable water (IS:10500) tested semi-annually with records", 4, True),
                ("Q14: Food material tested internally or via accredited lab", 2, False),
                ("Q15: Incoming material procured from approved vendors with records", 2, False),
                ("Q16: Raw materials inspected at receiving for safety hazards", 2, False),
                ("Q17: Proper storage temperature/humidity, FIFO & FEFO practiced", 4, True),
                ("Q18: Manufacturing time/temperature maintained and recorded", 4, True),
                ("Q19: Food packed in a hygienic manner", 2, False),
                ("Q20: Packaging materials food-grade & in sound condition", 2, False),
                ("Q21: Cleaning chemicals clearly identified & stored separately", 2, False),
                ("Q22: Transporting vehicles kept clean and maintained", 2, False),
                ("Q23: Transporting vehicles capable of requisite temperature", 2, False),
                ("Q24: Recalled products handled safely with records", 2, False)
            ]
            q_ops = render_checklist_section("2. Control of Operation (Q13 - Q24)", ops_questions)

            # Section 3
            maint_questions = [
                ("Q25: Cleaning done as per schedule & program", 2, False),
                ("Q26: Preventive maintenance of equipment carried out regularly", 2, False),
                ("Q27: Measuring & monitoring devices calibrated periodically", 2, False),
                ("Q28: Pest control program carried out by trained personnel with records", 4, True),
                ("Q29: No signs of pest activity or infestation", 2, False),
                ("Q30: Drains equipped with traps to capture contaminants", 2, False),
                ("Q31: Food waste removed periodically", 2, False),
                ("Q32: Sewage/effluent disposal conforms to Environment Protection Act", 2, False)
            ]
            q_maint = render_checklist_section("3. Maintenance & Sanitation (Q25 - Q32)", maint_questions)

            # Section 4
            hyg_questions = [
                ("Q33: Annual medical examination & inoculation of food handlers", 2, False),
                ("Q34: No person with illness, open wounds handling food", 2, False),
                ("Q35: Food handlers maintain personal cleanliness & behavior", 4, True),
                ("Q36: Food handlers equipped with aprons, gloves, headgear", 2, False)
            ]
            q_hyg = render_checklist_section("4. Personal Hygiene (Q33 - Q36)", hyg_questions)

            # Section 5
            train_questions = [
                ("Q37: Internal/External audit done periodically with records", 2, False),
                ("Q38: Effective consumer complaints redressal mechanism", 2, False),
                ("Q39: Food handlers trained to handle food safely", 2, False),
                ("Q40: Appropriate documentation & records retained for 1 year", 4, True)
            ]
            q_train = render_checklist_section("5. Training & Complaint Handling (Q37 - Q40)", train_questions)

            # Combine dictionaries
            audit_responses = {**q_design, **q_ops, **q_maint, **q_hyg, **q_train}

            st.markdown("---")
            st.markdown("#### 📸 Audit Evidence & Photo Documentation")
            audit_photos = st.file_uploader(
                "Upload Inspection Snaps (Select multiple files if needed)", 
                type=["jpg", "png", "jpeg"], 
                accept_multiple_files=True
            )
            
            audit_remarks = st.text_area("Overall Audit Remarks / Corrective Actions Required")

            if st.form_submit_button("Calculate Score & Submit Audit", type="primary"):
                if not audit_vendor_name:
                    st.error("❌ Vendor Name is required.")
                else:
                    with st.spinner("Uploading photos and calculating compliance score..."):
                        photo_urls = []
                        if audit_photos:
                            for idx, photo_file in enumerate(audit_photos):
                                url = upload_photo(photo_file, "vendor_audits", f"{audit_vendor_name.replace(' ', '_')}_{idx+1}")
                                if url:
                                    photo_urls.append(url)
                        
                        final_proof_url = ", ".join(photo_urls) if photo_urls else None

                        # Automatic Scoring Engine
                        earned_points = 0
                        max_points = 90
                        
                        for q_key, data in audit_responses.items():
                            status = data["status"]
                            pts = data["points"]
                            
                            if status == "Compliance (C)":
                                earned_points += pts
                            elif status == "Partial Compliance (PC)":
                                earned_points += (pts / 2)

                        final_percentage = (earned_points / max_points) * 100

                        # Grade Assignment based strictly on percentage
                        if final_percentage >= 80:
                            grade = "A+ (Exemplar)"
                            status_result = "Passed"
                        elif 72 <= final_percentage < 80:
                            grade = "A (Satisfactory)"
                            status_result = "Passed"
                        elif 45 <= final_percentage < 72:
                            grade = "B (Needs Improvement)"
                            status_result = "Conditionally Approved"
                        else:
                            grade = "Non Compliance"
                            status_result = "Failed"

                        # Save payload to Supabase
                        payload = {
                            "vendor_name": audit_vendor_name,
                            "category": "General Manufacturing",
                            "score": f"{final_percentage:.1f}% ({earned_points}/{max_points} - Grade: {grade})",
                            "status": status_result,
                            "remark": f"Auditor: {audit_fso} | License: {audit_lic_no} | Date: {audit_date.strftime('%d-%b-%Y')} | Remarks: {audit_remarks}",
                            "audit_month": selected_month,
                            "proof_url": final_proof_url
                        }
                        
                        try:
                            if supabase is not None:
                                supabase.table("vendor_audits").insert(payload).execute()
                            
                            # Note: Ensure generate_detailed_checklist_pdf is defined elsewhere in your environment
                            if 'generate_detailed_checklist_pdf' in globals():
                                pdf_report_bytes = generate_detailed_checklist_pdf(
                                    audit_vendor_name, audit_fso, audit_lic_no, audit_address, audit_date,
                                    audit_responses, final_percentage, grade, audit_remarks, final_proof_url
                                )
                                st.session_state['latest_generated_audit_pdf'] = {
                                    "name": audit_vendor_name,
                                    "data": pdf_report_bytes
                                }
                            
                            st.success(f"✅ Audit Completed & Saved! Score: {final_percentage:.1f}% | Grade: {grade}")
                            st.balloons()
                        except Exception as e:
                            st.error(f"❌ Failed to save audit: {e}")

        # Instant Download Button if just submitted
        if 'latest_generated_audit_pdf' in st.session_state:
            latest = st.session_state['latest_generated_audit_pdf']
            st.markdown("---")
            st.success(f"📄 Itemized audit report ready for **{latest['name']}**!")
            st.download_button(
                label=f"📥 Download Itemized PDF Report ({latest['name']})",
                data=latest['data'],
                file_name=f"General_Manufacturing_Audit_{latest['name'].replace(' ', '_')}.pdf",
                mime="application/pdf",
                type="primary"
            )

# ==========================================
# TAB 4: LICENSE SUMMARY & DIGITAL VAULT
# ==========================================
with tab_lic_summary:
    st.subheader("📜 License Compliance Summary & Digital Vault")
    st.caption("High-level overview, statutory license date tracking, and secure document archiving pulled from Supabase.")
    
    # 1. LOAD DATA FROM SUPABASE
    df_lic = pd.DataFrame()
    try:
        if supabase is not None:
            response = supabase.table("license_tracker").select("*").execute()
            if response.data:
                df_lic = pd.DataFrame(response.data)
                # Rename columns back to match your tracker format for the UI
                df_lic = df_lic[['s_no', 'location', 'city', 'fssai', 'trade', 'fire', 'pollution_cto', 'signage', 'remark']]
                df_lic.columns = ['S.no', 'Location', 'City', 'FSSAI', 'Trade', 'Fire', 'Pollution CTO', 'Signage', 'Remark']
    except Exception as e:
        st.error(f"Could not fetch license data from Supabase: {e}")

    if df_lic.empty:
        st.info("📂 No license data found in the cloud database. Upload your Excel sheet below *once* to save it permanently.")
    else:
        # ------------------------------------------
        # EXPIRY & METRIC CALCULATIONS
        # ------------------------------------------
        today = datetime.datetime.now()
        three_months_later = today + datetime.timedelta(days=90)
        
        license_cols = ['FSSAI', 'Trade', 'Fire', 'Pollution CTO', 'Signage']
        expiring_soon_count = 0
        chart_data_rows = []
        
        for _, row in df_lic.iterrows():
            loc = row['Location']
            city = row['City']
            active_licenses = 0
            expiring_alert = False
            
            for col in license_cols:
                val = row[col]
                if pd.notna(val) and str(val).strip().lower() not in ['nan', 'nat', 'none', 'not started', 'under process', 'part of trade lic']:
                    active_licenses += 1
                    try:
                        dt = pd.to_datetime(val)
                        if today <= dt <= three_months_later:
                            expiring_soon_count += 1
                            expiring_alert = True
                    except:
                        pass
            
            chart_data_rows.append({
                "Location": f"{loc} ({city})",
                "Active Licenses": active_licenses,
                "Expiring Soon": 1 if expiring_alert else 0
            })
            
        total_stores = len(df_lic)
        total_cities = df_lic['City'].dropna().nunique()
        
        # TOP KPI METRICS
        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric("🏢 Total Tracked Facilities", f"{total_stores} Stores")
        col_m2.metric("🌍 Operating Cities", f"{total_cities} Cities")
        col_m3.metric("🚨 Expiring in 3 Months", f"{expiring_soon_count} Licenses", delta_color="inverse" if expiring_soon_count > 0 else "off")
        
        st.markdown("---")
        
        # BAR CHART
        st.markdown("### 📊 Facility License Portfolio & Expiry Alert Overview")
        if len(chart_data_rows) > 0:
            chart_df = pd.DataFrame(chart_data_rows).set_index("Location")
            st.bar_chart(chart_df[["Active Licenses"]], color="#1f77b4")
        
        st.markdown("---")
        
        # FILTERS & TABLE DETAILS
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            valid_cities = [c for c in df_lic['City'].unique() if pd.notna(c) and str(c).strip().lower() != 'nan']
            city_filter = st.selectbox("Filter by City", ["All Cities"] + valid_cities)
        with col_f2:
            status_filter = st.selectbox("Filter by Action Required", ["All Stores", "Pending / Has Remarks"])
            
        filtered_df = df_lic.copy()
        if city_filter != "All Cities":
            filtered_df = filtered_df[filtered_df['City'] == city_filter]
        if status_filter == "Pending / Has Remarks":
            filtered_df = filtered_df[filtered_df['Remark'].notna() & (filtered_df['Remark'].astype(str).str.strip() != '') & (filtered_df['Remark'].astype(str).str.lower() != 'nan')]
            
        st.markdown("---")
        st.markdown("### 🔍 Store License Details & Document Vault")
        
        def format_date(d):
            if pd.isna(d) or str(d).strip().lower() in ['nan', 'nat', 'none']: 
                return "N/A"
            if isinstance(d, datetime.datetime): 
                return d.strftime('%d-%b-%Y')
            return str(d)[:10] 

        # Loop through filtered stores
        for _, row in filtered_df.iterrows():
            loc_name = row['Location']
            city_name = row['City']
            
            with st.expander(f"📍 {loc_name} ({city_name})"):
                cols = st.columns(5)
                cols[0].metric("FSSAI", format_date(row['FSSAI']))
                cols[1].metric("Trade License", format_date(row['Trade']))
                cols[2].metric("Fire NOC", format_date(row['Fire']))
                cols[3].metric("Pollution CTO", format_date(row['Pollution CTO']))
                cols[4].metric("Signage", format_date(row['Signage']))
                
                remark_text = row['Remark']
                if pd.notna(remark_text) and str(remark_text).strip().lower() not in ['nan', 'none', '']:
                    st.warning(f"⚠️ **Status / Remarks:** {remark_text}")
                else:
                    st.success("✅ All statutory licenses up to date.")
                
                # --- NEW: SECURE DOCUMENT VIEWER & UPLOADER PER STORE ---
                st.markdown("---")
                st.markdown(f"**📂 Scanned Certificate Vault for {loc_name}**")
                
                # Fetch uploaded files for this specific store from Supabase 'store_licenses' table
                store_docs = []
                try:
                    if supabase is not None:
                        doc_res = supabase.table("store_licenses").select("*").eq("store_id", loc_name).execute()
                        if doc_res.data:
                            store_docs = doc_res.data
                except Exception:
                    pass
                
                if store_docs:
                    st.caption("Existing uploaded files in cloud vault:")
                    for doc in store_docs:
                        col_d1, col_d2, col_d3 = st.columns([2, 2, 1])
                        col_d1.text(f"📌 {doc['license_type']} ({doc['license_number']})")
                        col_d2.text(f"Exp: {doc['expiry_date']}")
                        col_d3.markdown(f"[🔗 View File]({doc['file_url']})", unsafe_allow_html=True)
                else:
                    st.caption("No physical certificate files uploaded for this location yet.")
                
                # Expandable upload form for individual store files (Zero Manual Typing)
                with st.form(key=f"upload_form_{loc_name}"):
                    st.markdown("##### Upload New Certificate Copy")
                    
                    # 1. Select Category & File (No text box needed for certificate number)
                    up_type = st.selectbox("Certificate Type", [
                        "Central FSSAI", 
                        "State FSSAI", 
                        "Trade License", 
                        "Fire NOC", 
                        "Pollution CTO", 
                        "Signage Permit"
                    ], key=f"type_{loc_name}")
                    
                    up_file = st.file_uploader("Upload PDF or Image", type=["pdf", "jpg", "jpeg", "png"], key=f"file_{loc_name}")
                    
                    if st.form_submit_button("🔒 Upload to Cloud Vault"):
                        if not up_file:
                            st.error("❌ Please select a file to upload.")
                        else:
                            with st.spinner("Encrypting and syncing document..."):
                                try:
                                    # 2. Automatically generate a clean, uniform reference number
                                    current_year = datetime.datetime.now().strftime("%Y")
                                    auto_cert_number = f"{up_type} - {loc_name} ({current_year})"
                                    
                                    file_url = ""
                                    if cloudinary:
                                        upload_res = cloudinary.uploader.upload(
                                            up_file, 
                                            folder=f"cbtl/licenses/{loc_name.replace(' ', '_')}"
                                        )
                                        file_url = upload_res.get("secure_url", "")
                                    
                                    payload = {
                                        "store_id": loc_name,
                                        "license_type": up_type,
                                        "license_number": auto_cert_number, # Automatically standardized!
                                        "expiry_date": str(datetime.datetime.now().date()), 
                                        "file_url": file_url
                                    }
                                    if supabase is not None:
                                        supabase.table("store_licenses").insert(payload).execute()
                                        st.success("✅ File uploaded successfully! Refreshing...")
                                        st.rerun()
                                except Exception as e:
                                    st.error(f"❌ Upload failed: {e}")

    # 3. PERMANENT CLOUD UPLOAD SECTION (EXCEL BULK SYNC)
    st.markdown("---")
    st.markdown("### 📂 Permanent Cloud License Excel Sync")
    st.caption("Upload your master Excel sheet *once* to update all statutory dates globally in Supabase.")
    
    uploaded_file = st.file_uploader("Upload Master License Tracker Excel File", type=["xlsx", "xls"], key="cloud_license_uploader")
    
    if uploaded_file is not None:
        if st.button("🚀 Sync & Save Permanently to Cloud Database", type="primary"):
            with st.spinner("Uploading and syncing records to Supabase..."):
                try:
                    df_upload = pd.read_excel(uploaded_file, sheet_name="Sheet1")
                    df_upload.columns = ['s_no', 'location', 'city', 'fssai', 'trade', 'fire', 'pollution_cto', 'signage', 'remark']
                    
                    # Drop the header row if it's acting as a sub-header
                    df_upload = df_upload.iloc[1:].reset_index(drop=True)
                    
                    # 1. Format dates nicely
                    for col in ['fssai', 'trade', 'fire', 'pollution_cto', 'signage']:
                        if col in df_upload.columns:
                            df_upload[col] = pd.to_datetime(df_upload[col], errors='coerce').dt.strftime('%Y-%m-%d')

                    # 2. Convert entire dataframe to string to strip away complex Pandas/NumPy types
                    df_upload = df_upload.astype(str)
                    
                    # 3. BULLETPROOF DICTIONARY CLEANER
                    raw_records = df_upload.to_dict(orient="records")
                    clean_records = []
                    
                    for row in raw_records:
                        clean_row = {}
                        for k, v in row.items():
                            if pd.isna(v) or str(v).strip().lower() in ['nan', 'nat', 'none', '<na>', '']:
                                clean_row[k] = None
                            else:
                                clean_row[k] = str(v).strip()
                        clean_records.append(clean_row)
                    
                    if supabase is not None:
                        # Clear old table data first
                        supabase.table("license_tracker").delete().neq("id", 0).execute()
                        
                        # Insert clean records
                        supabase.table("license_tracker").insert(clean_records).execute()
                        
                        st.success("✅ License tracker successfully saved to Supabase cloud database! Refreshing...")
                        st.rerun()
                except Exception as e:
                    st.error(f"❌ Failed to sync to database: {e}")

# ==========================================
# TAB 5: NSF AUDIT INTELLIGENCE
# ==========================================
with tab_nsf:
    st.subheader("📈 NSF Audit Intelligence & Network Performance")
    st.caption("Deep-dive analytics into third-party NSF food safety audits across Corporate (Ekaagra) and Sub-Franchise locations.")

    if not df_db.empty:
        # ------------------------------------------
        # 1. HIGH-LEVEL NETWORK METRICS
        # ------------------------------------------
        total_nsf = len(df_db)
        ekaagra_count = len(ekaagra_df)
        sub_count = len(subfranchise_df)

        col1, col2, col3 = st.columns(3)
        col1.metric("Total Tracked NSF Audits", total_nsf)
        col2.metric("🏢 Ekaagra Direct Stores", ekaagra_count)
        col3.metric("🤝 Sub-Franchise Stores", sub_count)

        st.markdown("---")

        # ------------------------------------------
        # 2. VISUAL ANALYTICS (Corporate vs Franchise)
        # ------------------------------------------
        st.markdown("### 📊 Performance by Ownership Type")
        col_chart1, col_chart2 = st.columns(2)

        with col_chart1:
            if 'score' in df_db.columns and 'Type' in df_db.columns:
                # Average Score by Type
                avg_scores = df_db.groupby('Type')['score'].mean().reset_index()
                fig_avg = px.bar(
                    avg_scores, x='Type', y='score', color='Type', text='score',
                    title="Average Audit Score (%) by Ownership",
                    color_discrete_map={"Ekaagra Direct": "#3b82f6", "Sub Franchise": "#f59e0b"}
                )
                fig_avg.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
                fig_avg.update_layout(showlegend=False, yaxis_range=[0, 100])
                st.plotly_chart(fig_avg, use_container_width=True)
            else:
                st.info("Score data not available for visualization.")

        with col_chart2:
            # Look for either 'result' or 'status' column to build distribution
            status_col = 'result' if 'result' in df_db.columns else 'status' if 'status' in df_db.columns else None
            
            if status_col and 'Type' in df_db.columns:
                # Pass/Fail/Completed distribution by Type
                result_dist = df_db.groupby(['Type', status_col]).size().reset_index(name='Count')
                fig_dist = px.bar(
                    result_dist, x='Type', y='Count', color=status_col, barmode='group', text='Count',
                    title=f"Audit Status Distribution",
                    color_discrete_map={"PASS": "#10B981", "COMPLETED": "#10B981", "FAIL": "#EF4444", "EXPIRED": "#EF4444"}
                )
                fig_dist.update_traces(textposition='outside')
                st.plotly_chart(fig_dist, use_container_width=True)
            else:
                st.info("Status/Result data not available for visualization.")

        st.markdown("---")

        # ------------------------------------------
        # 3. DETAILED DATA SPLITS (Ekaagra vs Sub-Franchise)
        # ------------------------------------------
        st.markdown("### 📋 Detailed Audit Records by Network")
        
        # Use nested tabs to keep the data tables clean and separated
        sub_tab_ekaagra, sub_tab_franchise = st.tabs(["🏢 Ekaagra Direct (Corporate)", "🤝 Sub-Franchise Network"])
        
        with sub_tab_ekaagra:
            if not ekaagra_df.empty:
                st.dataframe(ekaagra_df, use_container_width=True, hide_index=True)
            else:
                st.info("No Ekaagra Direct records found in the database.")
                
        with sub_tab_franchise:
            if not subfranchise_df.empty:
                st.dataframe(subfranchise_df, use_container_width=True, hide_index=True)
            else:
                st.info("No Sub-Franchise records found in the database.")

    else:
        st.warning("⚠️ No NSF Audit data found in the cloud database. Please ensure your Supabase connection is active and populated.")

# ==========================================
# TAB 6: REPORTS & ARCHIVE
# ==========================================
with tab_reports:
    st.subheader("📑 Executive PDF Report Generation")
    
    def generate_pdf(month_str, records, vendors, nsf_data):
        if FPDF is None: return None
        pdf = FPDF()
        pdf.add_page()
        
        # --- Document Header ---
        pdf.set_font("Arial", size=15, style='B')
        pdf.cell(200, 8, txt="The Coffee Bean & Tea Leaf (CBTL) India", ln=1, align='C')
        pdf.set_font("Arial", size=10, style='I')
        pdf.cell(200, 5, txt="Ekaagra Ostalaritza Private Limited - QA & Compliance Vault", ln=1, align='C')
        pdf.ln(2)
        
        pdf.set_font("Arial", size=11, style='B')
        pdf.cell(200, 7, txt=f"Executive Briefing Report | Period: {month_str}", ln=1, align='C')
        pdf.set_font("Arial", size=9)
        pdf.cell(200, 5, txt=f"Generated On: {datetime.date.today().strftime('%d-%b-%Y')} | Admin: Girish Kumar", ln=1, align='C')
        pdf.ln(6)
        
        # --- 1. Store Network Compliance Section ---
        pdf.set_font("Arial", size=11, style='B')
        pdf.cell(200, 6, txt="1. Store Network & Staff Compliance Status", ln=1, align='L')
        
        pdf.set_font("Arial", size=9)
        if records:
            for record in records:
                store_name = record.get('name', 'Unknown')
                fostac = record.get('fostac_pending', 0)
                med = record.get('medical_pending', 0)
                is_comp = "Yes" if record.get('is_compliant') else "No"
                row_text = f" - {store_name} | Compliant: {is_comp} | FoSTaC Pending: {fostac} | Medical: {med}"
                pdf.cell(200, 5, txt=row_text, ln=1, align='L')
        else:
            pdf.cell(200, 5, txt=" - No store data available.", ln=1, align='L')
            
        pdf.ln(4)
        
        # --- 2. Cleaned NSF Audit Summary ---
        pdf.set_font("Arial", size=11, style='B')
        pdf.cell(200, 6, txt="2. NSF Audit Performance Summary (Cloud Records)", ln=1, align='L')
        
        pdf.set_font("Arial", size=9)
        if not nsf_data.empty and 'store_name' in nsf_data.columns:
            valid_nsf = nsf_data.dropna(subset=['score']).copy()
            valid_nsf = valid_nsf[valid_nsf['score'] > 0]
            
            if not valid_nsf.empty:
                for _, row in valid_nsf.head(15).iterrows():
                    s_name = row.get('store_name', 'Unknown')
                    s_score = row.get('score', 0)
                    s_result = row.get('result', 'N/A')
                    row_text = f" - {s_name} | Score: {s_score}% | Result: {s_result}"
                    pdf.cell(200, 5, txt=row_text, ln=1, align='L')
            else:
                pdf.cell(200, 5, txt=" - No valid NSF scores available in the database.", ln=1, align='L')
        else:
            pdf.cell(200, 5, txt=" - No NSF audit records found.", ln=1, align='L')
            
        pdf.ln(4)
        
        # --- 3. Enhanced Vendor & Supply Chain Section ---
        pdf.set_font("Arial", size=11, style='B')
        pdf.cell(200, 6, txt="3. Vendor Operations & Supply Chain Status", ln=1, align='L')
        
        pdf.set_font("Arial", size=9)
        if vendors:
            for v in vendors:
                v_name = v.get('vendor', 'Unknown')
                v_cat = v.get('category', 'General')
                v_score = v.get('score', 'N/A')
                v_status = v.get('status', 'N/A')
                v_remark = v.get('remark', 'None')
                v_text = f" - [{v_cat}] {v_name} | Status: {v_status} | Score: {v_score}"
                pdf.cell(200, 5, txt=v_text, ln=1, align='L')
                pdf.cell(200, 4, txt=f"   Remark: {v_remark}", ln=1, align='L')
        else:
            pdf.cell(200, 5, txt=" - No vendor audits recorded for this period.", ln=1, align='L')

        pdf.ln(4)

        # --- 4. License Compliance Flags ---
        pdf.set_font("Arial", size=11, style='B')
        pdf.cell(200, 6, txt="4. Active License Compliance Flags", ln=1, align='L')
        
        pdf.set_font("Arial", size=9)
        flagged_stores = [r for r in records if r.get('has_license_issue')]
        if flagged_stores:
            for store in flagged_stores:
                pdf.cell(200, 5, txt=f" - {store['name']} has pending or expired statutory licenses.", ln=1, align='L')
        else:
            pdf.cell(200, 5, txt=" - All store statutory licenses are currently valid and up to date.", ln=1, align='L')

        try:
            return bytes(pdf.output())
        except TypeError:
            return pdf.output(dest='S').encode('latin-1')

    if st.button("Generate Executive PDF Report", type="primary"):
        vendor_data = st.session_state.get('vendor_db', {}).get(selected_month, [])
        pdf_bytes = generate_pdf(selected_month, monthly_records, vendor_data, df_db)
        
        if pdf_bytes:
            st.session_state['pdf_archive'][selected_month] = pdf_bytes
            st.success("✅ Executive PDF generated successfully!")
        else:
            st.error("FPDF library missing.")
            
    if selected_month in st.session_state['pdf_archive']:
        st.download_button(
            label="📥 Download Executive PDF Report", 
            data=st.session_state['pdf_archive'][selected_month], 
            file_name=f"CBTL_Executive_Report_{selected_month}.pdf", 
            mime="application/pdf"
        )

# ==========================================
# TAB 7: RESOURCES VAULT (Central Control)
# ==========================================
with tab_res:
    st.subheader("📚 Central Resources & Document Management")
    st.caption("Upload, view, and manage master documents pushed out to all store locations.")
    
    # 1. Upload Section
    with st.form("upload_master_resource"):
        st.markdown("##### 📤 Publish New Master Document")
        doc_category = st.selectbox("Document Category", [
            "QA SOPs & Safety", 
            "Menu & Nutrition Booklet", 
            "Shelf Life Chart", 
            "Chemical Info Sheet"
        ])
        doc_file = st.file_uploader("Upload Master Document (PDF)", type=["pdf"])
        
        if st.form_submit_button("🚀 Publish to All Stores", type="primary"):
            if doc_file:
                with st.spinner("Uploading to cloud storage..."):
                    try:
                        # Upload to Cloudinary under a dedicated central folder
                        file_url = ""
                        if cloudinary:
                            upload_res = cloudinary.uploader.upload(
                                doc_file, 
                                folder="cbtl/central_resources",
                                resource_type="auto"
                            )
                            file_url = upload_res.get("secure_url", "")
                        
                        # Save reference to Supabase 'central_resources' table
                        payload = {
                            "category": doc_category,
                            "file_name": doc_file.name,
                            "file_url": file_url,
                            "updated_at": str(datetime.datetime.now().date())
                        }
                        if supabase is not None:
                            supabase.table("central_resources").insert(payload).execute()
                            st.success(f"✅ Master document for '{doc_category}' successfully published to the store network!")
                            st.rerun()
                        else:
                            st.error("Database connection missing.")
                    except Exception as e:
                        st.error(f"❌ Upload failed: {e}")
            else:
                st.error("❌ Please upload a PDF document.")
                
    st.markdown("---")
    
    # 2. View and Download Section (Pulled live from Supabase)
    st.markdown("### 📂 Active Network Documents Vault")
    st.caption("Review or download the current active files accessible by store teams.")
    
    try:
        if supabase is not None:
            res_query = supabase.table("central_resources").select("*").execute()
            if res_query.data:
                df_resources = pd.DataFrame(res_query.data)
                
                for _, row in df_resources.iterrows():
                    col_d1, col_d2, col_d3 = st.columns([2, 2, 1])
                    col_d1.text(f"📌 {row['category']}")
                    col_d2.text(f"File: {row['file_name']}")
                    col_d3.markdown(f"[🔗 View / Download]({row['file_url']})", unsafe_allow_html=True)
            else:
                st.info("📂 No custom master documents uploaded yet. Default guidelines are currently active.")
        else:
            st.warning("Database connection inactive.")
    except Exception as e:
        st.info("Loading resource repository...")
# ==========================================
# TAB 8: SYSTEM ADMINISTRATION
# ==========================================
with tab_admin:
    st.subheader("⚙️ Store Portfolio & System Administration")
    
    # --- 1. YOUR ORIGINAL STORE MANAGEMENT TOOL ---
    with st.expander("➕ Add a New Store Location", expanded=False):
        with st.form("new_store_form"):
            new_name = st.text_input("Store Name")
            is_out = st.checkbox("Is Outstation?")
            if st.form_submit_button("Add Store") and new_name:
                # Ensure the list exists in session state before appending
                if 'master_stores' not in st.session_state:
                    st.session_state['master_stores'] = []
                st.session_state['master_stores'].append({'name': new_name, 'is_outstation': is_out})
                st.success("Added!")
                st.rerun()
                
    st.markdown("---") # Adds a clean visual divider line
    
    # --- 2. THE NEW TERMINOLOGY UNIFICATION TRACKER ---
    st.subheader("📦 Supply Chain Terminology Unification Management")
    st.caption("Track and update vendor compliance with standardized retail names.")

    try:
        if supabase is not None:
            # Fetch the master item list
            response = supabase.table("master_item_reference").select("*").order("id").execute()
            
            if response.data:
                df_items = pd.DataFrame(response.data)
                
                # --- METRICS & PROGRESS ---
                total_items = len(df_items)
                unified_items = df_items['is_name_unified'].sum()
                completion_rate = (unified_items / total_items) if total_items > 0 else 0
                
                st.progress(completion_rate, text=f"Overall Unification Progress: {int(unified_items)} out of {total_items} items unified.")
                
                # --- INTERACTIVE DATA EDITOR ---
                st.info("Instructions: When a vendor successfully updates their invoice to match the target retail name, check the 'Unified?' box below and save.")
                
                edited_df = st.data_editor(
                    df_items[['id', 'warehouse_item_name', 'store_retail_name', 'item_category', 'is_name_unified']],
                    use_container_width=True,
                    hide_index=True,
                    disabled=['id', 'warehouse_item_name', 'store_retail_name', 'item_category'],
                    column_config={
                        "id": None, 
                        "warehouse_item_name": st.column_config.TextColumn("Current Invoice Name"),
                        "store_retail_name": st.column_config.TextColumn("Target Retail Name (Standard)"),
                        "item_category": st.column_config.TextColumn("Category"),
                        "is_name_unified": st.column_config.CheckboxColumn("Unified?", default=False)
                    },
                    key="unification_tracker"
                )
                
                # --- SAVE LOGIC ---
                if st.button("💾 Save Compliance Updates", type="primary"):
                    with st.spinner("Syncing updates to central database..."):
                        updates_made = 0
                        for index, row in edited_df.iterrows():
                            original_status = df_items.loc[index, 'is_name_unified']
                            new_status = row['is_name_unified']
                            
                            if original_status != new_status:
                                supabase.table("master_item_reference").update(
                                    {"is_name_unified": new_status}
                                ).eq("id", row['id']).execute()
                                updates_made += 1
                                
                        if updates_made > 0:
                            st.success(f"✅ Successfully updated {updates_made} terminology records.")
                            st.rerun() 
                        else:
                            st.info("No changes detected.")
                            
            else:
                st.warning("No items found in the master reference table. Please add items via Supabase.")
    except Exception as e:
        st.error(f"Failed to load terminology data: {e}")
