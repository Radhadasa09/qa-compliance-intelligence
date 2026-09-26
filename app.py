try:
    import google.generativeai as genai
except ImportError:
    genai = None
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
import pdfplumber

try:
    from fpdf import FPDF
except ImportError:
    FPDF = None

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="QA Intelligence Command Center", 
    layout="wide", 
    page_icon="🛡️",
    initial_sidebar_state="expanded"
)

# --- UNIFIED BRANDING REMOVAL & SPACING FIX ---
st.markdown("""
 <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        
        section[data-testid="stSidebar"] {
            background-color: #FFFFFF;
            border-right: 1px solid #E2E8F0;
        }

        div[data-testid="stExpander"] {
            background-color: #EAF2F8;
            border-radius: 10px;
            border: 1px solid #D6EAF8;
        }
        div[data-testid="stExpander"] summary {
            background-color: #EAF2F8;
            border-radius: 10px;
        }
        
        [data-testid="stMetric"] {
            background-color: #EAF2F8;
            border-radius: 8px;
            padding: 10px 15px;
            border: none;
        }
        [data-testid="stMetric"]:has(label:contains("Score")), 
        [data-testid="stMetric"]:has(label:contains("Grade")) {
            background: linear-gradient(135deg, #E0F8E9 0%, #C8F0D6 100%);
            border-left: 4px solid #2ECC71;
        }
        
        .block-container {
            padding-top: 1.5rem; 
            padding-bottom: 2rem;
            max-width: 1200px;
        }
    </style>
""", unsafe_allow_html=True)# --- CLOUDINARY CONFIGURATION & HELPER ---
try:
    cloudinary.config(
        cloud_name=st.secrets.get("CLOUDINARY_CLOUD_NAME", os.environ.get("CLOUDINARY_CLOUD_NAME")),
        api_key=st.secrets.get("CLOUDINARY_API_KEY", os.environ.get("CLOUDINARY_API_KEY")),
        api_secret=st.secrets.get("CLOUDINARY_API_SECRET", os.environ.get("CLOUDINARY_API_SECRET")),
        secure=True
    )
except Exception:
    pass

cloudinary_configured = (
    bool(cloudinary.config().cloud_name) and 
    bool(cloudinary.config().api_key) and 
    bool(cloudinary.config().api_secret)
)

def upload_photo(file_buffer, folder_name, sub_folder):
    try:
        res = cloudinary.uploader.upload(file_buffer, folder=f"cbtl/{folder_name}/{sub_folder}")
        return res.get("secure_url")
    except Exception as e:
        st.error(f"Upload failed: {e}")
        return None

# --- 1. SECURE DATABASE CONNECTION ---
try:
    URL = st.secrets.get("SUPABASE_URL", os.environ.get("SUPABASE_URL"))
    KEY = st.secrets.get("SUPABASE_KEY", os.environ.get("SUPABASE_KEY"))
    if not URL or not KEY:
        raise ValueError("Missing Supabase credentials")
    supabase: Client = create_client(URL, KEY)
except Exception:
    supabase = None

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
@st.cache_data(ttl=300)
def load_store_master():
    if supabase is None:
        return pd.DataFrame()
    try:
        response = supabase.table("store_master").select("*").eq("is_active", True).order("site_code").execute()
        return pd.DataFrame(response.data)
    except Exception:
        return pd.DataFrame()

df_stores_dynamic = load_store_master()

# Dynamically generate the mapping dictionary and dropdown list
if not df_stores_dynamic.empty:
    store_name_map = dict(zip(df_stores_dynamic['site_code'], df_stores_dynamic['store_name']))
    store_opt = [f"{row['site_code']} - {row['store_name']}" for _, row in df_stores_dynamic.iterrows()]
else:
    store_name_map = {}
    store_opt = []

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

# --- SIDEBAR COMMAND NAV ---
with st.sidebar:
    st.markdown("### 🛡️ CBTL India Command")
    st.caption("Ekaagra Master Franchise • QA Hub")
    selected_month = st.selectbox("Global Period Filter", ["Live Data", "Present Quarter (Q3 2026)", "August 2026", "September 2026", "October 2026"])
    
    st.markdown("---")
    nav_selection = st.radio(
        "Navigation",
        [
            "📊 Executive Dashboard",
            "🏬 Retail Operations",
            "🚚 Vendor & Supply Chain",
            "📜 License Summary",
            "📈 NSF Audit Intelligence",
            "📑 Reports & Archive",
            "📚 Resources Vault",
            "💳 Finance Invoices",
            "⚙️ System Administration",
            "🤖 AI Support Assistant"
        ],
        label_visibility="collapsed"
    )
    st.markdown("---")
    st.caption("Admin: Girish Kumar | v2.4 Live")

monthly_records = []
for idx, row in df_stores.iterrows():
    s_name = row['name']
    m_data = get_store_monthly(s_name, selected_month if selected_month != "Live Data" else "August 2026")
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

# --- Filter only the base cloud data for Q3 if selected ---
if selected_month == "Present Quarter (Q3 2026)":
    if not df_db.empty and 'audit_date' in df_db.columns:
        df_db['audit_date'] = pd.to_datetime(df_db['audit_date'], errors='coerce')
        df_db = df_db[(df_db['audit_date'].dt.year == 2026) & (df_db['audit_date'].dt.quarter == 3)]
        # Re-apply strict classification to keep Ekaagra Direct isolated for the Executive Dashboard
        df_db['site_code_str'] = df_db['site_code'].astype(str).str.strip().str.replace(r'\.0$', '', regex=True)
        df_db['Type'] = df_db['site_code_str'].apply(lambda x: "Ekaagra Direct" if x.startswith("189") and x != "1891004" else "Sub Franchise") # adjusting for specific overrides if needed
        ekaagra_df = df_db[df_db['Type'] == "Ekaagra Direct"]
        subfranchise_df = df_db[df_db['Type'] == "Sub Franchise"]
# --- PDF GENERATOR HELPERS ---
def generate_pdf(month_str, records, vendors, nsf_data):
    if FPDF is None: return None
    pdf = FPDF()
    pdf.add_page()
    
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

