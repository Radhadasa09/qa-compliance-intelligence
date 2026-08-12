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
st.subheader("NSF Audit Upload")

uploaded_file = st.file_uploader(
"Upload NSF Audit CSV",
type=["csv"]
)
 
if uploaded_file:
 
df = pd.read_csv(uploaded_file)
 
st.write(df.head())
 
if st.button("Upload to Supabase"):
 
records = df.to_dict(orient="records")
 
supabase.table("nsf_audits").insert(records).execute()
 
st.success(
f"{len(records)} records uploaded successfully"
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

# --- 2. DATA LOADING & SAMPLE INITIALIZATION (14 Outlets from Image) ---
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

# July 2026 Database pre-populated with exact license tracker data
if 'monthly_db' not in st.session_state:
    st.session_state['monthly_db'] = {
        ("Janakpuri, Delhi", "July 2026"): {
            "fostac_pending": 0, "medical_pending": 0, "nsf_score": 94,
            "self_audit_done": "Yes", "self_audit_score": 92, "remark": "All licenses valid.",
            "licenses": {
                "FSSAI": {"applicable": True, "status": "Valid", "expiry": datetime.date(2028, 2, 5)},
                "Trade License": {"applicable": True, "status": "Valid", "expiry": datetime.date(2028, 3, 31)},
                "Fire NOC": {"applicable": True, "status": "Valid", "expiry": datetime.date(2028, 7, 24)},
                "Pollution CTO": {"applicable": True, "status": "Valid", "expiry": datetime.date(2035, 4, 22)},
                "Signage License": {"applicable": False, "status": "N/A", "expiry": datetime.date(2027, 1, 1)}
            }
        },
        ("GK1, Delhi", "July 2026"): {
            "fostac_pending": 0, "medical_pending": 0, "nsf_score": 92,
            "self_audit_done": "Yes", "self_audit_score": 90, "remark": "Clean audit.",
            "licenses": {
                "FSSAI": {"applicable": True, "status": "Valid", "expiry": datetime.date(2028, 3, 11)},
                "Trade License": {"applicable": True, "status": "Valid", "expiry": datetime.date(2028, 3, 31)},
                "Fire NOC": {"applicable": False, "status": "N/A", "expiry": datetime.date(2027, 1, 1)},
                "Pollution CTO": {"applicable": True, "status": "Valid", "expiry": datetime.date(2035, 4, 14)},
                "Signage License": {"applicable": False, "status": "N/A", "expiry": datetime.date(2027, 1, 1)}
            }
        },
        ("Oberoi SkyCity, Mumbai", "July 2026"): {
            "fostac_pending": 0, "medical_pending": 0, "nsf_score": 95,
            "self_audit_done": "Yes", "self_audit_score": 94, "remark": "All operational.",
            "licenses": {
                "FSSAI": {"applicable": True, "status": "Valid", "expiry": datetime.date(2027, 6, 21)},
                "Trade License": {"applicable": True, "status": "Valid", "expiry": datetime.date(2027, 6, 20)},
                "Fire NOC": {"applicable": False, "status": "N/A", "expiry": datetime.date(2027, 1, 1)},
                "Pollution CTO": {"applicable": False, "status": "N/A", "expiry": datetime.date(2027, 1, 1)},
                "Signage License": {"applicable": True, "status": "Valid", "expiry": datetime.date(2027, 7, 13)}
            }
        },
        ("M3M Atrium, Gurgoan", "July 2026"): {
            "fostac_pending": 1, "medical_pending": 0, "nsf_score": 89,
            "self_audit_done": "Yes", "self_audit_score": 88, "remark": "Trade/Fire/Pollution/Signage NA.",
            "licenses": {
                "FSSAI": {"applicable": True, "status": "Valid", "expiry": datetime.date(2028, 8, 24)},
                "Trade License": {"applicable": False, "status": "N/A", "expiry": datetime.date(2027, 1, 1)},
                "Fire NOC": {"applicable": False, "status": "N/A", "expiry": datetime.date(2027, 1, 1)},
                "Pollution CTO": {"applicable": False, "status": "N/A", "expiry": datetime.date(2027, 1, 1)},
                "Signage License": {"applicable": False, "status": "N/A", "expiry": datetime.date(2027, 1, 1)}
            }
        },
        ("Secor 50 Noida, Noida", "July 2026"): {
            "fostac_pending": 0, "medical_pending": 0, "nsf_score": 91,
            "self_audit_done": "Yes", "self_audit_score": 90, "remark": "FSSAI valid up to 2030.",
            "licenses": {
                "FSSAI": {"applicable": True, "status": "Valid", "expiry": datetime.date(2030, 7, 20)},
                "Trade License": {"applicable": False, "status": "N/A", "expiry": datetime.date(2027, 1, 1)},
                "Fire NOC": {"applicable": False, "status": "N/A", "expiry": datetime.date(2027, 1, 1)},
                "Pollution CTO": {"applicable": False, "status": "N/A", "expiry": datetime.date(2027, 1, 1)},
                "Signage License": {"applicable": False, "status": "N/A", "expiry": datetime.date(2027, 1, 1)}
            }
        },
        ("Malcha, Delhi", "July 2026"): {
            "fostac_pending": 0, "medical_pending": 1, "nsf_score": 88,
            "self_audit_done": "Yes", "self_audit_score": 87, "remark": "Trade License Under Process; Fire part of Trade.",
            "licenses": {
                "FSSAI": {"applicable": True, "status": "Valid", "expiry": datetime.date(2028, 7, 29)},
                "Trade License": {"applicable": True, "status": "Applied/Pending", "expiry": datetime.date(2027, 1, 1)},
                "Fire NOC": {"applicable": False, "status": "N/A", "expiry": datetime.date(2027, 1, 1)},
                "Pollution CTO": {"applicable": True, "status": "Valid", "expiry": datetime.date(2027, 3, 28)},
                "Signage License": {"applicable": False, "status": "N/A", "expiry": datetime.date(2027, 1, 1)}
            }
        },
        ("Platina, Gurgoan", "July 2026"): {
            "fostac_pending": 0, "medical_pending": 0, "nsf_score": 93,
            "self_audit_done": "Yes", "self_audit_score": 91, "remark": "FSSAI valid.",
            "licenses": {
                "FSSAI": {"applicable": True, "status": "Valid", "expiry": datetime.date(2028, 9, 3)},
                "Trade License": {"applicable": False, "status": "N/A", "expiry": datetime.date(2027, 1, 1)},
                "Fire NOC": {"applicable": False, "status": "N/A", "expiry": datetime.date(2027, 1, 1)},
                "Pollution CTO": {"applicable": False, "status": "N/A", "expiry": datetime.date(2027, 1, 1)},
                "Signage License": {"applicable": False, "status": "N/A", "expiry": datetime.date(2027, 1, 1)}
            }
        },
        ("Season Mall Pune, Pune", "July 2026"): {
            "fostac_pending": 0, "medical_pending": 0, "nsf_score": 90,
            "self_audit_done": "Yes", "self_audit_score": 89, "remark": "Trade license valid.",
            "licenses": {
                "FSSAI": {"applicable": True, "status": "Valid", "expiry": datetime.date(2027, 12, 3)},
                "Trade License": {"applicable": True, "status": "Valid", "expiry": datetime.date(2026, 12, 3)},
                "Fire NOC": {"applicable": False, "status": "N/A", "expiry": datetime.date(2027, 1, 1)},
                "Pollution CTO": {"applicable": False, "status": "N/A", "expiry": datetime.date(2027, 1, 1)},
                "Signage License": {"applicable": False, "status": "N/A", "expiry": datetime.date(2027, 1, 1)}
            }
        },
        ("BRS Nagar Ludhiana, Ludhiana", "July 2026"): {
            "fostac_pending": 0, "medical_pending": 0, "nsf_score": 92,
            "self_audit_done": "Yes", "self_audit_score": 90, "remark": "FSSAI valid to 2031.",
            "licenses": {
                "FSSAI": {"applicable": True, "status": "Valid", "expiry": datetime.date(2031, 1, 2)},
                "Trade License": {"applicable": False, "status": "N/A", "expiry": datetime.date(2027, 1, 1)},
                "Fire NOC": {"applicable": False, "status": "N/A", "expiry": datetime.date(2027, 1, 1)},
                "Pollution CTO": {"applicable": False, "status": "N/A", "expiry": datetime.date(2027, 1, 1)},
                "Signage License": {"applicable": False, "status": "N/A", "expiry": datetime.date(2027, 1, 1)}
            }
        },
        ("DLF Moti Nagar, Delhi", "July 2026"): {
            "fostac_pending": 0, "medical_pending": 0, "nsf_score": 94,
            "self_audit_done": "Yes", "self_audit_score": 92, "remark": "FSSAI and Trade valid.",
            "licenses": {
                "FSSAI": {"applicable": True, "status": "Valid", "expiry": datetime.date(2028, 12, 3)},
                "Trade License": {"applicable": True, "status": "Valid", "expiry": datetime.date(2028, 3, 31)},
                "Fire NOC": {"applicable": False, "status": "N/A", "expiry": datetime.date(2027, 1, 1)},
                "Pollution CTO": {"applicable": False, "status": "N/A", "expiry": datetime.date(2027, 1, 1)},
                "Signage License": {"applicable": False, "status": "N/A", "expiry": datetime.date(2027, 1, 1)}
            }
        },
        ("Goldust Patiala, Patiala", "July 2026"): {
            "fostac_pending": 0, "medical_pending": 0, "nsf_score": 96,
            "self_audit_done": "Yes", "self_audit_score": 95, "remark": "FSSAI valid to 2031.",
            "licenses": {
                "FSSAI": {"applicable": True, "status": "Valid", "expiry": datetime.date(2031, 3, 1)},
                "Trade License": {"applicable": False, "status": "N/A", "expiry": datetime.date(2027, 1, 1)},
                "Fire NOC": {"applicable": False, "status": "N/A", "expiry": datetime.date(2027, 1, 1)},
                "Pollution CTO": {"applicable": False, "status": "N/A", "expiry": datetime.date(2027, 1, 1)},
                "Signage License": {"applicable": False, "status": "N/A", "expiry": datetime.date(2027, 1, 1)}
            }
        },
        ("Warehouse, Delhi", "July 2026"): {
            "fostac_pending": 0, "medical_pending": 0, "nsf_score": 95,
            "self_audit_done": "Yes", "self_audit_score": 95, "remark": "FSSAI valid.",
            "licenses": {
                "FSSAI": {"applicable": True, "status": "Valid", "expiry": datetime.date(2026, 7, 8)},
                "Trade License": {"applicable": False, "status": "N/A", "expiry": datetime.date(2027, 1, 1)},
                "Fire NOC": {"applicable": False, "status": "N/A", "expiry": datetime.date(2027, 1, 1)},
                "Pollution CTO": {"applicable": False, "status": "N/A", "expiry": datetime.date(2027, 1, 1)},
                "Signage License": {"applicable": False, "status": "N/A", "expiry": datetime.date(2027, 1, 1)}
            }
        },
        ("Creek Side, Ludhiana", "July 2026"): {
            "fostac_pending": 1, "medical_pending": 1, "nsf_score": 85,
            "self_audit_done": "No", "self_audit_score": 80, "remark": "New Store Opening - FSSAI Applied.",
            "licenses": {
                "FSSAI": {"applicable": True, "status": "Applied/Pending", "expiry": datetime.date(2027, 1, 1)},
                "Trade License": {"applicable": False, "status": "N/A", "expiry": datetime.date(2027, 1, 1)},
                "Fire NOC": {"applicable": False, "status": "N/A", "expiry": datetime.date(2027, 1, 1)},
                "Pollution CTO": {"applicable": False, "status": "N/A", "expiry": datetime.date(2027, 1, 1)},
                "Signage License": {"applicable": False, "status": "N/A", "expiry": datetime.date(2027, 1, 1)}
            }
        },
        ("Chembur, Mumbai", "July 2026"): {
            "fostac_pending": 2, "medical_pending": 3, "nsf_score": 82,
            "self_audit_done": "No", "self_audit_score": 75, "remark": "New Store Opening - FSSAI Not Started.",
            "licenses": {
                "FSSAI": {"applicable": True, "status": "Applied/Pending", "expiry": datetime.date(2027, 1, 1)},
                "Trade License": {"applicable": False, "status": "N/A", "expiry": datetime.date(2027, 1, 1)},
                "Fire NOC": {"applicable": False, "status": "N/A", "expiry": datetime.date(2027, 1, 1)},
                "Pollution CTO": {"applicable": False, "status": "N/A", "expiry": datetime.date(2027, 1, 1)},
                "Signage License": {"applicable": False, "status": "N/A", "expiry": datetime.date(2027, 1, 1)}
            }
        }
    }

if 'vendor_db' not in st.session_state:
    st.session_state['vendor_db'] = {
        "July 2026": [
            {"vendor": "ABC Pest Control", "category": "Pest Control", "score": "95%", "status": "Passed", "remark": "All guidelines met"},
            {"vendor": "FreshFoods Logistics", "category": "Supply Chain", "score": "88%", "status": "Conditionally Approved", "remark": "CA pending for handwash procedures"}
        ]
    }

if 'qa_calendar_db' not in st.session_state:
    st.session_state['qa_calendar_db'] = {
        "July 2026": [
            {"date": "03", "day": "Monday", "activity": "Platina"},
            {"date": "04", "day": "Tuesday", "activity": "M3M Gurgaon-Audit"},
            {"date": "05", "day": "Wednesday", "activity": "GK-1-Audit"},
            {"date": "06", "day": "Thursday", "activity": "WFH"},
            {"date": "07", "day": "Friday", "activity": "Platina"},
            {"date": "10", "day": "Monday", "activity": "Janakpuri-Training"},
            {"date": "11", "day": "Tuesday", "activity": "Head Office"},
            {"date": "12", "day": "Wednesday", "activity": "Warehouse"},
            {"date": "13", "day": "Thursday", "activity": "Noida"},
            {"date": "14", "day": "Friday", "activity": "Malcha Marg"},
            {"date": "17", "day": "Monday", "activity": "Janakpuri"},
            {"date": "18", "day": "Tuesday", "activity": "Moti Nagar"},
            {"date": "19", "day": "Wednesday", "activity": "Patiala"},
            {"date": "20", "day": "Thursday", "activity": "Ludhiana"},
            {"date": "21", "day": "Friday", "activity": "Head Office"},
            {"date": "24", "day": "Monday", "activity": "Warehouse"},
            {"date": "25", "day": "Tuesday", "activity": "Vendor Audit"},
            {"date": "26", "day": "Wednesday", "activity": "Head Office"},
            {"date": "27", "day": "Thursday", "activity": "Pune Season Mall"},
            {"date": "28", "day": "Friday", "activity": "Sky City Mumbai"},
            {"date": "31", "day": "Monday", "activity": "Platina"}
        ]
    }

if 'pdf_archive' not in st.session_state:
    st.session_state['pdf_archive'] = {}

# Helper to grab store monthly info
def get_store_monthly(store_name, month):
    key = (store_name, month)
    if key in st.session_state['monthly_db']:
        return copy.deepcopy(st.session_state['monthly_db'][key])
    else:
        return {
            "fostac_pending": 1, "medical_pending": 5, "nsf_score": 90,
            "self_audit_done": "No", "self_audit_score": 85, "remark": "",
            "licenses": {
                "FSSAI": {"applicable": True, "status": "Valid", "expiry": datetime.date(2027, 12, 31)},
                "Trade License": {"applicable": True, "status": "Valid", "expiry": datetime.date(2027, 6, 30)},
                "Fire NOC": {"applicable": False, "status": "N/A", "expiry": datetime.date(2027, 1, 1)},
                "Pollution CTO": {"applicable": False, "status": "N/A", "expiry": datetime.date(2027, 1, 1)},
                "Signage License": {"applicable": False, "status": "N/A", "expiry": datetime.date(2027, 1, 1)}
            }
        }

# Build aggregated dataframe for the selected month
monthly_records = []
for idx, row in df_stores.iterrows():
    s_name = row['name']
    m_data = get_store_monthly(s_name, selected_month)
    is_comp = (m_data['fostac_pending'] == 0) and (m_data['medical_pending'] == 0)
    
    lics = m_data['licenses']
    any_lic_issue = any(l_val['applicable'] and l_val['status'] != 'Valid' for l_val in lics.values())
    
    monthly_records.append({
        'name': s_name,
        'is_outstation': row['is_outstation'],
        'month': selected_month,
        'fostac_pending': m_data['fostac_pending'],
        'medical_pending': m_data['medical_pending'],
        'is_compliant': is_comp,
        'nsf_score': m_data['nsf_score'],
        'self_audit_done': m_data['self_audit_done'],
        'self_audit_score': m_data['self_audit_score'],
        'remark': m_data['remark'],
        'has_license_issue': any_lic_issue,
        'licenses': lics
    })

df_monthly_filtered = pd.DataFrame(monthly_records)

# --- CEO-LEVEL HEADER ---
st.title(f"🛡️ Enterprise QA & Compliance Command Center — {selected_month}")
st.markdown("Real-time oversight of Retail Operations, Licensing, Supply Chain, and Regulatory Compliance.")
st.divider()

# --- DASHBOARD TABS ---
tab_exec, tab_ops, tab_supply, tab_lic_summary, tab_calendar, tab_subfranchise, tab_reports, tab_admin = st.tabs([
    "📊 Executive Dashboard", 
    "🏬 Retail Operations", 
    "🚚 Vendor & Supply Chain", 
    "📜 License Summary",
    "📅 QA Calendar",
    "🤝 Sub Franchise",
    "📑 Reports & Archive",
    "⚙️ System Administration"
])

# ==========================================
# TAB 1: EXECUTIVE DASHBOARD
# ==========================================
with tab_exec:
    st.subheader(f"📈 {selected_month} Summary")
    
    col1, col2, col3, col4 = st.columns(4)
    total_stores = len(df_stores)
    compliant_stores = int(df_monthly_filtered['is_compliant'].sum()) if not df_monthly_filtered.empty else 0
    avg_nsf = df_monthly_filtered['nsf_score'].mean() if not df_monthly_filtered.empty else 0
    stores_with_lic_issues = int(df_monthly_filtered['has_license_issue'].sum()) if not df_monthly_filtered.empty else 0
    
    col1.metric("Total Active Stores", total_stores)
    col2.metric("Fully Compliant Stores (Staffing)", f"{compliant_stores}/{total_stores}", delta=f"{compliant_stores-total_stores} Non-compliant", delta_color="inverse")
    col3.metric("Average NSF Score", f"{avg_nsf:.1f}%" if pd.notnull(avg_nsf) else "N/A")
    col4.metric("Stores with License Flags", f"{stores_with_lic_issues}", delta=f"{stores_with_lic_issues} Flags", delta_color="inverse")

    st.markdown("---")

    if not df_monthly_filtered.empty:
        chart_col1, chart_col2 = st.columns(2)
        
        with chart_col1:
            comp_counts = df_monthly_filtered['is_compliant'].value_counts().reset_index()
            comp_counts['is_compliant'] = comp_counts['is_compliant'].map({True: 'Compliant (FoSTaC & Medical = 0)', False: 'Pending Requirements'})
            comp_counts.columns = ['Status', 'Count']
            fig_comp = px.pie(
                comp_counts, values='Count', names='Status', hole=0.6, 
                title=f"Staff Compliance Status ({selected_month})",
                color_discrete_sequence=['#10B981', '#EF4444']
            )
            fig_comp.update_traces(textposition='inside', textinfo='percent+label')
            fig_comp.update_layout(showlegend=False, margin=dict(t=40, b=0, l=0, r=0))
            st.plotly_chart(fig_comp, use_container_width=True)

        with chart_col2:
            fig_nsf = px.bar(
                df_monthly_filtered, x='name', y='nsf_score', text='nsf_score',
                title=f"NSF Audit Scores by Store ({selected_month})",
                color='nsf_score', color_continuous_scale='Blues'
            )
            fig_nsf.update_traces(textposition='outside')
            fig_nsf.update_layout(xaxis_tickangle=-35, showlegend=False, margin=dict(t=40, b=40, l=0, r=0))
            st.plotly_chart(fig_nsf, use_container_width=True)

    st.markdown("### 📋 Store-by-Store Compliance Status")
    if not df_monthly_filtered.empty:
        table_view = df_monthly_filtered[['name', 'fostac_pending', 'medical_pending', 'is_compliant', 'nsf_score', 'self_audit_done', 'self_audit_score', 'remark']].copy()
        table_view.columns = ["Store Name", "FoSTaC Pending", "Medical Pending", "Fully Compliant?", "NSF Score", "Self Audit Done?", "Self Audit Score", "Remark"]
        st.dataframe(table_view, use_container_width=True, hide_index=True)

# ==========================================
# TAB 2: RETAIL OPERATIONS (Data Entry & Licenses)
# ==========================================
with tab_ops:
    st.subheader("Update Store-Level Compliance & Licenses")
    if not df_stores.empty:
        store_names = df_stores['name'].tolist()
        selected_store = st.selectbox("Select Store", store_names, key=f"ops_store_{selected_month}")
        
        current_data = get_store_monthly(selected_store, selected_month)
        
        st.markdown(f"**Managing Data For:** `{selected_store}` | **Period:** `{selected_month}`")
        
        with st.form(f"form_{selected_store}_{selected_month}"):
            col_a, col_b = st.columns(2)
            
            with col_a:
                st.markdown("#### 👥 Staff Compliance & Pending Counts")
                fostac_val = st.number_input("FoSTaC Pending Count", min_value=0, value=int(current_data['fostac_pending']), key=f"fos_{selected_store}_{selected_month}")
                medical_val = st.number_input("Medical Pending Count", min_value=0, value=int(current_data['medical_pending']), key=f"med_{selected_store}_{selected_month}")
                
                st.markdown("#### 📋 Self-Audit & NSF Scores")
                nsf_val = st.number_input("NSF Score (%)", min_value=0, max_value=100, value=int(current_data['nsf_score']), key=f"nsf_{selected_store}_{selected_month}")
                
                audit_options = ["No", "Yes"]
                default_audit_idx = 1 if current_data['self_audit_done'] == "Yes" else 0
                self_audit_choice = st.selectbox("Monthly Self Audit Done?", audit_options, index=default_audit_idx, key=f"sa_done_{selected_store}_{selected_month}")
                
                self_score_val = st.number_input("Self Audit Score (%)", min_value=0, max_value=100, value=int(current_data['self_audit_score']), key=f"sa_score_{selected_store}_{selected_month}")
            
            with col_b:
                st.markdown("#### 📑 License Compliance Tracking")
                st.caption("Toggle off if a license is not applicable to this specific outlet.")
                
                updated_licenses = {}
                licenses_dict = current_data['licenses']
                
                for lic_name, lic_info in licenses_dict.items():
                    with st.expander(f"License: {lic_name}", expanded=True):
                        is_app = st.checkbox("Applicable?", value=bool(lic_info['applicable']), key=f"app_{selected_store}_{lic_name}_{selected_month}")
                        
                        if is_app:
                            status_opts = ["Valid", "Applied/Pending", "Expired"]
                            curr_stat = lic_info['status'] if lic_info['status'] in status_opts else "Valid"
                            stat_val = st.selectbox("Status", status_opts, index=status_opts.index(curr_stat), key=f"stat_{selected_store}_{lic_name}_{selected_month}")
                            
                            try:
                                default_exp = lic_info['expiry'] if isinstance(lic_info['expiry'], datetime.date) else datetime.date.today()
                            except:
                                default_exp = datetime.date.today()
                                
                            exp_val = st.date_input("Expiry Date", value=default_exp, key=f"exp_{selected_store}_{lic_name}_{selected_month}")
                        else:
                            stat_val = "N/A"
                            exp_val = datetime.date(2027, 1, 1)
                            
                        updated_licenses[lic_name] = {"applicable": is_app, "status": stat_val, "expiry": exp_val}
                
                st.markdown("---")
                st.markdown("#### ➕ Add Custom License")
                new_lic_name = st.text_input("New License Name (e.g. Signage, Pollution)", key=f"new_lic_{selected_store}_{selected_month}")
                add_lic_clicked = st.form_submit_button("Add License to Outlet")
                if add_lic_clicked and new_lic_name:
                    if new_lic_name not in updated_licenses:
                        updated_licenses[new_lic_name] = {"applicable": True, "status": "Valid", "expiry": datetime.date.today()}
                        st.success(f"Added {new_lic_name}!")

            st.markdown("---")
            remark_val = st.text_area("Remark / Notes", value=str(current_data['remark']), key=f"rem_{selected_store}_{selected_month}")
            
            save_button = st.form_submit_button(f"Save Store Data for {selected_month}", type="primary")
            
            if save_button:
                st.session_state['monthly_db'][(selected_store, selected_month)] = {
                    "fostac_pending": fostac_val,
                    "medical_pending": medical_val,
                    "nsf_score": nsf_val,
                    "self_audit_done": self_audit_choice,
                    "self_audit_score": self_score_val,
                    "remark": remark_val,
                    "licenses": updated_licenses
                }
                st.success(f"Successfully recorded operations data for {selected_store} in {selected_month}!")

# ==========================================
# TAB 3: VENDOR & SUPPLY CHAIN
# ==========================================
with tab_supply:
    st.subheader(f"Vendor Audit Performance — {selected_month}")
    st.markdown("Record audits performed for specific vendors during the selected month.")
    
    if selected_month not in st.session_state['vendor_db']:
        st.session_state['vendor_db'][selected_month] = []
        
    current_vendors = st.session_state['vendor_db'][selected_month]
    
    with st.form(f"vendor_form_{selected_month}"):
        col_v1, col_v2, col_v3 = st.columns(3)
        with col_v1:
            v_name = st.text_input("Vendor Name")
        with col_v2:
            v_cat = st.selectbox("Category", ["Pest Control", "Supply Chain", "Packaging", "Chemicals"])
            v_score = st.text_input("Audit Score / Percentage")
        with col_v3:
            v_status = st.selectbox("Audit Status", ["Passed", "Conditionally Approved", "Failed"])
            
        v_remark = st.text_input("Remark")
        
        add_vendor_btn = st.form_submit_button("Add Vendor Audit Record")
        if add_vendor_btn and v_name:
            st.session_state['vendor_db'][selected_month].append({
                "vendor": v_name, "category": v_cat, "score": v_score, "status": v_status, "remark": v_remark
            })
            st.success(f"Added audit record for {v_name}!")
            
    st.markdown("### Recorded Vendor Audits for this Month")
    if current_vendors:
        df_v = pd.DataFrame(current_vendors)
        df_v.columns = ["Vendor Name", "Category", "Score", "Status", "Remark"]
        st.dataframe(df_v, use_container_width=True, hide_index=True)
    else:
        st.info("No vendor audits recorded for this month yet.")

# ==========================================
# TAB 4: LICENSE SUMMARY
# ==========================================
with tab_lic_summary:
    st.subheader(f"📜 Consolidated License Compliance Summary — {selected_month}")
    st.markdown("Overview of all active licenses across all 14 outlets for the selected reporting month.")
    
    lic_summary_rows = []
    for idx, row in df_stores.iterrows():
        s_name = row['name']
        m_data = get_store_monthly(s_name, selected_month)
        for l_name, l_info in m_data['licenses'].items():
            lic_summary_rows.append({
                "Store Name": s_name,
                "License Name": l_name,
                "Applicable": "Yes" if l_info['applicable'] else "No",
                "Status": l_info['status'],
                "Expiry Date": str(l_info['expiry'])
            })
            
    if lic_summary_rows:
        df_lic_summary = pd.DataFrame(lic_summary_rows)
        
        f_status = st.selectbox("Filter by Status", ["All"] + list(df_lic_summary['Status'].unique()))
        if f_status != "All":
            df_lic_summary = df_lic_summary[df_lic_summary['Status'] == f_status]
            
        st.dataframe(df_lic_summary, use_container_width=True, hide_index=True)

# ==========================================
# TAB 5: QA CALENDAR
# ==========================================
with tab_calendar:
    st.subheader(f"📅 QA Field Audit & Schedule — {selected_month}")
    st.markdown("Track on-site store audits, training sessions, vendor visits, and travel itineraries.")
    
    if selected_month not in st.session_state['qa_calendar_db']:
        st.session_state['qa_calendar_db'][selected_month] = []
        
    current_cal = st.session_state['qa_calendar_db'][selected_month]
    
    with st.expander("➕ Add New Schedule Entry", expanded=False):
        with st.form(f"add_cal_form_{selected_month}"):
            c1, c2, c3 = st.columns(3)
            with c1:
                cal_date = st.text_input("Date (e.g. 03 or 15)")
            with c2:
                cal_day = st.selectbox("Day", ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"])
            with c3:
                cal_activity = st.text_input("Activity / Location")
                
            submitted_cal = st.form_submit_button("Add to Calendar")
            if submitted_cal and cal_date and cal_activity:
                st.session_state['qa_calendar_db'][selected_month].append({
                    "date": cal_date, "day": cal_day, "activity": cal_activity
                })
                st.success("Calendar entry added successfully!")
                st.rerun()
                
    if current_cal:
        df_cal_view = pd.DataFrame(current_cal)
        df_cal_view.columns = ["Date", "Day", "Scheduled Activity / Location"]
        st.dataframe(df_cal_view, use_container_width=True, hide_index=True)
    else:
        st.info("No schedule entries found for this month.")

# ==========================================
# TAB 6: SUB FRANCHISE
# ==========================================
with tab_subfranchise:
    st.subheader(f"🤝 Sub Franchise (189-Series) Audit Summary")
    st.markdown("Overview and details of NSF audits for Sub Franchise outlets.")
    
    if 'sub_franchise_audits' not in st.session_state:
        st.session_state['sub_franchise_audits'] = [
            {"Store Name": "C-Block, Janakpuri, DL", "Site Code": "18910001", "Score": 90.43, "Result": "PASS", "Audit Date": "2026-07-28"},
            {"Store Name": "Downtown Market, Ludhiana", "Site Code": "18910010", "Score": 87.39, "Result": "PASS", "Audit Date": "2026-07-16"},
            {"Store Name": "Downtown Market, Ludhiana", "Site Code": "18910010", "Score": 83.78, "Result": "FAIL", "Audit Date": "2026-06-23"},
            {"Store Name": "Seasons Mall, Pune", "Site Code": "18910009", "Score": 90.52, "Result": "PASS", "Audit Date": "2026-07-31"},
            {"Store Name": "DLF Mid Town Plaza, Moti Nagar", "Site Code": "18910012", "Score": 85.84, "Result": "PASS", "Audit Date": "2026-07-24"}
        ]
    
    sf_df = pd.DataFrame(st.session_state['sub_franchise_audits'])
    
    col_sf1, col_sf2, col_sf3, col_sf4 = st.columns(4)
    total_sf_audits = len(sf_df)
    avg_sf_score = sf_df['Score'].mean()
    pass_count = len(sf_df[sf_df['Result'] == 'PASS'])
    pass_rate = (pass_count / total_sf_audits) * 100 if total_sf_audits > 0 else 0
    
    col_sf1.metric("Total SF Audits", total_sf_audits)
    col_sf2.metric("Average SF Score", f"{avg_sf_score:.2f}%")
    col_sf3.metric("Passed Audits", pass_count)
    col_sf4.metric("Pass Rate", f"{pass_rate:.1f}%")

    # Interactive Bar Chart for SF Audits
    fig_sf = px.bar(
        sf_df, x='Store Name', y='Score', text='Score', color='Result',
        color_discrete_map={'PASS': '#10B981', 'FAIL': '#EF4444'},
        title=f"Sub Franchise NSF Scores"
    )
    fig_sf.update_traces(textposition='outside')
    fig_sf.update_layout(xaxis_tickangle=-15, margin=dict(t=40, b=40, l=0, r=0))
    st.plotly_chart(fig_sf, use_container_width=True)
    
    st.markdown("### 📋 NSF Audit Details")
    st.dataframe(sf_df, use_container_width=True, hide_index=True)

# ==========================================
# TAB 7: REPORTS & ARCHIVE
# ==========================================
with tab_reports:
    st.subheader(f"📑 PDF Report Generation & Historical Archive ({selected_month})")
    st.markdown("Generate and archive an official PDF report of the network compliance for the selected month. Past reports can be retrieved from the archive below.")
    
    def generate_pdf(month_str, records, vendors, calendar_entries):
        if FPDF is None:
            return None
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=14, style='B')
        pdf.cell(200, 10, txt=f"QA & Compliance Report - {month_str}", ln=True, align='C')
        pdf.set_font("Arial", size=10)
        pdf.cell(200, 8, txt=f"Generated on: {datetime.date.today().strftime('%Y-%m-%d')}", ln=True, align='C')
        pdf.ln(10)
        
        pdf.set_font("Arial", size=11, style='B')
        pdf.cell(200, 8, txt="Executive Summary & Store Compliance:", ln=True)
        pdf.set_font("Arial", size=9)
        
        for r in records:
            comp_txt = "Fully Compliant" if r['is_compliant'] else f"Pending (FoSTaC: {r['fostac_pending']}, Med: {r['medical_pending']})"
            pdf.cell(200, 6, txt=f"- {r['name']}: {comp_txt} | NSF: {r['nsf_score']}% | Remark: {r['remark']}", ln=True)
            
        pdf.ln(5)
        pdf.set_font("Arial", size=11, style='B')
        pdf.cell(200, 8, txt="Vendor Audit Summary:", ln=True)
        pdf.set_font("Arial", size=9)
        for v in vendors:
            pdf.cell(200, 6, txt=f"- {v['vendor']} ({v['category']}): Score {v['score']} - Status: {v['status']} [{v['remark']}]", ln=True)

        pdf.ln(5)
        pdf.set_font("Arial", size=11, style='B')
        pdf.cell(200, 8, txt="QA Field Schedule Summary:", ln=True)
        pdf.set_font("Arial", size=9)
        for c in calendar_entries:
            pdf.cell(200, 6, txt=f"- Date {c['date']} ({c['day']}): {c['activity']}", ln=True)
            
        return pdf.output(dest='S').encode('latin-1')

    if st.button("Generate & Archive PDF Report", type="primary"):
        pdf_bytes = generate_pdf(selected_month, monthly_records, st.session_state['vendor_db'].get(selected_month, []), st.session_state['qa_calendar_db'].get(selected_month, []))
        if pdf_bytes:
            st.session_state['pdf_archive'][selected_month] = pdf_bytes
            st.success(f"PDF successfully generated and archived for {selected_month}!")
        else:
            st.error("fpdf2 library not installed. Please add 'fpdf2' to requirements.txt.")
            
    if selected_month in st.session_state['pdf_archive']:
        st.download_button(
            label=f"📥 Download Archived PDF Report ({selected_month})",
            data=st.session_state['pdf_archive'][selected_month],
            file_name=f"QA_Compliance_Report_{selected_month.replace(' ', '_')}.pdf",
            mime="application/pdf"
        )
    else:
        st.info("No archived PDF found for this month yet. Click the button above to generate one.")

# ==========================================
# TAB 8: SYSTEM ADMINISTRATION
# ==========================================
with tab_admin:
    st.subheader("⚙️ Store Portfolio & System Administration")
    st.markdown("Add, edit, or delete store locations in your master network.")
    
    with st.expander("➕ Add a New Store Location", expanded=False):
        with st.form("new_store_form"):
            new_name = st.text_input("Store Name", placeholder="e.g., New Outlet Name")
            is_out = st.checkbox("Is Outstation?")
            if st.form_submit_button("Add Store to Database"):
                if new_name:
                    st.session_state['master_stores'].append({'name': new_name, 'is_outstation': is_out})
                    st.success(f"Added {new_name} successfully!")
                    st.rerun()
                    
    with st.expander("✏️ Edit or Remove an Existing Store", expanded=False):
        if st.session_state['master_stores']:
            store_names_list = [s['name'] for s in st.session_state['master_stores']]
            store_to_edit = st.selectbox("Select Store to Edit/Delete", store_names_list)
            
            store_obj = next((s for s in st.session_state['master_stores'] if s['name'] == store_to_edit), None)
            
            if store_obj:
                with st.form("edit_store_form"):
                    updated_name = st.text_input("Update Store Name", value=store_obj['name'])
                    updated_outstation = st.checkbox("Is Outstation?", value=store_obj['is_outstation'])
                    
                    col_e1, col_e2 = st.columns(2)
                    update_submitted = col_e1.form_submit_button("Save Changes", type="primary")
                    delete_submitted = col_e2.form_submit_button("Delete Store")
                    
                    if update_submitted and updated_name:
                        store_obj['name'] = updated_name
                        store_obj['is_outstation'] = updated_outstation
                        st.success("Store updated successfully!")
                        st.rerun()
                        
                    if delete_submitted:
                        st.session_state['master_stores'] = [s for s in st.session_state['master_stores'] if s['name'] != store_to_edit]
                        st.warning(f"Deleted {store_to_edit} from database.")
                        st.rerun()
