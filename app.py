import streamlit as st
from supabase import create_client, Client
import pandas as pd
import plotly.express as px
import os
import datetime
import io
import copy

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
# --- 3. NSF AUDIT CLOUD UPLOADER (Direct PDF Reader) ---
st.subheader("☁️ NSF Audit Cloud Uploader (Direct PDF)")
with st.expander("Upload Official NSF Audit PDF", expanded=False):
    uploaded_pdf = st.file_uploader("Upload Official NSF Audit PDF", type=["pdf"])
    
    if uploaded_pdf:
        try:
            import pdfplumber
            extracted_rows = []
            
            # Open and parse the PDF tables page-by-page
            with pdfplumber.open(uploaded_pdf) as pdf:
                for page in pdf.pages:
                    tables = page.extract_tables()
                    for table in tables:
                        for row in table:
                            extracted_rows.append(row)
            
            if extracted_rows:
                standard_columns = [
                    "Audit Code", "Postal Code", "Address Line", "City", "Site Name", "Site Code", 
                    "Score", "Result", "Grade", "CAR Status", "Audit Date", "Time Zone", 
                    "Audit Type", "Audit Category", "Audit Time", "Audit Status", 
                    "Customer Name", "Level 1", "Level 2", "Level 3", "Level 4", "Level 5", "Level 6"
                ]
                
                # Filter out repeated table headers or empty rows extracted from page breaks
              # Filter out repeated table headers or empty rows extracted from page breaks
clean_data = []
for row in extracted_rows:
    row_text = "".join([str(cell) for cell in row if cell])
    # Skip rows that contain duplicate PDF header fragments or are empty
    if not row_text.strip() or "Audit Code" in row_text or "Site Name" in row_text or "Postal" in row_text:
        continue
    clean_data.append(row)
                
                df_upload = pd.DataFrame(clean_data)
                
                # Map columns precisely to match database schema length
                if len(df_upload.columns) >= len(standard_columns):
                    df_upload = df_upload.iloc[:, :len(standard_columns)]
                    df_upload.columns = standard_columns
                else:
                    df_upload.columns = [f"Col_{i}" for i in range(len(df_upload.columns))]
                
                st.write(f"✅ Successfully extracted {len(df_upload)} clean audit records from PDF.")
                st.dataframe(df_upload.head(3))
                
                if st.button("Push PDF Data to Database", type="primary"):
                    if supabase is None:
                        st.error("❌ Database connection is inactive. Check credentials.")
                    else:
                        try:
                            records = df_upload.to_dict(orient="records")
                            supabase.table("nsf_audits").insert(records).execute()
                            st.success(f"✅ {len(records)} records uploaded successfully from PDF!")
                            st.cache_data.clear()
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Upload failed: {e}")
            else:
                st.warning("⚠️ No structured tables were detected in this PDF layout.")
        except Exception as e:
            st.error(f"❌ Error parsing PDF: {e}")

# Fetch live data from Supabase
df_db = load_nsf_audits()

# Process dynamic categorizations for Ekaagra Direct (189 series) vs Sub Franchise
if not df_db.empty and 'Site Code' in df_db.columns:
    df_db['Site Code'] = df_db['Site Code'].astype(str)
    df_db['Type'] = df_db['Site Code'].apply(lambda x: "Ekaagra Direct" if x.startswith("189") else "Sub Franchise")
    ekaagra_df = df_db[df_db['Type'] == "Ekaagra Direct"]
    subfranchise_df = df_db[df_db['Type'] == "Sub Franchise"]
else:
    ekaagra_df = pd.DataFrame()
    subfranchise_df = pd.DataFrame()
