import streamlit as st
import datetime
from supabase import create_client, Client
import cloudinary
import cloudinary.uploader

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="CBTL Store Operations", 
    layout="centered", 
    initial_sidebar_state="collapsed",
    page_icon="☕"
)
import streamlit as st
import cloudinary
import cloudinary.uploader
@st.cache_data(ttl=3600)
def load_master_reference():
    try:
        if supabase:
            response = supabase.table("master_item_reference").select("*").eq("is_active", True).execute()
            return response.data
    except Exception as e:
        st.error(f"Failed to load master reference: {e}")
    return []

# --- SECURE CLOUDINARY INIT ---
cloudinary.config(
    cloud_name = st.secrets["CLOUDINARY_CLOUD_NAME"],
    api_key = st.secrets["CLOUDINARY_API_KEY"],
    api_secret = st.secrets["CLOUDINARY_API_SECRET"],
    secure = True
)

# --- MOBILE-FIRST CBTL CORPORATE UI THEME ---
st.markdown("""
    <style>
        /* Main background */
        .stApp {
            background-color: #F5F7FA;
            font-family: 'Arial', sans-serif;
        }
        
        /* Mobile-friendly large submit buttons */
        .stButton>button {
            width: 100%;
            border-radius: 8px;
            padding: 15px;
            font-size: 18px;
            font-weight: bold;
            background-color: #003366; /* CBTL Navy */
            color: white;
            border: none;
        }
        .stButton>button:hover {
            background-color: #002244;
            color: white;
        }
        
        /* Light Blue Informational Cards */
        div[data-testid="stExpander"] {
            background-color: #EAF2F8;
            border-radius: 10px;
            border: 1px solid #D6EAF8;
            margin-bottom: 10px;
        }
        
        /* Clean inputs for touch screens */
        .stSelectbox, .stTextInput, .stNumberInput {
            margin-bottom: 10px;
        }
        
        /* File uploader mobile styling */
        [data-testid="stFileUploadDropzone"] {
            background-color: #ffffff;
            border: 2px dashed #63B3ED;
            border-radius: 10px;
            padding: 20px;
        }
    </style>
""", unsafe_allow_html=True)
# --- PREMIUM CBTL AESTHETICS & CSS ---
premium_style = """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;600&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Montserrat', sans-serif;
    }
    
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .block-container {padding-top: 2rem; padding-bottom: 2rem;}
    
    /* Gold & Espresso Buttons */
    .stButton>button {
        background-color: #C5A059; 
        color: #1A110A; 
        border-radius: 6px;
        border: none;
        font-weight: 600;
        letter-spacing: 0.5px;
        transition: all 0.3s ease;
        width: 100%;
    }
    .stButton>button:hover {
        background-color: #B78727;
        color: #ffffff;
        box-shadow: 0px 4px 10px rgba(197, 160, 89, 0.4);
    }
    
    /* Premium Header Banner */
    .premium-banner {
        background: linear-gradient(135deg, #1A110A 0%, #2A1B12 100%);
        padding: 25px;
        border-radius: 12px;
        text-align: center;
        border: 1px solid #C5A059;
        box-shadow: 0 8px 20px rgba(0,0,0,0.15);
        margin-bottom: 30px;
    }
    .premium-banner h2 {
        color: #C5A059;
        margin: 0;
        font-weight: 600;
        font-size: 26px;
        letter-spacing: 1px;
    }
    .premium-banner p {
        color: #D3D3D3;
        margin: 10px 0 0 0;
        font-size: 11px;
        font-weight: 400;
        letter-spacing: 2px;
        text-transform: uppercase;
    }
    
    /* Form & Expander Styling */
    div[data-testid="stForm"] {
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        padding: 20px;
        background-color: #ffffff;
        box-shadow: 0 4px 6px rgba(0,0,0,0.02);
    }
    </style>
"""
st.markdown(premium_style, unsafe_allow_html=True)