def generate_detailed_checklist_pdf(name, fso, lic, addr, audit_dt, responses, pct, grade, rem, proof):
    if FPDF is None: return b""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=14, style='B')
    pdf.cell(200, 8, txt="General Manufacturing Vendor Audit Report", ln=1, align='C')
    pdf.set_font("Arial", size=10)
    pdf.cell(200, 6, txt=f"Vendor: {name} | FSO: {fso} | License: {lic}", ln=1, align='C')
    pdf.cell(200, 6, txt=f"Address: {addr} | Date: {audit_dt} | Score: {pct:.1f}% ({grade})", ln=1, align='C')
    pdf.ln(5)
    pdf.set_font("Arial", size=9)
    
    for q_key, data in responses.items():
        # Combine the text
        raw_text = f"[{data['status']}] {q_key} - Note: {data.get('comment', '')}"
        # Strip unsupported emojis/unicode that crash FPDF Arial font
        safe_text = raw_text.encode('latin-1', 'ignore').decode('latin-1')
        
        # Use explicit width 190 (Standard A4 width minus margins) instead of 0
        pdf.multi_cell(190, 5, txt=safe_text)
        pdf.ln(1) # Add a small visual gap between questions
        
    if rem:
        pdf.ln(3)
        safe_rem = f"Overall Remarks: {rem}".encode('latin-1', 'ignore').decode('latin-1')
        pdf.multi_cell(190, 5, txt=safe_rem)
        
    try:
        return bytes(pdf.output())
    except TypeError:
        return pdf.output(dest='S').encode('latin-1')