# --- SIDEBAR: GLOBAL CONTROLS ---
st.sidebar.title("⚙️ Dashboard Controls")
st.sidebar.markdown("**Head of QA & Compliance:** Girish Kumar")

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
st.title(f"🛡️ QA & Compliance Leadership Briefing — {selected_month}")
st.markdown("Real-time oversight of Ekaagra Master Franchise Operations, Licensing, Supply Chain, and Sub Franchise compliance.")
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
    st.subheader(f"📈 Cloud Database Summary ({selected_month})")
    
    col1, col2, col3, col4 = st.columns(4)
    total_db_audits = len(df_db) if not df_db.empty else 0
    ekaagra_avg = ekaagra_df['Score'].mean() if not ekaagra_df.empty and 'Score' in ekaagra_df else 0
    sub_avg = subfranchise_df['Score'].mean() if not subfranchise_df.empty and 'Score' in subfranchise_df else 0
    
    col1.metric("Total Network Audits (Cloud)", total_db_audits)
    col2.metric("Ekaagra Direct Avg Score", f"{ekaagra_avg:.1f}%" if ekaagra_avg > 0 else "N/A")
    col3.metric("Sub Franchise Avg Score", f"{sub_avg:.1f}%" if sub_avg > 0 else "N/A")
    
    stores_with_lic_issues = int(df_monthly_filtered['has_license_issue'].sum()) if not df_monthly_filtered.empty else 0
    col4.metric("Stores with License Flags", f"{stores_with_lic_issues}", delta=f"{stores_with_lic_issues} Flags", delta_color="inverse")

    st.markdown("---")

    if not ekaagra_df.empty and 'Score' in ekaagra_df.columns and 'Store Name' in ekaagra_df.columns:
        st.markdown("### 🏬 Ekaagra Direct Operations (189 Series)")
        fig_nsf = px.bar(
            ekaagra_df, x='Store Name', y='Score', text='Score',
            title=f"Ekaagra Direct Outlets NSF Scores",
            color='Result' if 'Result' in ekaagra_df.columns else 'Score', 
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
# TAB 2: RETAIL OPERATIONS (Data Entry)
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

# ==========================================
# TAB 3: VENDOR & SUPPLY CHAIN
# ==========================================
with tab_supply:
    st.subheader(f"Vendor Audit Performance — {selected_month}")
    current_vendors = st.session_state['vendor_db'].get(selected_month, [])
    
    with st.form("vendor_form"):
        col_v1, col_v2, col_v3 = st.columns(3)
        with col_v1: v_name = st.text_input("Vendor Name")
        with col_v2: 
            v_cat = st.selectbox("Category", ["Pest Control", "Supply Chain", "Packaging", "Chemicals"])
            v_score = st.text_input("Score / %")
        with col_v3: v_status = st.selectbox("Status", ["Passed", "Conditionally Approved", "Failed"])
        v_remark = st.text_input("Remark")
        
        if st.form_submit_button("Add Vendor Audit") and v_name:
            if selected_month not in st.session_state['vendor_db']: st.session_state['vendor_db'][selected_month] = []
            st.session_state['vendor_db'][selected_month].append({
                "vendor": v_name, "category": v_cat, "score": v_score, "status": v_status, "remark": v_remark
            })
            st.success("Vendor added!")
            st.rerun()
            
    if current_vendors:
        st.dataframe(pd.DataFrame(current_vendors), use_container_width=True, hide_index=True)

# ==========================================
# TAB 4: LICENSE SUMMARY
# ==========================================
with tab_lic_summary:
    st.subheader(f"📜 License Compliance Summary — {selected_month}")
    lic_summary_rows = []
    for _, row in df_stores.iterrows():
        m_data = get_store_monthly(row['name'], selected_month)
        for l_name, l_info in m_data['licenses'].items():
            lic_summary_rows.append({
                "Store Name": row['name'], "License Name": l_name,
                "Applicable": "Yes" if l_info['applicable'] else "No",
                "Status": l_info['status'], "Expiry Date": str(l_info['expiry'])
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
    current_cal = st.session_state['qa_calendar_db'].get(selected_month, [])
    
    with st.expander("➕ Add New Schedule Entry", expanded=False):
        with st.form("add_cal_form"):
            c1, c2, c3 = st.columns(3)
            with c1: cal_date = st.text_input("Date (e.g. 03)")
            with c2: cal_day = st.selectbox("Day", ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"])
            with c3: cal_activity = st.text_input("Activity / Location")
                
            if st.form_submit_button("Add to Calendar") and cal_date and cal_activity:
                if selected_month not in st.session_state['qa_calendar_db']: st.session_state['qa_calendar_db'][selected_month] = []
                st.session_state['qa_calendar_db'][selected_month].append({"date": cal_date, "day": cal_day, "activity": cal_activity})
                st.success("Entry added!")
                st.rerun()
                
    if current_cal:
        st.dataframe(pd.DataFrame(current_cal), use_container_width=True, hide_index=True)

# ==========================================
# TAB 6: SUB FRANCHISE
# ==========================================
with tab_subfranchise:
    st.subheader(f"🤝 Sub Franchise Audit Summary (Cloud Database)")
    st.markdown("Real-time live NSF audits for Sub Franchise outlets pulled from Supabase.")
    
    if not subfranchise_df.empty and 'Score' in subfranchise_df.columns:
        col_sf1, col_sf2, col_sf3, col_sf4 = st.columns(4)
        total_sf_audits = len(subfranchise_df)
        avg_sf_score = subfranchise_df['Score'].mean()
        
        # Check if 'Result' column exists to calculate pass rate dynamically
        if 'Result' in subfranchise_df.columns:
            pass_count = len(subfranchise_df[subfranchise_df['Result'] == 'PASS'])
            pass_rate = (pass_count / total_sf_audits) * 100 if total_sf_audits > 0 else 0
        else:
            pass_count, pass_rate = 0, 0
        
        col_sf1.metric("Total SF Audits", total_sf_audits)
        col_sf2.metric("Average SF Score", f"{avg_sf_score:.2f}%")
        col_sf3.metric("Passed Audits", pass_count if 'Result' in subfranchise_df.columns else "N/A")
        col_sf4.metric("Pass Rate", f"{pass_rate:.1f}%" if 'Result' in subfranchise_df.columns else "N/A")

        if 'Store Name' in subfranchise_df.columns:
            fig_sf = px.bar(
                subfranchise_df, x='Store Name', y='Score', text='Score', 
                color='Result' if 'Result' in subfranchise_df.columns else 'Score',
                color_discrete_map={'PASS': '#10B981', 'FAIL': '#EF4444'} if 'Result' in subfranchise_df.columns else None,
                title=f"Sub Franchise NSF Scores"
            )
            fig_sf.update_traces(textposition='outside')
            fig_sf.update_layout(xaxis_tickangle=-15, margin=dict(t=40, b=40, l=0, r=0))
            st.plotly_chart(fig_sf, use_container_width=True)
        
        st.markdown("### 📋 NSF Audit Details")
        st.dataframe(subfranchise_df, use_container_width=True, hide_index=True)
    else:
        st.info("No Sub Franchise data available. Please upload a CSV using the uploader tool above.")

# ==========================================
# TAB 7: REPORTS & ARCHIVE
# ==========================================
with tab_reports:
    st.subheader(f"📑 PDF Report Generation")
    
    def generate_pdf(month_str, records, vendors, calendar_entries):
        if FPDF is None: return None
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=14, style='B')
        pdf.cell(200, 10, txt=f"QA & Compliance Report - {month_str}", ln=True, align='C')
        return pdf.output(dest='S').encode('latin-1')

    if st.button("Generate Basic PDF Report", type="primary"):
        pdf_bytes = generate_pdf(selected_month, monthly_records, st.session_state['vendor_db'].get(selected_month, []), st.session_state['qa_calendar_db'].get(selected_month, []))
        if pdf_bytes:
            st.session_state['pdf_archive'][selected_month] = pdf_bytes
            st.success("PDF generated!")
        else:
            st.error("fpdf2 missing.")
            
    if selected_month in st.session_state['pdf_archive']:
        st.download_button(label=f"📥 Download PDF", data=st.session_state['pdf_archive'][selected_month], file_name=f"QA_{selected_month}.pdf", mime="application/pdf")

# ==========================================
# TAB 8: SYSTEM ADMINISTRATION
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
