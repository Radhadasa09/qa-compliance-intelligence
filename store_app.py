import streamlit as st
import datetime
from supabase import create_client, Client
import cloudinary
import cloudinary.uploader

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="CBTL Store Operations", page_layout="centered", initial_sidebar_state="collapsed")

# --- HIDE STREAMLIT BRANDING & APPLY QA HEADER STYLING ---
hide_streamlit_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .block-container {padding-top: 2rem; padding-bottom: 2rem;}
    </style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# --- PROFESSIONAL CORPORATE BANNER ---
st.markdown(
    """
    <div style="background-color: #1a1a1a; padding: 18px; border-radius: 8px; text-align: center; border: 1px solid #333; margin-bottom: 25px;">
        <h2 style="color: #ffffff; margin: 0; font-family: sans-serif; font-size: 22px;">☕ The Coffee Bean & Tea Leaf (CBTL) India</h2>
        <p style="color: #b0b0b0; margin: 6px 0 0 0; font-size: 13px; font-weight: 500; letter-spacing: 0.5px;">
            EKAAGRA OSTALARITZA PRIVATE LIMITED &bull; QA & COMPLIANCE VAULT
        </p>
    </div>
    """,
    unsafe_allow_html=True
)
# --- INITIALIZATION (DB & CLOUD) ---
@st.cache_resource
def init_supabase() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_supabase()

cloudinary.config(
    cloud_name=st.secrets["CLOUDINARY_CLOUD_NAME"],
    api_key=st.secrets["CLOUDINARY_API_KEY"],
    api_secret=st.secrets["CLOUDINARY_API_SECRET"],
    secure=True
)

def upload_photo(file_buffer, store_id, folder_name):
    """Uploads file to Cloudinary and returns the secure URL"""
    try:
        res = cloudinary.uploader.upload(file_buffer, folder=f"cbtl/{store_id}/{folder_name}")
        return res.get("secure_url")
    except Exception as e:
        st.error(f"Upload failed: {e}")
        return None

# --- SESSION STATE ---
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "store_id" not in st.session_state:
    st.session_state["store_id"] = ""
if "store_name" not in st.session_state:
    st.session_state["store_name"] = ""
# --- LOGIN SCREEN ---
def login_screen():
    st.title("☕ CBTL Store Login")
    st.caption("FSSAI & NSF Operational Compliance Portal")
    
    try:
        # Fetch live stores and PINs from Supabase
        response = supabase.table("stores").select("store_id, store_name, secure_pin").execute()
        
        if not response.data:
            st.warning("⚠️ Connected to database, but no stores found. Please check Supabase table.")
            return

        store_dict = {f"{row['store_id']} - {row['store_name']}": row for row in response.data}
        
        with st.form("login_form"):
            selected_display = st.selectbox("Select Your Store", options=list(store_dict.keys()))
            confirm_store = st.checkbox(f"I confirm I am logging in for {selected_display}")
            entered_pin = st.text_input("Enter Store PIN", type="password", max_chars=4)
            
            if st.form_submit_button("Proceed to Outlet"):
                correct_pin = store_dict[selected_display]['secure_pin']
                
                if not confirm_store:
                    st.error("❌ Please check the confirmation box.")
                elif entered_pin != correct_pin:
                    st.error("❌ Incorrect PIN. Access denied.")
                else:
                    st.session_state["logged_in"] = True
                    st.session_state["store_id"] = store_dict[selected_display]['store_id']
                    st.session_state["store_name"] = store_dict[selected_display]['store_name']
                    st.rerun()
                    
    except Exception as e:
        st.error(f"Database connection error: {e}")
