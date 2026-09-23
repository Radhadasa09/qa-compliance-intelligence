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

try:
    from fpdf import FPDF
except ImportError:
    FPDF = None

try:
    from google import genai
except ImportError:
    genai = None

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
        header {visibility: hidden;}
        footer {visibility: hidden;}
        
        div[data-testid="stToolbar"] {display: none !important;}
        div[data-testid="stStatusWidget"] {display: none !important;}
        .stDeployButton {display: none !important;}
        
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
""", unsafe_allow_html=True)

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

if not df_db.empty and 'site_code' in df_db.columns:
    df_db['site_code'] = df_db['site_code'].astype(str)
    df_db['Type'] = df_db['site_code'].apply(lambda x: "Ekaagra Direct" if x.startswith("189") else "Sub Franchise")
    ekaagra_df = df_db[df_db['Type'] == "Ekaagra Direct"]
    subfranchise_df = df_db[df_db['Type'] == "Sub Franchise"]
else:
    ekaagra_df = pd.DataFrame()
    subfranchise_df = pd.DataFrame()

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

with st.sidebar:
    st.markdown("### 🛡️ CBTL India Command")
    st.caption("Ekaagra Master Franchise • QA Hub")
    selected_month = st.selectbox("Global Period Filter", ["Live Data", "August 2026", "September 2026", "October 2026"])
    st.markdown("---")
    nav_selection = st.radio(
        "Navigation",
        [
            "📊 Executive Dashboard", "🏬 Retail Operations", "🚚 Vendor & Supply Chain",
            "📜 License Summary", "📈 NSF Audit Intelligence", "📑 Reports & Archive",
            "📚 Resources Vault", "💳 Finance Invoices", "⚙️ System Administration", "🤖 AI Support Assistant"
        ],
        label_visibility="collapsed"
    )
    st.markdown("---")
    st.caption("Admin: Girish Kumar | v2.4 Live")

monthly_records = []
for idx, row in df_stores.iterrows():
    s_name = row['name']
    m_data = get_store_monthly(s_name, "Live Data")
    is_comp = (m_data['fostac_pending'] == 0) and (m_data['medical_pending'] == 0)
    lics = m_data['licenses']
    any_lic_issue = any(l_val['applicable'] and l_val['status'] != 'Valid' for l_val in lics.values())
    monthly_records.append({
        'name': s_name, 'is_outstation': row['is_outstation'], 'month': "Live Data",
        'fostac_pending': m_data['fostac_pending'], 'medical_pending': m_data['medical_pending'],
        'is_compliant': is_comp, 'nsf_score': m_data['nsf_score'], 'self_audit_done': m_data['self_audit_done'],
        'self_audit_score': m_data['self_audit_score'], 'remark': m_data['remark'],
        'has_license_issue': any_lic_issue, 'licenses': lics
    })
df_monthly_filtered = pd.DataFrame(monthly_records)

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
    for record in records:
        pdf.cell(200, 5, txt=f" - {record.get('name')} | Compliant: {'Yes' if record.get('is_compliant') else 'No'}", ln=1, align='L')
    pdf.ln(4)
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
    try:
        return bytes(pdf.output())
    except TypeError:
        return pdf.output(dest='S').encode('latin-1')

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
    if not ekaagra_df.empty and 'score' in ekaagra_df.columns and 'store_name' in ekaagra_df.columns:
        st.markdown("### 🏬 Ekaagra Direct Operations (189 Series)")
        fig_nsf = px.bar(ekaagra_df, x='store_name', y='score', text='score', title="Ekaagra Direct Outlets NSF Scores", color='result', color_discrete_map={'PASS': '#10B981', 'FAIL': '#EF4444'})
        fig_nsf.update_traces(textposition='outside')
        st.plotly_chart(fig_nsf, use_container_width=True)

elif nav_selection == "🏬 Retail Operations":
    st.header("🏪 Retail Operations & Logistics")
    st.subheader("📡 Live Store Analytics Feed")
    st.info("Retail operations view ready.")

elif nav_selection == "🚚 Vendor & Supply Chain":
    st.subheader(f"Vendor Audit Management — {selected_month}")
    st.info("Vendor supply chain module active.")

elif nav_selection == "📜 License Summary":
    st.subheader("📜 License Compliance Summary & Digital Vault")
    st.info("License module active.")

elif nav_selection == "📈 NSF Audit Intelligence":
    st.subheader("📈 NSF Audit Intelligence & Network Performance")
    if not df_db.empty:
        st.markdown("### 🚨 Corrective Action Request (CAR) Pending Tracker")
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

elif nav_selection == "📑 Reports & Archive":
    st.subheader("📑 Executive PDF Report Generation")

elif nav_selection == "📚 Resources Vault":
    st.subheader("📚 Central Resources & Document Management")

elif nav_selection == "💳 Finance Invoices":
    st.subheader("💳 Central Invoices & Finance Clearance")

elif nav_selection == "⚙️ System Administration":
    st.subheader("⚙️ Store Portfolio & System Administration")

elif nav_selection == "🤖 AI Support Assistant":
    st.subheader("🤖 QA & Compliance Support Assistant (Strict Supabase Grounding)")
    if "support_messages" not in st.session_state:
        st.session_state["support_messages"] = [{"role": "model", "content": "Hello! Ask me about specific store audit scores, CAR delay metrics, or vault SOP references from Supabase."}]
    for msg in st.session_state["support_messages"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
    if prompt := st.chat_input("Ask a grounded compliance question..."):
        st.session_state["support_messages"].append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)
