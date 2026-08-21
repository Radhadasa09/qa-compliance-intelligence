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

tab_exec, tab_ops, tab_supply, tab_lic_summary, tab_nsf, tab_reports, tab_admin = st.tabs([
    "📊 Executive Dashboard",
    "🏬 Retail Operations",
    "🚚 Vendor & Supply Chain",
    "📜 License Summary",
    "📈 NSF Audit Intelligence",
    "📑 Reports & Archive",
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
    if not df_monthly_filtered.empty:
        table_view = df_monthly_filtered[['name', 'fostac_pending', 'medical_pending', 'is_compliant', 'self_audit_done', 'self_audit_score', 'remark']].copy()
        table_view.columns = ["Store Name", "FoSTaC Pending", "Medical Pending", "Fully Compliant?", "Self Audit Done?", "Self Audit Score", "Remark"]
        st.dataframe(table_view, use_container_width=True, hide_index=True)

# ==========================================
# TAB 2: RETAIL OPERATIONS (Data Entry & Live Logs)
# ==========================================
with tab_ops:
    st.subheader("🏬 Retail Operations & Compliance Status")
    
    # --- 1. LIVE DAILY SHIFT CHECKLISTS ---
    st.markdown("### 📋 Live Daily Shift Submissions")
    if not df_daily_live.empty:
        # Select the most important columns to show management
        cols_to_show = ['store_id', 'manager_name', 'shift']
        if 'created_at' in df_daily_live.columns:
            cols_to_show.append('created_at')
            
        display_df = df_daily_live[cols_to_show].copy()
        
        # Rename columns for a cleaner presentation
        display_df.columns = [col.replace("_", " ").title() for col in display_df.columns]
        
        st.dataframe(display_df, use_container_width=True, hide_index=True)
    else:
        st.info("No daily shift checklists submitted by store managers yet.")

    st.markdown("---")

    # --- 2. MONTHLY COMPLIANCE TRACKER ---
    st.markdown("### ⚙️ Update Store-Level Monthly Compliance & Licenses")
    if not df_stores.empty:
        store_names = df_stores['name'].tolist()
        selected_store = st.selectbox("Select Store", store_names, key=f"ops_store_{selected_month}")
        
        current_data = get_store_monthly(selected_store, selected_month)
        st.markdown(f"**Managing Data For:** `{selected_store}` | **Period:** `{selected_month}`")
        
        with st.form(f"form_{selected_store}_{selected_month}"):
            col_a, col_b = st.columns(2)
            
            with col_a:
                st.markdown("#### 👥 Staff Compliance & Pending Counts")
                fostac_val = st.number_input("FoSTaC Pending Count", min_value=0, value=int(current_data['fostac_pending']))
                medical_val = st.number_input("Medical Pending Count", min_value=0, value=int(current_data['medical_pending']))
                
                st.markdown("#### 📋 Self-Audit")
                audit_options = ["No", "Yes"]
                default_audit_idx = 1 if current_data['self_audit_done'] == "Yes" else 0
                self_audit_choice = st.selectbox("Monthly Self Audit Done?", audit_options, index=default_audit_idx)
                self_score_val = st.number_input("Self Audit Score (%)", min_value=0, max_value=100, value=int(current_data['self_audit_score']))
            
            with col_b:
                st.markdown("#### 📑 License Compliance Tracking")
                updated_licenses = {}
                licenses_dict = current_data['licenses']
                
                for lic_name, lic_info in licenses_dict.items():
                    with st.expander(f"License: {lic_name}", expanded=True):
                        is_app = st.checkbox("Applicable?", value=bool(lic_info['applicable']), key=f"app_{selected_store}_{lic_name}")
                        if is_app:
                            status_opts = ["Valid", "Applied/Pending", "Expired"]
                            curr_stat = lic_info['status'] if lic_info['status'] in status_opts else "Valid"
                            stat_val = st.selectbox("Status", status_opts, index=status_opts.index(curr_stat), key=f"stat_{selected_store}_{lic_name}")
                            try:
                                default_exp = lic_info['expiry'] if isinstance(lic_info['expiry'], datetime.date) else datetime.date.today()
                            except:
                                default_exp = datetime.date.today()
                            exp_val = st.date_input("Expiry Date", value=default_exp, key=f"exp_{selected_store}_{lic_name}")
                        else:
                            stat_val, exp_val = "N/A", datetime.date(2027, 1, 1)
                        updated_licenses[lic_name] = {"applicable": is_app, "status": stat_val, "expiry": exp_val}
                
                st.markdown("---")
                new_lic_name = st.text_input("New License Name")
                if st.form_submit_button("Add License") and new_lic_name:
                    if new_lic_name not in updated_licenses:
                        updated_licenses[new_lic_name] = {"applicable": True, "status": "Valid", "expiry": datetime.date.today()}
                        st.success(f"Added {new_lic_name}!")

            st.markdown("---")
            remark_val = st.text_area("Remark / Notes", value=str(current_data['remark']))
            
            if st.form_submit_button(f"Save Store Data for {selected_month}", type="primary"):
                st.session_state['monthly_db'][(selected_store, selected_month)] = {
                    "fostac_pending": fostac_val, "medical_pending": medical_val, 
                    "nsf_score": current_data['nsf_score'], "self_audit_done": self_audit_choice,
                    "self_audit_score": self_score_val, "remark": remark_val, "licenses": updated_licenses
                }
                st.success("Successfully recorded operations data!")
import requests
from io import BytesIO

# ==========================================
# HELPER: ITEMIZED CHECKLIST PDF GENERATOR (With Item-Level Comments)
# ==========================================
def generate_detailed_checklist_pdf(vendor_name, fso, lic_no, address, audit_date, audit_responses, score_val, grade, remarks, photo_urls):
    if FPDF is None: return None
    pdf = FPDF()
    pdf.add_page()
    
    # Header
    pdf.set_font("Arial", size=15, style='B')
    pdf.cell(200, 8, txt="The Coffee Bean & Tea Leaf (CBTL) India", ln=1, align='C')
    pdf.set_font("Arial", size=9, style='I')
    pdf.cell(200, 5, txt="Ekaagra Ostalaritza Private Limited - General Manufacturing Audit Report", ln=1, align='C')
    pdf.ln(4)
    
    # Metadata Box
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font("Arial", size=9, style='B')
    pdf.cell(200, 6, txt=f"  Vendor / FBO Name: {vendor_name}", ln=1, align='L', fill=True)
    pdf.cell(200, 6, txt=f"  FBO License No.: {lic_no}  |  Address: {address}", ln=1, align='L', fill=True)
    pdf.cell(200, 6, txt=f"  Auditor / FSO: {fso}", ln=1, align='L', fill=True)
    pdf.cell(200, 6, txt=f"  Final Score: {score_val:.1f}%  |  Official Grade: {grade}", ln=1, align='L', fill=True)
    pdf.cell(200, 6, txt=f"  Audit Date: {audit_date.strftime('%d-%b-%Y')}  |  Report Generated: {datetime.date.today().strftime('%d-%b-%Y')}", ln=1, align='L', fill=True)
    pdf.ln(6)
    
    # Table Header
    pdf.set_font("Arial", size=9, style='B')
    pdf.set_fill_color(50, 50, 50)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(130, 7, txt="  Audit Question / Checklist Parameter", border=1, align='L', fill=True)
    pdf.cell(30, 7, txt="Status", border=1, align='C', fill=True)
    pdf.cell(30, 7, txt="Deduction Note", border=1, align='C', fill=True)
    pdf.set_text_color(0, 0, 0)
    pdf.ln()
    
    # Table Body
    pdf.set_font("Arial", size=8)
    fill_row = False
    for q_text, data in audit_responses.items():
        status_short = data["status"].split(" ")[0]
        row_label = f"  {q_text} ({data['points']} pts)"
        comment_note = data.get("comment", "")
        
        pdf.set_fill_color(245, 245, 245) if fill_row else pdf.set_fill_color(255, 255, 255)
        pdf.cell(130, 6, txt=row_label, border=1, align='L', fill=True)
        pdf.cell(30, 6, txt=status_short, border=1, align='C', fill=True)
        pdf.cell(30, 6, txt=comment_note[:18] if comment_note else "-", border=1, align='C', fill=True)
        pdf.ln()
        fill_row = not fill_row
        
    pdf.ln(6)
    
    # Overall Remarks
    pdf.set_font("Arial", size=10, style='B')
    pdf.cell(200, 6, txt="Overall Remarks & Corrective Actions Required:", ln=1, align='L')
    pdf.set_font("Arial", size=9)
    pdf.multi_cell(200, 5, txt=str(remarks if remarks else "None"))
    pdf.ln(6)
    
    # Embedded Photo Gallery
    if photo_urls:
        pdf.add_page()
        pdf.set_font("Arial", size=12, style='B')
        pdf.cell(200, 7, txt="Inspection Photographic Evidence", ln=1, align='L')
        pdf.ln(4)
        
        urls = [u.strip() for u in photo_urls.split(",")]
        col_width = 85
        col_gap = 10
        current_col = 0
        y_start = pdf.get_y()
        
        for idx, u in enumerate(urls):
            try:
                response = requests.get(u)
                if response.status_code == 200:
                    image_stream = BytesIO(response.content)
                    x_pos = 10 + current_col * (col_width + col_gap)
                    y_pos = pdf.get_y()
                    
                    if current_col == 1 and idx > 0:
                        y_pos = y_start
                    
                    pdf.set_xy(x_pos, y_pos)
                    pdf.set_font("Arial", size=8, style='B')
                    pdf.cell(col_width, 5, txt=f"Proof Photo {idx+1}", ln=1, align='L')
                    pdf.set_x(x_pos)
                    pdf.image(image_stream, x=x_pos, w=col_width)
                    
                    if current_col == 1:
                        pdf.ln(55)
                        y_start = pdf.get_y()
                        current_col = 0
                    else:
                        current_col = 1
            except Exception:
                pass

    try:
        return bytes(pdf.output())
    except TypeError:
        return pdf.output(dest='S').encode('latin-1')


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
        st.caption("Evaluate vendors across the 40-point checklist[cite: 2]. Point deduction comment boxes appear automatically when compliance is compromised.")
        
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
# TAB 4: LICENSE SUMMARY (Interactive File Upload)
# ==========================================
with tab_lic_summary:
    st.subheader("📜 License Compliance Summary — Live Data")
    st.caption("Upload your 90-Day Tracker Excel file to generate the live compliance dashboard.")
    
    # 1. Add the File Uploader
    uploaded_file = st.file_uploader("Upload License Tracker (Excel)", type=["xlsx", "xls"])
    
    if uploaded_file is not None:
        try:
            # 2. Load and clean the Excel file directly from the uploader
            df_lic = pd.read_excel(uploaded_file, sheet_name="Sheet1")
            
            # Clean up the headers (row 0 contains the actual column names in your sheet)
            df_lic.columns = ['S.no', 'Location', 'City', 'FSSAI', 'Trade', 'Fire', 'Pollution CTO', 'Signage', 'Remark']
            df_lic = df_lic.iloc[1:].reset_index(drop=True)
            
            # 3. Interactive Filters
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                city_filter = st.selectbox("Filter by City", ["All Cities"] + list(df_lic['City'].dropna().unique()))
            with col_f2:
                status_filter = st.selectbox("Filter by Action Required", ["All Stores", "Pending / Has Remarks"])
                
            # Apply Filters
            filtered_df = df_lic.copy()
            if city_filter != "All Cities":
                filtered_df = filtered_df[filtered_df['City'] == city_filter]
            if status_filter == "Pending / Has Remarks":
                filtered_df = filtered_df[filtered_df['Remark'].notna()]
                
            st.markdown("---")
            st.markdown("### 🔍 Store License Details")
            
            # Helper function to clean up messy date formats or blank cells from Excel
            def format_date(d):
                if pd.isna(d) or str(d).strip().lower() in ['nan', 'nat']: 
                    return "N/A"
                if isinstance(d, datetime.datetime): 
                    return d.strftime('%d-%b-%Y')
                return str(d)[:10] # Fallback for string dates

            # 4. Presentable Executive View (Consolidated Store Cards)
            for _, row in filtered_df.iterrows():
                with st.expander(f"📍 {row['Location']} ({row['City']})"):
                    # Display all 5 licenses side-by-side using metrics
                    cols = st.columns(5)
                    cols[0].metric("FSSAI", format_date(row['FSSAI']))
                    cols[1].metric("Trade License", format_date(row['Trade']))
                    cols[2].metric("Fire NOC", format_date(row['Fire']))
                    cols[3].metric("Pollution CTO", format_date(row['Pollution CTO']))
                    cols[4].metric("Signage", format_date(row['Signage']))
                    
                    # Highlight remarks and pending actions below the dates
                    remark_text = row['Remark']
                    if pd.notna(remark_text):
                        st.warning(f"⚠️ **Status / Remarks:** {remark_text}")
                    else:
                        st.success("✅ All statutory licenses up to date.")
                        
        except Exception as e:
            st.error(f"❌ Could not process the uploaded file. Please make sure it's the correct format. Error: {e}")
    else:
        # Prompt the user to upload a file if nothing is uploaded yet
        st.info("👆 Please upload your 'License 90 Day tracker' Excel file above to view the dashboard.")
# ==========================================
# TAB 5: NSF AUDIT INTELLIGENCE
# ==========================================
with tab_nsf:
    st.subheader(f"📈 NSF Audit Intelligence (Cloud Database)")
    st.markdown("Real-time live NSF audits for Sub Franchise outlets pulled from Supabase.")
    
    if not subfranchise_df.empty and 'score' in subfranchise_df.columns:
        col_sf1, col_sf2, col_sf3, col_sf4 = st.columns(4)
        total_sf_audits = len(subfranchise_df)
        avg_sf_score = subfranchise_df['score'].mean()
        
        if 'result' in subfranchise_df.columns:
            pass_count = len(subfranchise_df[subfranchise_df['result'] == 'PASS'])
            pass_rate = (pass_count / total_sf_audits) * 100 if total_sf_audits > 0 else 0
        else:
            pass_count, pass_rate = 0, 0
        
        col_sf1.metric("Total SF Audits", total_sf_audits)
        col_sf2.metric("Average SF Score", f"{avg_sf_score:.2f}%")
        col_sf3.metric("Passed Audits", pass_count if 'result' in subfranchise_df.columns else "N/A")
        col_sf4.metric("Pass Rate", f"{pass_rate:.1f}%" if 'result' in subfranchise_df.columns else "N/A")

        if 'store_name' in subfranchise_df.columns:
            fig_sf = px.bar(
                subfranchise_df, x='store_name', y='score', text='score', 
                color='result' if 'result' in subfranchise_df.columns else 'score',
                color_discrete_map={'PASS': '#10B981', 'FAIL': '#EF4444'} if 'result' in subfranchise_df.columns else None,
                title=f"Sub Franchise NSF Scores"
            )
            fig_sf.update_traces(textposition='outside')
            fig_sf.update_layout(xaxis_tickangle=-15, margin=dict(t=40, b=40, l=0, r=0))
            st.plotly_chart(fig_sf, use_container_width=True)
        
        st.markdown("### 📋 NSF Audit Details")
        st.dataframe(subfranchise_df, use_container_width=True, hide_index=True)
    else:
        st.info("No Sub Franchise data available. Please upload a PDF using the uploader tool below.")
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
# TAB 7: SYSTEM ADMINISTRATION
# ==========================================
with tab_admin:
    st.subheader("⚙️ Store Portfolio & System Administration")
    with st.expander("➕ Add a New Store Location", expanded=False):
        with st.form("new_store_form"):
            new_name = st.text_input("Store Name")
            is_out = st.checkbox("Is Outstation?")
            if st.form_submit_button("Add Store") and new_name:
                st.session_state['master_stores'].append({'name': new_name, 'is_outstation': is_out})
                st.success("Added!")
                st.rerun()