# --- PROFESSIONAL CORPORATE BANNER ---
st.markdown(
    """
    <div class="premium-banner">
        <h2>☕ The Coffee Bean & Tea Leaf</h2>
        <p>Ekaagra Ostalaritza Private Limited &bull; QA & Compliance Vault</p>
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

try:
    supabase = init_supabase()
except Exception:
    supabase = None
    st.error("⚠️ Database configuration missing or invalid.")

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

# --- AUTO-SAVE HELPER ---
def get_draft_key(store_id):
    return f"draft_{store_id}_daily"

# --- SESSION STATE ---
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "store_id" not in st.session_state:
    st.session_state["store_id"] = ""
if "store_name" not in st.session_state:
    st.session_state["store_name"] = ""

# --- LOGIN SCREEN ---
def login_screen():
    st.markdown("<h3 style='text-align: center; color: #1A110A;'>Store Authentication</h3>", unsafe_allow_html=True)
    st.caption("<div style='text-align: center; margin-bottom: 20px;'>Authorized Personnel Only</div>", unsafe_allow_html=True)
    
    try:
        if supabase is None:
            return
            
        response = supabase.table("stores").select("store_id, store_name, secure_pin").execute()
        
        if not response.data:
            st.warning("⚠️ Connected to database, but no stores found. Please populate the 'stores' table.")
            return

        store_dict = {f"{row['store_id']} - {row['store_name']}": row for row in response.data}
        
        with st.form("login_form"):
            selected_display = st.selectbox("Select Your Location", options=list(store_dict.keys()))
            confirm_store = st.checkbox(f"I confirm I am logging in for {selected_display}")
            entered_pin = st.text_input("Enter 4-Digit Secure PIN", type="password", max_chars=4)
            
            if st.form_submit_button("Secure Login"):
                correct_pin = str(store_dict[selected_display]['secure_pin'])
                
                if not confirm_store:
                    st.error("❌ Please confirm your location selection.")
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
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown(f"<h3 style='color: #1A110A;'>📍 {st.session_state['store_name']}</h3>", unsafe_allow_html=True)
    with col2:
        st.button("🔒 Logout", on_click=lambda: st.session_state.update({"logged_in": False}))
    
    tab1, tab2, tab3, tab4 = st.tabs([
        "📋 Daily Audit", 
        "📥 Receiving", 
        "🔄 Transfer", 
        "🗑️ Wastage"
    ])
    
    # --- TAB 1: DAILY FSSAI & NSF CHECKLIST ---
    with tab1:
        st.markdown("#### FSSAI & NSF Operational Checklist")
        st.caption("Auto-save is enabled. Click 'Save Draft' to preserve your progress.")
        
        draft_key = get_draft_key(st.session_state['store_id'])
        
        # Initialize Draft State if empty
        if draft_key not in st.session_state:
            st.session_state[draft_key] = {
                "manager_name": "", "shift_idx": 0,
                "c_fssai": False, "c_med": False, "c_water": False,
                "c_soap": False, "c_temp": False, "c_uni": False, "c_jewel": False, "c_glove": False,
                "c_sink": False, "c_ppm": False, "c_cloth": False, "c_mop": False, "c_trash": False, "c_chem": False,
                "c_cold": False, "c_6in": False, "c_mrd": False, "c_ice": False, "c_tool": False, "c_esp": False,
                "c_pest": False, "c_gask": False, "c_drain": False, "c_struct": False
            }

        draft = st.session_state[draft_key]
        status_msg = st.empty()

        with st.form("daily_checklist_form"):
            manager_name = st.text_input("Manager on Duty Name", value=draft["manager_name"])
            shift = st.selectbox("Shift", ["Morning", "Evening"], index=draft["shift_idx"])
            
            st.markdown("### A. Admin & Documentation")
            c_fssai = st.checkbox("FSSAI License & Display Board prominently visible", value=draft["c_fssai"])
            c_med = st.checkbox("Current medical certificates available on-site", value=draft["c_med"])
            c_water = st.checkbox("IS-10500:2012 Water Analysis report on file", value=draft["c_water"])
            with st.expander("📸 Attach Proof: Documents / Board"):
                proof_a = st.camera_input("Capture Admin Proof", key="cam_a")
            
            st.markdown("### B. Team Hygiene")
            c_soap = st.checkbox("Handwash sinks fully stocked with paper towels & soap", value=draft["c_soap"])
            c_temp = st.checkbox("Handwash water temperature reaches 38°C (±2°C)", value=draft["c_temp"])
            c_uni = st.checkbox("Staff in clean, approved uniforms with aprons tied", value=draft["c_uni"])
            c_jewel = st.checkbox("Zero Jewellery policy strictly enforced", value=draft["c_jewel"])
            c_glove = st.checkbox("Gloves and bright bandages stocked and used", value=draft["c_glove"])
            with st.expander("📸 Attach Proof: Handwash Station"):
                proof_b = st.camera_input("Capture Hygiene Proof", key="cam_b")
            
            st.markdown("### C. Sanitation")
            c_sink = st.checkbox("3-Compartment sink set up correctly", value=draft["c_sink"])
            c_ppm = st.checkbox("Sanitizer maintained at 50-100 PPM", value=draft["c_ppm"])
            c_cloth = st.checkbox("Wiping cloths submerged in sanitizer", value=draft["c_cloth"])
            c_mop = st.checkbox("Mops stored clean and elevated", value=draft["c_mop"])
            c_trash = st.checkbox("Trash bins covered and foot-operated", value=draft["c_trash"])
            c_chem = st.checkbox("Chemical spray bottles clearly labeled", value=draft["c_chem"])
            with st.expander("📸 Attach Proof: Sanitizer Test Strip"):
                proof_c = st.camera_input("Capture Sanitation Proof", key="cam_c")
            
            st.markdown("### D. Product & Equipment")
            c_cold = st.checkbox("Cold holding maintained < 5°C / 41°F", value=draft["c_cold"])
            c_6in = st.checkbox("All goods stored 6 inches off floor", value=draft["c_6in"])
            c_mrd = st.checkbox("Zero expired goods; MRD labels applied", value=draft["c_mrd"])
            c_ice = st.checkbox("Ice machine 100% mold-free", value=draft["c_ice"])
            c_tool = st.checkbox("Thermometers calibrated & scoops available", value=draft["c_tool"])
            c_esp = st.checkbox("Espresso calibrated 18-26s (14g dose)", value=draft["c_esp"])
            with st.expander("📸 Attach Proof: MRD Labels"):
                proof_d = st.camera_input("Capture Product Proof", key="cam_d")
            
            st.markdown("### E. Facility Integrity")
            c_pest = st.checkbox("Zero pests; fly catchers ON", value=draft["c_pest"])
            c_gask = st.checkbox("Refrigeration gaskets clean/untorn", value=draft["c_gask"])
            c_drain = st.checkbox("Drains unclogged and odor-free", value=draft["c_drain"])
            c_struct = st.checkbox("No structural seepage or peeling paint", value=draft["c_struct"])
            with st.expander("📸 Attach Proof: Clean Gaskets"):
                proof_e = st.camera_input("Capture Facility Proof", key="cam_e")
            
            st.markdown("---")
            
            # Action Buttons
            col_a, col_b = st.columns(2)
            with col_a:
                btn_save_draft = st.form_submit_button("💾 Save Draft Progress")
            with col_b:
                btn_submit = st.form_submit_button("🚀 Submit Final Audit")

            # Handle Actions
            if btn_save_draft or btn_submit:
                # Always update draft state on either button press
                st.session_state[draft_key] = {
                    "manager_name": manager_name, "shift_idx": 0 if shift == "Morning" else 1,
                    "c_fssai": c_fssai, "c_med": c_med, "c_water": c_water,
                    "c_soap": c_soap, "c_temp": c_temp, "c_uni": c_uni, "c_jewel": c_jewel, "c_glove": c_glove,
                    "c_sink": c_sink, "c_ppm": c_ppm, "c_cloth": c_cloth, "c_mop": c_mop, "c_trash": c_trash, "c_chem": c_chem,
                    "c_cold": c_cold, "c_6in": c_6in, "c_mrd": c_mrd, "c_ice": c_ice, "c_tool": c_tool, "c_esp": c_esp,
                    "c_pest": c_pest, "c_gask": c_gask, "c_drain": c_drain, "c_struct": c_struct
                }
                
                if btn_save_draft:
                    status_msg.success("✅ Progress saved locally. You can safely close or refresh.")

                if btn_submit:
                    if not manager_name:
                        st.error("❌ Manager Name is required for final submission.")
                    else:
                        with st.spinner("Encrypting data & pushing to Central QA Vault..."):
                            url_a = upload_photo(proof_a, st.session_state["store_id"], "admin") if proof_a else None
                            url_b = upload_photo(proof_b, st.session_state["store_id"], "hygiene") if proof_b else None
                            url_c = upload_photo(proof_c, st.session_state["store_id"], "sanitation") if proof_c else None
                            url_d = upload_photo(proof_d, st.session_state["store_id"], "product") if proof_d else None
                            url_e = upload_photo(proof_e, st.session_state["store_id"], "facility") if proof_e else None
                            
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
                                # Clear draft upon successful submission
                                del st.session_state[draft_key]
                                status_msg.success("🎉 Audit successfully locked in Central QA Vault!")
                                st.balloons()
                            except Exception as e:
                                st.error(f"Database error: {e}")
                            
   # (Your Tab 1 code remains exactly the same above this, just add this caption above your camera inputs)
    # st.caption("📱 *Note: Mobile camera initialization may take a few seconds.*")

# ==========================================
    # TAB 2: RECEIVING & INVOICE LOG
    # ==========================================
    with tab2:
        st.subheader("📦 Goods Receiving & Verification")
        st.caption("Log incoming deliveries, verify core temperatures, and archive vendor challans.")
        
        with st.form("receiving_form"):
            vendor_name = st.text_input("Vendor Name / Supplier")
            invoice_number = st.text_input("Invoice / Chalan Number")
            received_temp = st.number_input("Delivery Core Temperature (°C)", step=0.1, format="%.1f")
            
            st.markdown("### 📸 Invoice / Chalan Upload")
            st.caption("📱 *Click the button below to activate the camera on-demand.*")
            
            # --- ON-DEMAND CAMERA TOGGLE ---
            if "enable_recv_cam" not in st.session_state:
                st.session_state["enable_recv_cam"] = False
                
            col_cam1, col_cam2 = st.columns([1, 2])
            with col_cam1:
                if st.form_submit_button("📷 Open/Close Camera"):
                    st.session_state["enable_recv_cam"] = not st.session_state["enable_recv_cam"]
            
            invoice_photo = None
            if st.session_state["enable_recv_cam"]:
                invoice_photo = st.camera_input("Capture Invoice Image", key="recv_photo")
            else:
                invoice_photo = st.file_uploader("Or Upload Image File", type=['png', 'jpg', 'jpeg'], key="recv_file")
            
            remarks = st.text_area("Receiving Remarks / Quality Check Notes")
            
            # --- SUBMIT & CLOUD SAVE LOGIC ---
            if st.form_submit_button("✅ Save Receiving Log", type="primary"):
                if not vendor_name or not invoice_number:
                    st.error("❌ Please fill in the Vendor Name and Invoice Number.")
                else:
                    with st.spinner("Uploading proof and saving receiving log..."):
                        try:
                            image_url = ""
                            # Upload to Cloudinary if photo/file is attached
                            if invoice_photo is not None and cloudinary_configured:
                                upload_result = cloudinary.uploader.upload(
                                    invoice_photo, 
                                    folder=f"cbtl/{st.session_state.get('store_id', 'store')}/receiving"
                                )
                                image_url = upload_result.get("secure_url", "")
                            
                            receiving_data = {
                                "store_id": st.session_state.get("store_id", "Default Store"),
                                "vendor_name": vendor_name,
                                "invoice_number": invoice_number,
                                "received_temp": received_temp,
                                "image_url": image_url,
                                "remarks": remarks
                            }
                            
                            if supabase is not None:
                                supabase.table("store_receiving_logs").insert(receiving_data).execute()
                                st.success("✅ Receiving log saved successfully with secure cloud archive!")
                            else:
                                st.error("Database connection is not active.")
                                
                        except Exception as e:
                            st.error(f"❌ Failed to save receiving log: {e}")
    
   # ==========================================
    # TAB 3: STOCK & INTERNAL TRANSFERS
    # ==========================================
    with tab3:
        st.subheader("🔄 Stock Transfer & Thaw Log")
        st.caption("Manage Inter-Store dispatch and strict FDU Chiller shelf-life protocols.")
        
        transfer_type = st.radio("Select Transfer Protocol", ["Freezer to FDU Chiller (Internal Thaw)", "Inter-Store Dispatch (External)"])
        
        if transfer_type == "Freezer to FDU Chiller (Internal Thaw)":
            # 1. Fetch live data from Supabase
            master_data = load_master_reference()
            
            # 2. Build dictionaries dynamically using the generic column names
            ITEM_MAPPING = {item['warehouse_item_name']: item['store_retail_name'] for item in master_data}
            SHELF_LIFE_HOURS = {item['store_retail_name']: item['shelf_life_hours'] for item in master_data}
            TEMP_ZONES = {item['store_retail_name']: item['temperature_zone'] for item in master_data}
            
            with st.form("fdu_transfer_form"):
                wh_item = st.selectbox("Select Warehouse Item (Invoice Name)", ["Select Item..."] + list(ITEM_MAPPING.keys()))
                
                # Auto-calculate and display Name B, Shelf Life, and Temp Zone
                if wh_item != "Select Item...":
                    store_name = ITEM_MAPPING[wh_item]
                    shelf_life = SHELF_LIFE_HOURS.get(store_name, 24)
                    temp_zone = TEMP_ZONES.get(store_name, "Chiller Zone (1-5°C)")
                    
                    now = datetime.datetime.now()
                    expiry_time = now + datetime.timedelta(hours=shelf_life)
                    
                    st.info(f"""
                    🏷️ **Store Retail Name:** {store_name}
                    ⏳ **FSSAI Shelf Life:** {shelf_life} hours
                    🌡️ **Storage Requirement:** {temp_zone}
                    """)
                    
                    if shelf_life == 0:
                        st.error("🚨 **RED-LINE PROTOCOL:** Do not thaw. Cook directly from Freezer Zone (<-18°C).")
                    else:
                        st.warning(f"🚨 **MRD Label Required:** Must be discarded by **{expiry_time.strftime('%d-%b-%Y %I:%M %p')}**")
                
                transfer_qty = st.number_input("Quantity Transferred to FDU", min_value=1, step=1)
                fdu_temp = st.number_input("Current FDU Chiller Temp (°C)", value=4.0, step=0.1)
                
                if st.form_submit_button("🔄 Log FDU Transfer", type="primary"):
                    if wh_item == "Select Item...":
                        st.error("❌ Please select an item to transfer.")
                    elif shelf_life == 0:
                        st.error("❌ Item cannot be transferred to FDU. Red-Line protocol enforced.")
                    else:
                        with st.spinner("Logging FDU transfer and locking shelf life..."):
                            fdu_data = {
                                "store_id": st.session_state["store_id"],
                                "warehouse_name": wh_item,
                                "store_name": store_name,
                                "quantity": transfer_qty,
                                "fdu_temp": fdu_temp,
                                "thaw_start_time": now.strftime('%Y-%m-%d %H:%M:%S'),
                                "discard_time": expiry_time.strftime('%Y-%m-%d %H:%M:%S')
                            }
                            try:
                                if supabase:
                                    supabase.table("store_fdu_transfers").insert(fdu_data).execute()
                                    st.success(f"✅ Transfer logged! Ensure {store_name} is labelled.")
                            except Exception as e:
                                st.error(f"Database error: {e}")
                                
        elif transfer_type == "Inter-Store Dispatch (External)":
            with st.form("transfer_form"):
                # Removed "FDU Chiller" from this list as it is now handled above
                destination = st.selectbox("Destination", ["DLF Mid Town Plaza", "Janakpuri, Delhi", "GK1, Delhi"])
                transfer_items = st.text_area("Items Transferred (Include Quantities)")
                dispatch_temp = st.number_input("Dispatch Core Temp (°C)", step=0.1, format="%.1f")
                transfer_remarks = st.text_input("Remarks / Condition of Goods")
                
                if st.form_submit_button("🔄 Initiate Dispatch", type="primary"):
                    if not transfer_items:
                        st.error("❌ Please list the items being transferred.")
                    else:
                        with st.spinner("Logging transfer..."):
                            transfer_data = {
                                "store_id": st.session_state["store_id"],
                                "destination": destination,
                                "items": transfer_items,
                                "dispatch_temp": dispatch_temp,
                                "remarks": transfer_remarks
                            }
                            try:
                                if supabase:
                                    supabase.table("store_transfers").insert(transfer_data).execute()
                                    st.success("✅ Dispatch logged successfully!")
                            except Exception as e:
                                st.error(f"Database error: {e}")
    # ==========================================
    # TAB 4: WASTAGE & DISCARD
    # ==========================================
    with tab4:
        st.subheader("🗑️ Wastage & Quality Discard Log")
        st.caption("Record expired or damaged goods strictly per NSF standards.")
        
        with st.form("wastage_form"):
            waste_item = st.text_input("Item Name")
            col_w1, col_w2 = st.columns(2)
            with col_w1:
                waste_qty = st.number_input("Quantity Discarded", min_value=0.0, step=0.5)
            with col_w2:
                waste_reason = st.selectbox("Reason for Discard", [
                    "Expired / Out of Date", 
                    "Temperature Abuse", 
                    "Physical Damage", 
                    "Quality Standard Failure"
                ])
            
            st.markdown("### 📸 Wastage Evidence")
            st.caption("📱 *Note: Please capture a clear photo of the discarded items.*")
            waste_photo = st.camera_input("Capture Discard Photo", key="waste_photo")
            
            if st.form_submit_button("🗑️ Log Wastage", type="primary"):
                if not waste_item or waste_qty <= 0:
                    st.error("❌ Valid Item Name and Quantity are required.")
                else:
                    with st.spinner("Logging wastage record..."):
                        waste_url = upload_photo(waste_photo, st.session_state["store_id"], "wastage") if waste_photo else None
                        
                        waste_data = {
                            "store_id": st.session_state["store_id"],
                            "item_name": waste_item,
                            "quantity": waste_qty,
                            "reason": waste_reason,
                            "evidence_url": waste_url
                        }
                        try:
                            if supabase:
                                supabase.table("store_wastage").insert(waste_data).execute()
                                st.success("✅ Wastage record permanently saved to the vault!")
                        except Exception as e:
                            st.error(f"Database error: {e}")

# --- APP ROUTING ---
if st.session_state["logged_in"]:
    store_dashboard()
else:
    login_screen()