# ==========================================
# MAIN ROUTER SWITCH
# ==========================================
if nav_selection == "📊 Executive Dashboard":
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

    if not df_db.empty and 'score' in df_db.columns and 'store_name' in df_db.columns:
        st.markdown("### 🏬 Network Operations (Historical Journey Stack)")
        
        tab_ekaagra, tab_sub = st.tabs(["🏢 Ekaagra Direct", "🏪 Sub Franchise"])
        
        with tab_ekaagra:
            if not ekaagra_df.empty:
                fig_nsf_e = px.bar(
                    ekaagra_df, x='store_name', y='score', text='score',
                    title="Ekaagra Direct Outlets Cumulative/Historical NSF Scores",
                    color='result' if 'result' in ekaagra_df.columns else 'score', 
                    color_discrete_map={'PASS': '#10B981', 'FAIL': '#EF4444'}
                )
                fig_nsf_e.update_traces(textposition='outside')
                fig_nsf_e.update_layout(xaxis_tickangle=-35, showlegend=True, margin=dict(t=40, b=40, l=0, r=0))
                st.plotly_chart(fig_nsf_e, width='stretch')
            else:
                st.info("No Ekaagra Direct NSF data available in the selected period.")

        with tab_sub:
            if not subfranchise_df.empty:
                fig_nsf_s = px.bar(
                    subfranchise_df, x='store_name', y='score', text='score',
                    title="Sub Franchise Outlets Cumulative/Historical NSF Scores",
                    color='result' if 'result' in subfranchise_df.columns else 'score', 
                    color_discrete_map={'PASS': '#10B981', 'FAIL': '#EF4444'}
                )
                fig_nsf_s.update_traces(textposition='outside')
                fig_nsf_s.update_layout(xaxis_tickangle=-35, showlegend=True, margin=dict(t=40, b=40, l=0, r=0))
                st.plotly_chart(fig_nsf_s, width='stretch')
            else:
                st.info("No Sub Franchise NSF data available in the selected period.")
    else:
        st.info("No NSF data available in the cloud database yet.")
    st.markdown("### 👥 Store-by-Store Staff Compliance Status")
    try:
        if supabase is not None:
            comp_response = supabase.table("store_monthly_compliance").select("*").execute()
            if comp_response.data:
                df_comp = pd.DataFrame(comp_response.data).sort_values(by='id', ascending=False)
                st.dataframe(
                    df_comp[['store_name', 'month_year', 'fostac_pending', 'medical_pending', 'fully_compliant', 'self_audit_done', 'self_audit_score', 'remark']],
                    use_container_width=True, hide_index=True,
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
                st.info("📂 No compliance data found.")
    except Exception as e:
        st.error(f"❌ Could not load compliance data from the cloud: {e}")

elif nav_selection == "🏬 Retail Operations":
    st.header("🏪 Retail Operations & Logistics")
    st.markdown("---")
    try:
        if supabase is not None:
            leader_res = supabase.table("daily_audits").select("store_id, created_at").order("created_at", desc=True).execute()
            if leader_res.data:
                df_leader = pd.DataFrame(leader_res.data)
                df_leader['created_at'] = pd.to_datetime(df_leader['created_at'])
                df_leader['date_only'] = df_leader['created_at'].dt.date
                df_unique_days = df_leader.drop_duplicates(subset=['store_id', 'date_only'], keep='first')
                submission_counts = df_unique_days['store_id'].value_counts()
                if not submission_counts.empty:
                    max_score = submission_counts.max()
                    top_store_ids = submission_counts[submission_counts == max_score].index.tolist()
                    champion_names = []
                    for s_id in top_store_ids:
                        store_info = supabase.table("stores").select("store_name").eq("store_id", s_id).execute()
                        champion_names.append(store_info.data[0]['store_name'] if store_info.data else f"Store {s_id}")
                    champions_display = " & ".join(champion_names)
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
    except Exception:
        pass

    st.subheader("📡 Live Store Analytics Feed")
    view_audit, view_recv, view_waste = st.tabs(["📋 Daily Audits", "📦 Receiving", "🗑️ Wastage"])
    
    with view_audit:
        try:
            if supabase is not None:
                audit_res = supabase.table("daily_audits").select("*").order("created_at", desc=True).limit(200).execute()
                if audit_res.data:
                    df_audits = pd.DataFrame(audit_res.data)
                    df_audits['created_at'] = pd.to_datetime(df_audits['created_at'])
                    df_audits['date_only'] = df_audits['created_at'].dt.date
                    df_latest_audits = df_audits.drop_duplicates(subset=['store_id', 'date_only'], keep='first').copy()
                    
                    store_name_map = {
                        "189001": "Janakpuri, Delhi", "189002": "GK1, Delhi", "189003": "Oberoi SkyCity, Mumbai",
                        "189004": "M3M Atrium, Gurgaon", "189005": "Secor 50 Noida, Noida", "189006": "Malcha, Delhi",
                        "189007": "Platina, Gurgaon", "189008": "Season Mall Pune, Pune", "189009": "BRS Nagar Ludhiana, Ludhiana",
                        "189010": "DLF Moti Nagar, Delhi", "189011": "Goldust Patiala, Patiala", "189012": "Warehouse, Delhi",
                        "189013": "Creek Side, Ludhiana", "189014": "Chembur, Mumbai"
                    }
                    df_latest_audits['store_id_str'] = df_latest_audits['store_id'].astype(str)
                    df_latest_audits['Store Name'] = df_latest_audits['store_id_str'].map(store_name_map).fillna(df_latest_audits['store_id_str'])
                    audit_counts = df_latest_audits['Store Name'].value_counts().reset_index()
                    audit_counts.columns = ['Store Name', 'Total Valid Submissions']
                    fig_audit = px.bar(audit_counts, x='Store Name', y='Total Valid Submissions', title="Valid Daily Audits by Store", text_auto=True, color='Total Valid Submissions', color_continuous_scale='Blues')
                    fig_audit.update_layout(xaxis_type='category')
                    st.plotly_chart(fig_audit, use_container_width=True)
                    
                    with st.expander("🔍 View & Download Detailed Audit Reports"):
                        df_display = df_latest_audits.copy()
                        df_display['created_at'] = df_display['created_at'].dt.strftime('%Y-%m-%d %H:%M')
                        cols_to_show = ['created_at', 'Store Name', 'manager_name', 'shift', 'admin_proof_url', 'hygiene_proof_url', 'sanitation_proof_url', 'product_proof_url', 'facility_proof_url']
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
                            use_container_width=True, hide_index=True
                        )
                        st.download_button("📥 Download Raw Audit CSV", data=df_display.to_csv(index=False).encode('utf-8'), file_name="audits.csv", mime="text/csv")
        except Exception as e:
            st.error(f"Error loading audits: {e}")

    with view_recv:
        try:
            if supabase is not None:
                recv_res = supabase.table("store_receiving_logs").select("*").order("created_at", desc=True).limit(100).execute()
                if recv_res.data:
                    df_recv = pd.DataFrame(recv_res.data)
                    fig_recv = px.scatter(df_recv, x='created_at', y='received_temp', color='store_id', title="Vendor Delivery Temperatures (°C)", size_max=10, hover_data=['vendor_name', 'invoice_number'])
                    fig_recv.add_hline(y=5.0, line_dash="dot", annotation_text="Max Acceptable Temp (5°C)", annotation_position="bottom right", line_color="red")
                    st.plotly_chart(fig_recv, use_container_width=True)
                    with st.expander("🔍 View Detailed Receiving Logs"):
                        st.dataframe(df_recv[['created_at', 'store_id', 'vendor_name', 'invoice_number', 'received_temp']], use_container_width=True, hide_index=True)
        except Exception as e:
            st.error(f"Error loading receiving logs: {e}")

    with view_waste:
        try:
            if supabase is not None:
                waste_res = supabase.table("store_wastage").select("*").order("created_at", desc=True).limit(100).execute()
                if waste_res.data:
                    df_waste = pd.DataFrame(waste_res.data)
                    waste_counts = df_waste['reason'].value_counts().reset_index()
                    waste_counts.columns = ['Reason', 'Count']
                    fig_waste = px.pie(waste_counts, names='Reason', values='Count', title="Wastage Breakdown by Reason", hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
                    st.plotly_chart(fig_waste, use_container_width=True)
                    with st.expander("🔍 View Detailed Wastage Records"):
                        st.dataframe(df_waste[['created_at', 'store_id', 'item_name', 'quantity', 'reason']], use_container_width=True, hide_index=True)
        except Exception as e:
            st.error(f"Error loading wastage logs: {e}")

    st.markdown("---")
    st.subheader("📋 Store Staff Compliance Entry")
    FULL_STORE_LIST = [
        "DLF Mid Town Plaza, Moti Nagar", "Janakpuri, Delhi", "GK1, Delhi",
        "Oberoi SkyCity, Mumbai", "M3M Atrium, Gurgaon", "Sector 50 Noida, Noida",
        "Malcha, Delhi", "Platina, Gurgaon", "Season Mall Pune, Pune", "BRS Nagar Ludhiana, Ludhiana"
    ]
    with st.expander("📝 Enter New Compliance Record", expanded=False):
        with st.form("compliance_entry_form"):
            selected_store_name = st.selectbox("Select Store Location", FULL_STORE_LIST)
            current_month_val = st.selectbox("Select Audit Month", ["August 2026", "September 2026", "October 2026", "November 2026"])
            col1, col2 = st.columns(2)
            with col1:
                input_fostac = st.number_input("FoSTaC Pending (Count)", min_value=0, step=1)
                self_audit_done = st.selectbox("Self Audit Completed?", ["Yes", "No"])
            with col2:
                input_medical = st.number_input("Medical Pending (Count)", min_value=0, step=1)
                self_audit_score = st.number_input("Self Audit Score (%)", min_value=0.0, max_value=100.0, step=0.1)
            is_compliant = st.checkbox("✅ Mark as Fully Compliant (No pending FoSTaC/Medical)")
            remark = st.text_area("Additional Remarks / Action Plan")
            if st.form_submit_button("🚀 Save Store Compliance Data", type="primary"):
                try:
                    compliance_data = {
                        "store_name": selected_store_name, "fostac_pending": input_fostac,
                        "medical_pending": input_medical, "fully_compliant": is_compliant,
                        "self_audit_done": self_audit_done, "self_audit_score": self_audit_score,
                        "remark": remark, "month_year": current_month_val
                    }
                    if supabase is not None:
                        supabase.table("store_monthly_compliance").insert(compliance_data).execute()
                        st.success(f"✅ Compliance data for {selected_store_name} successfully saved!")
                except Exception as e:
                    st.error(f"❌ Failed to save data: {e}")

    st.markdown("---")
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

elif nav_selection == "🚚 Vendor & Supply Chain":
    st.subheader(f"Vendor Audit Management — {selected_month}")
    sub_tab_view, sub_tab_create = st.tabs(["📋 Recorded Audits", "📝 New Manufacturing Audit Checklist"])
    
    with sub_tab_view:
        if not df_vendors_live.empty and 'audit_month' in df_vendors_live.columns:
            month_vendors = df_vendors_live[df_vendors_live['audit_month'] == selected_month]
            if not month_vendors.empty:
                for _, row in month_vendors.iterrows():
                    with st.expander(f"🏢 {row['vendor_name']} — Status: {row.get('status', 'N/A')} (Score: {row.get('score', 'N/A')})"):
                        st.write(f"**Category:** {row.get('category', 'N/A')}")
                        st.write(f"**Remark:** {row.get('remark', 'None')}")
                        proof = row.get('proof_url')
                        if proof and isinstance(proof, str):
                            for idx, u in enumerate([u.strip() for u in proof.split(",")]):
                                if "http" in u: st.markdown(f"🔗 [Photo Proof {idx+1}]({u})")
                        if st.button(f"🗑️ Delete Record ({row['vendor_name']})", key=f"del_v_{row.get('id', _)}"):
                            if supabase is not None:
                                supabase.table("vendor_audits").delete().eq("id", row['id']).execute()
                                st.rerun()
            else:
                st.info(f"No vendor audits for {selected_month}.")
        else:
            st.info("No vendor audit records found.")

    with sub_tab_create:
        st.markdown("### 📝 General Manufacturing Vendor Audit Tool")
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
            def render_sec(title, qlist):
                st.markdown(f"#### {title}")
                res = {}
                for q_text, pts, is_star in qlist:
                    lbl = f"⭐ {q_text} ({pts} pts)" if is_star else f"{q_text} ({pts} pts)"
                    c1, c2 = st.columns(2)
                    st_val = c1.selectbox(lbl, ["Compliance (C)", "Noncompliance (NC)", "Partial Compliance (PC)", "Not Applicable (NA)"], key=f"s_{q_text}")
                    comm = c2.text_input("Note (if NC/PC)", key=f"c_{q_text}")
                    res[q_text] = {"status": st_val, "points": pts, "is_star": is_star, "comment": comm}
                return res

            q_design = render_sec("1. Design & Facilities", [
                ("Q1: Food establishment location is away from environmental pollution", 2, False),
                ("Q2: Premises is clean, adequately lighted, and ventilated", 2, False),
                ("Q3: Walls, floors, ceilings are smooth, impervious, and easy to clean", 2, False),
                ("Q4: Windows and doors are fitted with insect and pest proof screens", 2, False),
                ("Q5: Drainage system is adequate and sloped appropriately", 2, False),
                ("Q6: Food contact surfaces are made of non-toxic, non-corrosive materials", 2, False),
                ("Q7: Adequate facilities for cleaning and disinfecting equipment", 2, False),
                ("Q8: Proper storage facilities for raw materials and finished goods", 2, False),
                ("Q9: Separate storage under lock & key for hazardous chemicals", 2, False),
                ("Q10: Adequate potable water supply available with test reports", 4, True)
            ])
            
            q_ops = render_sec("2. Control of Operation", [
                ("Q11: Raw materials purchased from approved/licensed vendors", 2, False),
                ("Q12: Raw materials inspected for quality and safety before use", 2, False),
                ("Q13: Segregation of raw and cooked food to prevent cross-contamination", 4, True),
                ("Q14: Time and temperature controls maintained during processing", 4, True),
                ("Q15: Food additives used are permitted and within legal limits", 4, True),
                ("Q16: Packaging materials are food grade and safe", 2, False),
                ("Q17: FIFO/FEFO method used for inventory rotation", 2, False),
                ("Q18: Transport vehicles are clean and maintain required temperature", 2, False),
                ("Q19: Traceability system is in place for forward and backward tracking", 2, False),
                ("Q20: Product recall procedure is documented and tested", 2, False)
            ])
            
            q_maint = render_sec("3. Maintenance & Sanitation", [
                ("Q21: Cleaning and sanitation schedule documented and followed", 2, False),
                ("Q22: Preventive maintenance program in place for machinery", 2, False),
                ("Q23: Equipment calibration records maintained", 2, False),
                ("Q24: Documented pest control program with authorized agency", 4, True),
                ("Q25: No signs of pest activity or harborages", 2, False),
                ("Q26: Waste is disposed of scientifically without attracting pests", 2, False),
                ("Q27: Drains are covered and equipped with traps", 2, False)
            ])

            q_hyg = render_sec("4. Personal Hygiene", [
                ("Q28: Annual medical examination records for all food handlers", 2, False),
                ("Q29: Daily fitness/illness screening for food handlers", 2, False),
                ("Q30: Food handlers wear clean uniforms, aprons, and hairnets", 2, False),
                ("Q31: Handwashing stations have soap, water, and drying facilities", 4, True),
                ("Q32: Strict policy against smoking, spitting, chewing in production", 2, False),
                ("Q33: Nails kept short, clean, and no jewelry worn by handlers", 2, False)
            ])
            
            q_train = render_sec("5. Training & Complaints", [
                ("Q34: At least one FOSTAC trained supervisor on premises", 4, True),
                ("Q35: Routine food safety training provided to all staff", 2, False),
                ("Q36: Documented consumer complaint handling procedure", 2, False),
                ("Q37: Corrective actions taken on complaints and documented", 2, False)
            ])

            audit_responses = {**q_design, **q_ops, **q_maint, **q_hyg, **q_train}

            audit_photos = st.file_uploader("Upload Inspection Snaps", type=["jpg", "png", "jpeg"], accept_multiple_files=True)
            audit_remarks = st.text_area("Overall Audit Remarks")

            if st.form_submit_button("Calculate Score & Submit Audit", type="primary"):
                if not audit_vendor_name:
                    st.error("❌ Vendor Name is required.")
                else:
                    photo_urls = []
                    if audit_photos and cloudinary_configured:
                        for idx, pfile in enumerate(audit_photos):
                            url = upload_photo(pfile, "vendor_audits", f"{audit_vendor_name.replace(' ', '_')}_{idx+1}")
                            if url: photo_urls.append(url)
                    earned = sum(d['points'] if d['status'] == "Compliance (C)" else (d['points']/2 if d['status'] == "Partial Compliance (PC)" else 0) for d in audit_responses.values())
                    max_pts = sum(d['points'] for d in audit_responses.values()) if audit_responses else 90
                    pct = (earned / max_pts) * 100 if max_pts > 0 else 0
                    grade = "A+ (Exemplar)" if pct >= 80 else ("A (Satisfactory)" if pct >= 72 else ("B (Needs Improvement)" if pct >= 45 else "Non Compliance"))
                    status_res = "Passed" if pct >= 72 else ("Conditionally Approved" if pct >= 45 else "Failed")
                    payload = {
                        "vendor_name": audit_vendor_name, "category": "General Manufacturing",
                        "score": f"{pct:.1f}% ({earned}/{max_pts} - Grade: {grade})",
                        "status": status_res,
                        "remark": f"Auditor: {audit_fso} | License: {audit_lic_no} | Date: {audit_date.strftime('%d-%b-%Y')} | Remarks: {audit_remarks}",
                        "audit_month": selected_month, "proof_url": ", ".join(photo_urls) if photo_urls else None
                    }
                    if supabase is not None:
                        supabase.table("vendor_audits").insert(payload).execute()
                        pdf_bytes = generate_detailed_checklist_pdf(audit_vendor_name, audit_fso, audit_lic_no, audit_address, audit_date, audit_responses, pct, grade, audit_remarks, payload["proof_url"])
                        st.session_state['latest_generated_audit_pdf'] = {"name": audit_vendor_name, "data": pdf_bytes}
                        st.success(f"✅ Audit Completed! Score: {pct:.1f}% | Grade: {grade}")

        if 'latest_generated_audit_pdf' in st.session_state:
            latest = st.session_state['latest_generated_audit_pdf']
            st.download_button(label=f"📥 Download Itemized PDF Report ({latest['name']})", data=latest['data'], file_name=f"Audit_{latest['name']}.pdf", mime="application/pdf", type="primary")

elif nav_selection == "📜 License Summary":
    st.subheader("📜 License Compliance Summary & Digital Vault")
    df_lic = pd.DataFrame()
    try:
        if supabase is not None:
            resp = supabase.table("license_tracker").select("*").execute()
            if resp.data:
                df_lic = pd.DataFrame(resp.data)[['s_no', 'location', 'city', 'fssai', 'trade', 'fire', 'pollution_cto', 'signage', 'remark']]
                df_lic.columns = ['S.no', 'Location', 'City', 'FSSAI', 'Trade', 'Fire', 'Pollution CTO', 'Signage', 'Remark']
    except Exception as e:
        st.error(f"Could not fetch license data: {e}")

    if df_lic.empty:
        st.info("📂 No license data found in cloud database.")
    else:
        st.metric("🏢 Total Tracked Facilities", f"{len(df_lic)} Stores")
        st.markdown("---")
        for _, row in df_lic.iterrows():
            with st.expander(f"📍 {row['Location']} ({row['City']})"):
                cols = st.columns(5)
                for idx, c in enumerate(['FSSAI', 'Trade', 'Fire', 'Pollution CTO', 'Signage']):
                    cols[idx].metric(c, str(row[c])[:10] if pd.notna(row[c]) else "N/A")
                if pd.notna(row['Remark']) and str(row['Remark']).strip() not in ['nan', 'none', '']:
                    st.warning(f"⚠️ **Remarks:** {row['Remark']}")

    st.markdown("---")
    st.markdown("### 📂 Permanent Cloud License Excel Sync")
    up_lic = st.file_uploader("Upload Master License Tracker Excel", type=["xlsx", "xls"], key="cloud_lic_up")
    if up_lic and st.button("🚀 Sync Permanently to Cloud Database", type="primary"):
        try:
            df_up = pd.read_excel(up_lic).iloc[1:].reset_index(drop=True)
            df_up.columns = ['s_no', 'location', 'city', 'fssai', 'trade', 'fire', 'pollution_cto', 'signage', 'remark']
            for c in ['fssai', 'trade', 'fire', 'pollution_cto', 'signage']:
                if c in df_up.columns: df_up[c] = pd.to_datetime(df_up[c], errors='coerce').dt.strftime('%Y-%m-%d')
            clean_recs = []
            for r in df_up.astype(str).to_dict(orient="records"):
                clean_recs.append({k: (None if pd.isna(v) or v.lower() in ['nan', 'nat', 'none', ''] else v.strip()) for k, v in r.items()})
            if supabase is not None:
                supabase.table("license_tracker").delete().neq("id", 0).execute()
                supabase.table("license_tracker").insert(clean_recs).execute()
                st.success("✅ Synced license tracker!")
                st.rerun()
        except Exception as e:
            st.error(f"Sync failed: {e}")

elif nav_selection == "📈 NSF Audit Intelligence":
    st.subheader("📈 NSF Audit Intelligence & Network Performance")
    upload_tab, manual_tab = st.tabs(["📂 Upload Master Summary Report", "✍️ Log Individual Store Score"])
    with upload_tab:
        summary_file = st.file_uploader("Upload Master Summary Report (Excel / CSV)", type=["xlsx", "csv"])
        if summary_file and st.button("📤 Parse & Sync Master Report", type="primary"):
            try:
                df_summary = pd.read_csv(summary_file) if summary_file.name.endswith('.csv') else pd.read_excel(summary_file)
                df_summary.columns = [str(c).strip().lower() for c in df_summary.columns]
                succ = 0
                if supabase is not None:
                    for _, row in df_summary.iterrows():
                        payload = {
                            "audit_code": str(row.get('audit_code', row.get('audit code', ''))),
                            "site_code": str(row.get('site_code', row.get('site code', ''))),
                            "store_name": str(row.get('store_name', row.get('site name', ''))),
                            "score": float(row.get('score', 0)),
                            "result": str(row.get('result', '')),
                            "audit_date": str(row.get('audit_date', row.get('audit date', datetime.date.today()))),
                            "car_status": str(row.get('car_status', row.get('car status', ''))),
                            "remarks": "Bulk uploaded from summary sheet"
                        }
                        if not payload["site_code"] or payload["site_code"] == "nan": continue
                        supabase.table("nsf_audits").upsert(payload).execute()
                        succ += 1
                    st.success(f"✅ Synced {succ} records!")
                    st.rerun()
            except Exception as e:
                st.error(f"Sync error: {e}")

    with manual_tab:
        with st.form("single_store_form"):
            col_n1, col_n2 = st.columns(2)
            with col_n1:
                acode = st.text_input("NSF Audit Code")
                store_opt = ["189001 - Janakpuri, Delhi", "189002 - GK1, Delhi", "189003 - Oberoi SkyCity, Mumbai", "189004 - M3M Atrium, Gurgaon", "189005 - Secor 50 Noida, Noida", "189006 - Malcha, Delhi", "189007 - Platina, Gurgaon", "189008 - Season Mall Pune, Pune", "189009 - BRS Nagar Ludhiana, Ludhiana", "189010 - DLF Moti Nagar, Delhi", "189011 - Goldust Patiala, Patiala", "189012 - Neelkanth - Murthal", "189013 - Creek Side, Ludhiana", "189014 - Chembur, Mumbai"]
                sel_store = st.selectbox("Select Store", store_opt)
                sc_val = st.number_input("Score (%)", 0.0, 100.0, 85.0)
            with col_n2:
                adt = st.date_input("Audit Date", value=datetime.date.today())
                ares = st.selectbox("Result", ["PASS", "FAIL"])
                arem = st.text_area("Remarks")
            if st.form_submit_button("🚀 Sync Store Record", type="primary") and acode.strip():
                if supabase is not None:
                    supabase.table("nsf_audits").insert({
                        "audit_code": acode.strip(), "site_code": sel_store.split(" - ")[0],
                        "store_name": sel_store.split(" - "), "score": sc_val, "result": ares,
                        "audit_date": str(adt), "remarks": arem
                    }).execute()
                    st.success("Synced record!")
                    st.rerun()

    st.markdown("---")
    st.markdown("### 📊 Performance by Ownership Type")
    if not df_db.empty and 'score' in df_db.columns and 'Type' in df_db.columns:
        c1, c2 = st.columns(2)
        with c1:
            avg_scores = df_db.groupby('Type')['score'].mean().reset_index()
            fig_avg = px.bar(avg_scores, x='Type', y='score', color='Type', text='score', title="Average Score (%) by Ownership")
            fig_avg.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
            st.plotly_chart(fig_avg, use_container_width=True)
        with c2:
            st_col = 'result' if 'result' in df_db.columns else 'status' if 'status' in df_db.columns else None
            if st_col:
                res_dist = df_db.groupby(['Type', st_col]).size().reset_index(name='Count')
                fig_dist = px.bar(res_dist, x='Type', y='Count', color=st_col, barmode='group', text='Count', title="Audit Status Distribution")
                st.plotly_chart(fig_dist, use_container_width=True)

    st.markdown("---")
    st.markdown("### 🚨 Corrective Action Request (CAR) Pending Tracker")
    st.caption("Monitoring stores with outstanding Corrective Actions and calculating delay days since audit generation.")
    if not df_db.empty:
        car_col = 'car_status' if 'car_status' in df_db.columns else 'CAR Status' if 'CAR Status' in df_db.columns else None
        date_col = 'audit_date' if 'audit_date' in df_db.columns else 'Audit Date' if 'Audit Date' in df_db.columns else None
        if car_col and date_col:
            df_car = df_db.copy()
            df_car[date_col] = pd.to_datetime(df_car[date_col], errors='coerce')
            df_car['Days_Elapsed'] = (pd.Timestamp(datetime.date.today()) - df_car[date_col]).dt.days
            df_pending = df_car[df_car[car_col].astype(str).str.contains("PENDING", case=False, na=False)].sort_values(by='Days_Elapsed', ascending=False)
            if not df_pending.empty:
                st.warning(f"⚠️ There are **{len(df_pending)}** audit records across the network with pending Corrective Actions.")
                st.dataframe(df_pending[['store_name', date_col, 'score', car_col, 'Days_Elapsed']], use_container_width=True, hide_index=True)
            else:
                st.success("🎉 All network audits have approved Corrective Actions.")
        else:
            st.info("CAR status tracking columns not detected in current data feed.")

elif nav_selection == "📑 Reports & Archive":
    st.subheader("📑 Executive PDF Report Generation")
    if st.button("Generate Executive PDF Report", type="primary") and FPDF:
        v_data = st.session_state.get('vendor_db', {}).get(selected_month, [])
        pdf_bytes = generate_pdf(selected_month, monthly_records, v_data, df_db)
        if pdf_bytes:
            st.session_state['pdf_archive'][selected_month] = pdf_bytes
            st.success("✅ Executive PDF generated successfully!")
    if selected_month in st.session_state['pdf_archive']:
        st.download_button("📥 Download Executive PDF Report", data=st.session_state['pdf_archive'][selected_month], file_name=f"CBTL_Executive_Report_{selected_month}.pdf", mime="application/pdf")

elif nav_selection == "📚 Resources Vault":
    st.subheader("📚 Central Resources & Document Management")
    
    pub_scope = st.radio("Publication Scope", ["Global (All Stores)", "Specific Outlet (Water Test, Pest Map, etc.)"], horizontal=True)
    
    target_store_val = "ALL"
    if pub_scope == "Specific Outlet (Water Test, Pest Map, etc.)":
        store_names_list = df_stores['name'].tolist() if not df_stores.empty else ["Janakpuri, Delhi"]
        target_store_val = st.selectbox("Select Target Outlet", store_names_list)

    with st.form("upload_master_resource", clear_on_submit=True):
        cat = st.selectbox("Category", [
            "QA SOPs & Safety", "Menu & Nutrition Booklet", "Shelf Life Chart", 
            "Chemical Info Sheet", "Water Test Report", "Pest Control Layout / Map"
        ])
        dfile = st.file_uploader("Upload Document (PDF, JPG, PNG)", type=["pdf", "jpg", "jpeg", "png"])
        btn_label = f"🚀 Publish to {target_store_val if target_store_val != 'ALL' else 'All Stores'}"
        
        if st.form_submit_button(btn_label, type="primary") and dfile and cloudinary_configured:
            folder_scope = target_store_val.replace(' ', '_') if target_store_val != 'ALL' else "global"
            folder_path = f"cbtl/central_resources/{folder_scope}"
            ures = cloudinary.uploader.upload(dfile, folder=folder_path, resource_type="auto")
            
            if supabase is not None:
                supabase.table("central_resources").insert({
                    "category": cat, 
                    "file_name": dfile.name, 
                    "file_url": ures.get("secure_url", ""), 
                    "updated_at": str(datetime.date.today()),
                    "target_store": target_store_val
                }).execute()
                st.success(f"✅ Published `{dv if 'dv' in locals() else dfile.name}` for **{target_store_val}**!")
                st.rerun()

    if supabase is not None:
        rquery = supabase.table("central_resources").select("*").order("updated_at", desc=True).execute()
        if rquery.data:
            df_res = pd.DataFrame(rquery.data)
            if 'target_store' not in df_res.columns:
                df_res['target_store'] = 'ALL'
                
            filter_view = st.selectbox("Filter Vault View", ["All Records", "Global Only", "Outlet Specific Only"])
            if filter_view == "Global Only":
                df_res = df_res[df_res['target_store'] == 'ALL']
            elif filter_view == "Outlet Specific Only":
                df_res = df_res[df_res['target_store'] != 'ALL']
                
            st.dataframe(
                df_res[['category', 'target_store', 'file_name', 'updated_at', 'file_url']],
                column_config={
                    "target_store": st.column_config.TextColumn("Scope / Outlet"),
                    "file_url": st.column_config.LinkColumn("Document", display_text="🔗 Open")
                },
                width='stretch', hide_index=True
            )
        else:
            st.info("No documents published in vault yet.")

elif nav_selection == "💳 Finance Invoices":
    st.subheader("💳 Central Invoices & Finance Clearance")
    with st.expander("➕ Add New Central Invoice"):
        with st.form("cent_inv"):
            ic = st.selectbox("Category", ["Medical (Health Certs)", "Pest Control", "FOSTAC (Training)", "Liasoning / Licensing", "Utilities & Maintenance", "Other"])
            vn = st.text_input("Vendor Name")
            inumb = st.text_input("Invoice Number")
            iamt = st.number_input("Amount (INR)", 0.0, step=100.0)
            ifile = st.file_uploader("Upload Doc", type=["pdf", "jpg", "jpeg", "png"])
            irem = st.text_area("Remarks")
            if st.form_submit_button("Submit to Ledger", type="primary") and vn and inumb:
                iurl = ""
                if ifile and cloudinary_configured:
                    iurl = cloudinary.uploader.upload(ifile, folder="cbtl/central_finance_invoices", resource_type="auto").get("secure_url", "")
                if supabase is not None:
                    supabase.table("central_finance_invoices").insert({"invoice_category": ic, "vendor_name": vn, "invoice_number": inumb, "invoice_amount": iamt, "invoice_url": iurl, "remarks": irem, "submitted_to_finance": False, "payment_done": False}).execute()
                    st.success("Logged invoice!")
                    st.rerun()
    if supabase is not None:
        inv_res = supabase.table("central_finance_invoices").select("*").order("created_at", desc=True).execute()
        if inv_res.data:
            st.dataframe(pd.DataFrame(inv_res.data), use_container_width=True)

elif nav_selection == "⚙️ System Administration":
    st.subheader("⚙️ Store Portfolio & System Administration")
    with st.expander("➕ Add a New Store Location"):
        with st.form("new_store"):
            nn = st.text_input("Store Name")
            isout = st.checkbox("Is Outstation?")
            if st.form_submit_button("Add Store") and nn:
                st.session_state['master_stores'].append({'name': nn, 'is_outstation': isout})
                st.success("Added store!")
                st.rerun()

    st.markdown("### 📦 Supply Chain Terminology Unification Management")
    try:
        if supabase is not None:
            response = supabase.table("master_item_reference").select("*").order("id").execute()
            if response.data:
                df_items = pd.DataFrame(response.data)
                total_items = len(df_items)
                unified_items = df_items['is_name_unified'].sum()
                completion_rate = (unified_items / total_items) if total_items > 0 else 0
                st.progress(completion_rate, text=f"Overall Unification Progress: {int(unified_items)} out of {total_items} items unified.")
                edited_df = st.data_editor(
                    df_items[['id', 'warehouse_item_name', 'store_retail_name', 'item_category', 'is_name_unified']],
                    width='stretch', hide_index=True,
                    disabled=['id', 'warehouse_item_name', 'store_retail_name', 'item_category'],
                    column_config={
                        "id": None, "warehouse_item_name": st.column_config.TextColumn("Current Invoice Name"),
                        "store_retail_name": st.column_config.TextColumn("Target Retail Name"),
                        "item_category": st.column_config.TextColumn("Category"),
                        "is_name_unified": st.column_config.CheckboxColumn("Unified?", default=False)
                    }, key="unification_tracker"
                )
                if st.button("💾 Save Compliance Updates", type="primary"):
                    updates_made = 0
                    for index, row in edited_df.iterrows():
                        if df_items.loc[index, 'is_name_unified'] != row['is_name_unified']:
                            supabase.table("master_item_reference").update({"is_name_unified": row['is_name_unified']}).eq("id", row['id']).execute()
                            updates_made += 1
                    if updates_made > 0:
                        st.success(f"✅ Updated {updates_made} records.")
                        st.rerun()
    except Exception as e:
        st.error(f"Failed to load terminology data: {e}")

    st.markdown("### 💬 Store Feedback & Support Tickets")
    if supabase is not None:
        fb_res = supabase.table("store_feedback").select("*").order("created_at", desc=True).execute()
        if fb_res.data:
            df_fb = pd.DataFrame(fb_res.data)
            for idx, r in df_fb.iterrows():
                col_text, col_btn = st.columns([3, 1])  # adjust ratio/count as needed
                date_str = str(r.get('created_at', 'N/A'))[:10]
                store_val = r.get('store_id', r.get('store_name', 'N/A'))
                msg_val = r.get('feedback_text', r.get('message', 'No text'))
                
                col_text.markdown(f"**[{date_str}] Store {store_val}**: {msg_val}")
                if col_btn.button("🗑️ Delete", key=f"del_fb_{r.get('id', idx)}"):
                    supabase.table("store_feedback").delete().eq("id", r['id']).execute()
                    st.success("✅ Ticket deleted!")
                    st.rerun()
        else:
            st.info("No store feedback yet.")            
elif nav_selection == "🤖 AI Support Assistant":
    st.subheader("🤖 Ekaagra QA & Compliance Intelligence Engine")
    st.caption("Powered by Gemini • Multi-Module Live Context + FSSAI Operational Guidance")

    # 1. API Key Setup
    gemini_ready = False
    if "GEMINI_API_KEY" in st.secrets and st.secrets["GEMINI_API_KEY"].strip():
        try:
            genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
            gemini_ready = True
        except Exception as e:
            st.error(f"Failed to configure Gemini API: {e}")
    else:
        st.warning("⚠️ `GEMINI_API_KEY` not detected in Streamlit Secrets. Please configure `.streamlit/secrets.toml`.")

    # 2. Session Chat History Initialization
    if "support_messages" not in st.session_state:
        st.session_state["support_messages"] = [
            {"role": "assistant", "content": "Hello! I am your QA & Compliance Assistant. Ask me anything across NSF audits, daily store FSSAI logs, vendor audits, support tickets, or general FSSAI guidelines."}
        ]

    for msg in st.session_state["support_messages"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # 3. Handle Prompt Input
    if prompt := st.chat_input("Ask a question across any operational module or compliance policy..."):
        st.session_state["support_messages"].append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            if not gemini_ready:
                reply = "⚠️ API Key is missing. Please check your Streamlit secrets."
                st.markdown(reply)
                st.session_state["support_messages"].append({"role": "assistant", "content": reply})
            else:
                with st.spinner("Analyzing operational database across all modules..."):
                    try:
                        # --- FULL MULTI-MODULE SUPABASE EXTRACTION ---
                        res_s = supabase.table("store_master").select("*").execute() if supabase else None
                        df_stores = pd.DataFrame(res_s.data) if res_s and res_s.data else pd.DataFrame()

                        res_n = supabase.table("nsf_audits").select("*").order("audit_date", desc=True).limit(40).execute() if supabase else None
                        df_nsf = pd.DataFrame(res_n.data) if res_n and res_n.data else pd.DataFrame()

                        res_f = supabase.table("store_feedback").select("*").order("created_at", desc=True).limit(20).execute() if supabase else None
                        df_fb = pd.DataFrame(res_f.data) if res_f and res_f.data else pd.DataFrame()

                        res_d = supabase.table("daily_audits").select("*").order("created_at", desc=True).limit(30).execute() if supabase else None
                        df_daily = pd.DataFrame(res_d.data) if res_d and res_d.data else pd.DataFrame()

                        res_v = supabase.table("vendor_audits").select("*").order("created_at", desc=True).limit(20).execute() if supabase else None
                        df_vendor = pd.DataFrame(res_v.data) if res_v and res_v.data else pd.DataFrame()

                        # --- SAFE CONDENSE DATASETS FOR GEMINI ---
                        def safe_to_string(df, preferred_cols, fallback_text="None"):
                            if df.empty:
                                return fallback_text
                            existing_cols = [c for c in preferred_cols if c in df.columns]
                            if existing_cols:
                                return df[existing_cols].to_string(index=False)
                            return df.to_string(index=False)

                        summary_stores = safe_to_string(df_stores, ['site_code', 'store_name', 'ownership_type'], "No store master records.")
                        summary_nsf = safe_to_string(df_nsf, ['site_code', 'store_name', 'score', 'result', 'car_status', 'audit_date'], "No NSF audit records.")
                        summary_fb = safe_to_string(df_fb, ['store_id', 'feedback_text', 'created_at'], "No store feedback tickets.")
                        summary_daily = safe_to_string(df_daily, ['store_id', 'store_name', 'audit_date', 'date', 'compliance_score', 'score', 'status', 'created_at'], "No daily store FSSAI records.")
                        summary_vendor = safe_to_string(df_vendor, ['vendor_name', 'score', 'grade', 'audit_date', 'created_at'], "No vendor audit records.")

                        # --- SYSTEM PROMPT ---
                        system_prompt = f"""
                        You are the Senior QA & Compliance AI Officer for CBTL India / Ekaagra Retail Operations.
                        
                        === FULL APPLICATION LIVE DATASETS ===
                        
                        [STORE MASTER PORTFOLIO]
                        {summary_stores}
                        
                        [NSF QUARTERLY AUDIT RECORDS]
                        {summary_nsf}
                        
                        [DAILY STORE FSSAI LOGS]
                        {summary_daily}
                        
                        [VENDOR & SUPPLY CHAIN AUDITS]
                        {summary_vendor}
                        
                        [STORE FEEDBACK & SUPPORT TICKETS]
                        {summary_fb}
                        
                        === OPERATIONAL & COMPLIANCE RULES ===
                        1. CLASSIFICATION: Site codes starting with '189' (or '1891...') are 'Ekaagra Direct Outlets'. All other codes are 'Sub Franchise Outlets'.
                        2. INTERNAL DATA GUARDRALL: Prioritize the provided tables above for internal company metrics, store performance, daily checklists, vendor scores, and support tickets. Never invent internal metrics.
                        3. HYBRID KNOWLEDGE RULE: For questions regarding general food safety standards, FSSAI regulations, FoSTaC guidelines, temp/FIFO controls, or hygiene SOPs, utilize general QA/FSSAI industry knowledge to provide practical advice.
                        4. STRUCTURE: Keep responses clear, professional, and well-structured with bullet points and bold headers.
                        """

                        # --- FAILOVER MODEL SELECTION LOOP ---
                        model_candidates = [
                            "models/gemini-3.8-flash",
                            "gemini-3.8-flash",
                            "models/gemini-1.5-flash",
                            "gemini-1.5-flash",
                            "models/gemini-1.5-pro"
                        ]

                        reply = None
                        last_exception = None

                        for target_model in model_candidates:
                            try:
                                model = genai.GenerativeModel(
                                    model_name=target_model,
                                    generation_config={"temperature": 0.2}
                                )
                                response = model.generate_content([system_prompt, f"User Question: {prompt}"])
                                if response and response.text:
                                    reply = response.text
                                    break
                            except Exception as model_err:
                                last_exception = model_err
                                continue

                        if not reply:
                            if last_exception and "429" in str(last_exception):
                                reply = "⚠️ **Rate limit reached**. Please wait a moment before sending another query."
                            else:
                                reply = f"Error processing query: {last_exception}"

                        # --- AUTOMATIC LOGGING TO SUPABASE CHAT_LOGS ---
                        if supabase is not None and reply and not reply.startswith("Error"):
                            try:
                                supabase.table("chat_logs").insert({
                                    "user_prompt": prompt,
                                    "ai_response": reply
                                }).execute()
                            except Exception:
                                pass

                    except Exception as e:
                        reply = f"Error processing query: {e}"

                    st.markdown(reply)
                    st.session_state["support_messages"].append({"role": "assistant", "content": reply})