# --- MAIN OUTLET DASHBOARD ---
def store_dashboard():
    st.header(f"{st.session_state['store_name']}")
    st.button("Logout", on_click=lambda: st.session_state.update({"logged_in": False}))
    
    # Reordered Tabs: Checklist is now Tab 1
    tab1, tab2, tab3, tab4 = st.tabs([
        "📋 Daily Checklist", 
        "📥 Receiving", 
        "🔄 FDU Transfer", 
        "🗑️ Wastage"
    ])
    
    # --- TAB 1: DAILY FSSAI & NSF CHECKLIST (LIVE) ---
    with tab1:
        st.subheader("FSSAI & NSF Shift Checklist")
        st.caption("All metrics must pass for audit readiness.")
        
        with st.form("daily_checklist_form"):
            manager_name = st.text_input("Manager on Duty Name")
            shift = st.selectbox("Shift", ["Morning", "Evening"])
            
            st.markdown("### A. Admin & Documentation")
            c_fssai = st.checkbox("FSSAI License & Display Board prominently visible")
            c_med = st.checkbox("Current medical certificates available on-site for all team members")
            c_water = st.checkbox("IS-10500:2012 Water Analysis report on file")
            proof_a = st.camera_input("Proof: Documents / Board", key="cam_a")
            
            st.markdown("### B. Team Hygiene")
            c_soap = st.checkbox("Handwash sinks fully stocked with paper towels & soap")
            c_temp = st.checkbox("Handwash water temperature reaches 38°C (±2°C)")
            c_uni = st.checkbox("Staff in clean, approved uniforms with aprons tied")
            c_jewel = st.checkbox("Zero Jewellery policy strictly enforced")
            c_glove = st.checkbox("Gloves and bright bandages stocked and used")
            proof_b = st.camera_input("Proof: Handwash Station", key="cam_b")
            
            st.markdown("### C. Sanitation")
            c_sink = st.checkbox("3-Compartment sink set up correctly")
            c_ppm = st.checkbox("Sanitizer maintained at 50-100 PPM")
            c_cloth = st.checkbox("Wiping cloths submerged in sanitizer")
            c_mop = st.checkbox("Mops stored clean and elevated")
            c_trash = st.checkbox("Trash bins covered and foot-operated")
            c_chem = st.checkbox("Chemical spray bottles clearly labeled")
            proof_c = st.camera_input("Proof: Sanitizer Test Strip", key="cam_c")
            
            st.markdown("### D. Product & Equipment")
            c_cold = st.checkbox("Cold holding maintained < 5°C / 41°F")
            c_6in = st.checkbox("All goods stored 6 inches off floor")
            c_mrd = st.checkbox("Zero expired goods; MRD labels applied")
            c_ice = st.checkbox("Ice machine 100% mold-free")
            c_tool = st.checkbox("Thermometers calibrated & scoops available")
            c_esp = st.checkbox("Espresso calibrated 18-26s (14g dose)")
            proof_d = st.camera_input("Proof: MRD Labels", key="cam_d")
            
            st.markdown("### E. Facility Integrity")
            c_pest = st.checkbox("Zero pests; fly catchers ON")
            c_gask = st.checkbox("Refrigeration gaskets clean/untorn")
            c_drain = st.checkbox("Drains unclogged and odor-free")
            c_struct = st.checkbox("No structural seepage or peeling paint")
            proof_e = st.camera_input("Proof: Clean Gaskets", key="cam_e")
            
            st.markdown("---")
            if st.form_submit_button("Submit Daily Audit"):
                if not manager_name:
                    st.error("❌ Manager Name is required.")
                else:
                    with st.spinner("Uploading photos and saving to Supabase..."):
                        # Upload photos to Cloudinary
                        url_a = upload_photo(proof_a, st.session_state["store_id"], "admin") if proof_a else None
                        url_b = upload_photo(proof_b, st.session_state["store_id"], "hygiene") if proof_b else None
                        url_c = upload_photo(proof_c, st.session_state["store_id"], "sanitation") if proof_c else None
                        url_d = upload_photo(proof_d, st.session_state["store_id"], "product") if proof_d else None
                        url_e = upload_photo(proof_e, st.session_state["store_id"], "facility") if proof_e else None
                        
                        # Save to Supabase
                        audit_data = {
                            "store_id": st.session_state["store_id"],
                            "manager_name": manager_name,
                            "shift": shift,
                            "admin_fssai_visible": c_fssai, "admin_medical_certs": c_med, "admin_water_report": c_water, "admin_proof_url": url_a,
                            "hygiene_handwash_stocked": c_soap, "hygiene_water_temp": c_temp, "hygiene_uniforms": c_uni, "hygiene_zero_jewelry": c_jewel, "hygiene_gloves": c_glove, "hygiene_proof_url": url_b,
                            "sanitation_sink_setup": c_sink, "sanitation_ppm_level": c_ppm, "sanitation_cloths_stored": c_cloth, "sanitation_mops_elevated": c_mop, "sanitation_trash_covered": c_trash, "sanitation_chemicals_labeled": c_chem, "sanitation_proof_url": url_c,
                            "product_cold_holding": c_cold, "product_6_inch_rule": c_6in, "product_mrd_labels": c_mrd, "product_ice_machine": c_ice, "product_tools_calibrated": c_tool, "product_espresso_calibrated": c_esp, "product_proof_url": url_d,
                            "facility_zero_pests": c_pest, "facility_gaskets_intact": c_gask, "facility_drains_clean": c_drain, "facility_structural_integrity": c_struct, "facility_proof_url": url_e
                        }
                        try:
                            supabase.table("daily_audits").insert(audit_data).execute()
                            st.success("✅ Audit securely saved to Central QA Vault!")
                            st.balloons()
                        except Exception as e:
                            st.error(f"Database error: {e}")

    # --- TAB 2 & 3 (Preserved UI - Pending DB wiring) ---
    with tab2:
        st.subheader("Receive Warehouse Delivery")
        st.info("Inventory DB connection pending. UI preserved.")
        
    with tab3:
        st.subheader("Freezer to FDU Chiller Transfer")
        st.info("Transfer DB connection pending. UI preserved.")

    # --- TAB 4 (Preserved UI) ---
    with tab4:
        st.subheader("Register Wastage")
        st.info("Wastage DB connection pending. UI preserved.")

# --- APP ROUTING (CRITICAL FOR RENDERING UI) ---
if st.session_state["logged_in"]:
    store_dashboard()
else:
    login_screen()
