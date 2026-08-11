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

# --- 2. DATA LOADING & SAMPLE INITIALIZATION ---
if 'master_stores' not in st.session_state:
    st.session_state['master_stores'] = [
        {'name': 'CBTL Janakpuri, New Delhi', 'is_outstation': False},
        {'name': 'CBTL Greater Kailash (M-Block), New Delhi', 'is_outstation': False},
        {'name': 'CBTL Platina Tower, Gurugram', 'is_outstation': False},
        {'name': 'CBTL Sector 50, Noida', 'is_outstation': False},
        {'name': 'CBTL Seasons Mall, Pune', 'is_outstation': True},
        {'name': 'CBTL Goldust City Centre, Patiala', 'is_outstation': True},
        {'name': 'CBTL Elante Mall, Chandigarh', 'is_outstation': True},
        {'name': 'CBTL Bandra West, Mumbai', 'is_outstation': True},
        {'name': 'CBTL Koramangala, Bengaluru', 'is_outstation': True},
        {'name': 'CBTL Jubilee Hills, Hyderabad', 'is_outstation': True},
        {'name': 'CBTL Central Plaza, Kolkata', 'is_outstation': True},
        {'name': 'CBTL VR Mall, Chennai', 'is_outstation': True},
        {'name': 'Creek Side, Ludhiana (New)', 'is_outstation': True}
    ]
df_stores = pd.DataFrame(st.session_state['master_stores'])

# Fallback/Session State Simulation for Monthly Operations & License tracking
if 'monthly_db' not in st.session_state:
    st.session_state['monthly_db'] = {
        ("CBTL Janakpuri, New Delhi", "July 2026"): {
            "fostac_pending": 0, "medical_pending": 0, "nsf_score": 92,
            "self_audit_done": "Yes", "self_audit_score": 90, "remarks": "All clean.",
            "licenses": {
                "FSSAI License": {"applicable": True, "status": "Valid", "expiry": datetime.date(2027, 5, 12)},
                "Trade License": {"applicable": True, "status": "Valid", "expiry": datetime.date(2027, 1, 10)},
                "Fire NOC": {"applicable": False, "status": "N/A", "expiry": datetime.date(2027, 1, 1)},
                "Signage License": {"applicable": True, "status": "Valid", "expiry": datetime.date(2027, 3, 15)}
            }
        },
        ("CBTL Greater Kailash (M-Block), New Delhi", "July 2026"): {
            "fostac_pending": 1, "medical_pending": 2, "nsf_score": 85,
            "self_audit_done": "Yes", "self_audit_score": 88, "remarks": "Pending license due to software portal issue",
            "licenses": {
                "FSSAI License": {"applicable": True, "status": "Applied/Pending", "expiry": datetime.date(2026, 8, 15)},
                "Trade License": {"applicable": True, "status": "Valid", "expiry": datetime.date(2027, 2, 20)},
                "Fire NOC": {"applicable": True, "status": "Valid", "expiry": datetime.date(2028, 1, 1)},
                "Signage License": {"applicable": True, "status": "Valid", "expiry": datetime.date(2027, 4, 1)}
            }
        }
    }

# Helper to grab store monthly info
def get_store_monthly(store_name, month):
    key = (store_name, month)
    if key in st.session_state['monthly_db']:
        return copy.deepcopy(st.session_state['monthly_db'][key])
    else:
        # Defaults requested: fostac_pending = 1, medical_pending = 5
        return {
            "fostac_pending": 1, "medical_pending": 5, "nsf_score": 90,
            "self_audit_done": "No", "self_audit_score": 85, "remarks": "",
            "licenses": {
                "FSSAI License": {"applicable": True, "status": "Valid", "expiry": datetime.date(2027, 12, 31)},
                "Trade License": {"applicable": True, "status": "Valid", "expiry": datetime.date(2027, 6, 30)},
                "Fire NOC": {"applicable": False, "status": "N/A", "expiry": datetime.date(2027, 1, 1)},
                "Signage License": {"applicable": True, "status": "Valid", "expiry": datetime.date(2027, 3, 31)}
            }
        }

# Build aggregated dataframe for the selected month
monthly_records = []
for idx, row in df_stores.iterrows():
    s_name = row['name']
    m_data = get_store_monthly(s_name, selected_month)
    is_comp = (m_data['fostac_pending'] == 0) and (m_data['medical_pending'] == 0)
    
    # Check license compliance overall
    lics = m_data['licenses']
    any_lic_issue = any(l_val['applicable'] and l_val['status'] != 'Valid' for l_val in lics.values())
    
    monthly_records.append({
        'name': s_name,
        'is_outstation': row['is_outstation'],
        'month': selected_month,
        'fostac_pending': m_data['fostac_pending'],
