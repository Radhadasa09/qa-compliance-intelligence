import streamlit as st
import datetime
import pandas as pd
from supabase import create_client, Client
import cloudinary
import cloudinary.uploader
import json
from PIL import Image, ImageDraw, ImageFont
import io

# --- PAGE CONFIGURATION (Must be first) ---
st.set_page_config(
    page_title="CBTL Store Operations", 
    layout="centered", 
    initial_sidebar_state="collapsed",
    page_icon="☕"
)

# --- SECURE CLOUDINARY INIT ---
try:
    cloudinary.config(
        cloud_name = st.secrets["CLOUDINARY_CLOUD_NAME"],
        api_key = st.secrets["CLOUDINARY_API_KEY"],
        api_secret = st.secrets["CLOUDINARY_API_SECRET"],
        secure = True
    )
    cloudinary_configured = True
except Exception:
    cloudinary_configured = False
    st.warning("Cloudinary configuration missing. Photo uploads will be disabled.")

# --- INITIALIZATION (DB) ---
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

@st.cache_data(ttl=3600)
def load_master_reference():
    try:
        if supabase:
            response = supabase.table("master_item_reference").select("*").eq("is_active", True).execute()
            return response.data
    except Exception as e:
        st.error(f"Failed to load master reference: {e}")
    return []

def upload_photo(file_buffer, store_id, folder_name):
    """Uploads file to Cloudinary and returns the secure URL"""
    try:
        res = cloudinary.uploader.upload(file_buffer, folder=f"cbtl/{store_id}/{folder_name}")
        return res.get("secure_url")
    except Exception as e:
        st.error(f"Upload failed: {e}")
        return None

def get_draft_key(store_id):
    return f"draft_{store_id}_daily"

# --- AESTHETICS & CSS ---
premium_style = """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;600&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Montserrat', sans-serif;
    }
    
    .stApp {
        background-color: #F5F7FA;
    }
    
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .block-container {padding-top: 2rem; padding-bottom: 2rem;}
    
    /* Gold & Espresso Buttons */
    .stButton>button {
        background-color: #C5A059; 
        color: #1A110A; 
        border-radius: 8px;
        border: none;
        padding: 15px;
        font-size: 16px;
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
    
    /* Light Blue Informational Cards */
    div[data-testid="stExpander"] {
        background-color: #EAF2F8;
        border-radius: 10px;
        border: 1px solid #D6EAF8;
        margin-bottom: 10px;
    }
    
    /* Form Styling */
    div[data-testid="stForm"] {
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        padding: 20px;
        background-color: #ffffff;
        box-shadow: 0 4px 6px rgba(0,0,0,0.02);
    }
    
    [data-testid="stFileUploadDropzone"] {
        background-color: #ffffff;
        border: 2px dashed #63B3ED;
        border-radius: 10px;
        padding: 20px;
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
        
        selected_display = st.selectbox("Select Your Location", options=list(store_dict.keys()))
        
        with st.form("login_form"):
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
    
    st.markdown("---")
    
    # ==========================================
    # --- 🌟 STORE PROGRESS & MOTIVATION TRACKER ---
    # ==========================================
    st.markdown("### 🌟 Your QA Excellence Tracker")
    try:
        if supabase is not None:
            my_audits = supabase.table("daily_audits").select("created_at").eq("store_id", st.session_state["store_id"]).execute()
            if my_audits.data:
                df_my = pd.DataFrame(my_audits.data)
                df_my['created_at'] = pd.to_datetime(df_my['created_at'])
                df_my['date_only'] = df_my['created_at'].dt.date
                total_compliant_days = df_my['date_only'].nunique()
                
                st.info(f"🔥 **Keep it up!** Your store has successfully completed **{total_compliant_days} Days** of QA Compliance!")
                st.progress(min(total_compliant_days / 30, 1.0), text="Monthly Goal Progress")
            else:
                st.info("👋 Welcome! Submit your first QA audit today to start your compliance streak!")
    except Exception:
        pass
    st.markdown("---")
    
    # ==========================================
    # --- 🎯 DAILY PROGRESS TRACKER (STAGE 1) ---
    # ==========================================
    st.markdown("### 🎯 Today's Morning Mission")
    
    audit_done = False
    readiness_done = False
    
    try:
        if supabase is not None:
            today_str = datetime.datetime.now().strftime("%Y-%m-%d")
            
            audit_res = supabase.table("daily_audits").select("id").eq("store_id", st.session_state["store_id"]).gte("created_at", today_str).execute()
            if len(audit_res.data) > 0:
                audit_done = True
                
            read_res = supabase.table("store_readiness_logs").select("id").eq("store_id", st.session_state["store_id"]).gte("created_at", today_str).execute()
            if len(read_res.data) > 0:
                readiness_done = True
    except Exception:
        pass
        
    progress = 0
    if audit_done: progress += 50
    if readiness_done: progress += 50
    
    st.progress(progress / 100.0)
    
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        if audit_done:
            st.success("✅ Daily Audit (Completed)")
        else:
            st.warning("⏳ Daily Audit (Pending)")
    with col_t2:
        if readiness_done:
            st.success("✅ Readiness Proofs (Completed)")
        else:
            st.warning("⏳ Readiness Proofs (Pending)")
            
    if progress == 100:
        st.info("🌟 100% Compliant Today! Your morning data is locked in the Central QA Vault.")
    else:
        st.caption("⚠️ Complete your Morning Mission to secure your store's daily QA score.")
        
    st.markdown("---")
    
    # Initialize 6 tabs
    # Add "📚 Resources" to your existing tabs list:
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📋 Daily Audit", 
        "📸 Readiness Proofs",
        "📥 Receiving", 
        "🔄 Transfer", 
        "🗑️ Wastage",
        "📚 Resources"
    ])
    
    # ==========================================
    # TAB 1: DAILY AUDIT (Checklists Only)
    # ==========================================
    with tab1:
        st.subheader("☀️ Daily Opening Checklist")
        st.caption("Auto-save is enabled. Click 'Save Draft' to preserve your progress.")
        
        draft_key = get_draft_key(st.session_state['store_id'])
        
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
            
            col_a, col_b = st.columns(2)
            with col_a:
                btn_save_draft = st.form_submit_button("💾 Save Draft Progress")
            with col_b:
                btn_submit = st.form_submit_button("🚀 Submit Final Audit")

            if btn_save_draft or btn_submit:
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
                                del st.session_state[draft_key]
                                status_msg.success("🎉 Audit successfully locked in Central QA Vault!")
                                st.balloons()
                                
                                # Store uploaded files temporarily in session state for instant collage generation
                                st.session_state["latest_audit_photos"] = [proof_a, proof_b, proof_c, proof_d, proof_e]
                                st.session_state["latest_manager_name"] = manager_name
                                st.rerun()
                            except Exception as e:
                                st.error(f"Database error: {e}")

        # --- QA HERO COLLAGE GENERATOR (Appears post-submission if photos exist) ---
        if "latest_audit_photos" in st.session_state and st.session_state["latest_audit_photos"]:
            st.markdown("---")
            st.markdown("### 📸 Generate Your Daily QA Hero Collage!")
            st.caption("Download a collage of today's audit to share with your team or regional manager.")
            
            qa_hero_name = st.text_input("Confirm Shift Manager / Hero Name:", value=st.session_state.get("latest_manager_name", ""))
            
            if st.button("🎨 Create Motivation Collage", type="primary"):
                with st.spinner("Stitching your photos together..."):
                    try:
                        collage_width = 1200
                        collage_height = 800
                        collage = Image.new('RGB', (collage_width, collage_height), color=(245, 247, 250))
                        
                        valid_images = [img for img in st.session_state["latest_audit_photos"] if img is not None]
                        
                        for idx, img_file in enumerate(valid_images[:5]):
                            img = Image.open(img_file).convert("RGB")
                            img = img.resize((400, 400))
                            x = (idx % 3) * 400
                            y = (idx // 3) * 400
                            collage.paste(img, (x, y))
                            
                        draw = ImageDraw.Draw(collage)
                        text_x, text_y = 800, 400
                        
                        draw.rectangle([text_x, text_y, text_x + 400, text_y + 400], fill=(0, 51, 102))
                        
                        today_str = datetime.datetime.now().strftime('%d %b %Y')
                        motivation_text = f"QA EXCELLENCE\n\nStore:\n{st.session_state['store_name']}\n\nQA Hero:\n{qa_hero_name}\n\nDate: {today_str}\nGreat Job Today!"
                        
                        draw.text((text_x + 30, text_y + 50), motivation_text, fill=(255, 255, 255), spacing=10)
                        
                        buf = io.BytesIO()
                        collage.save(buf, format="JPEG", quality=90)
                        collage_bytes = buf.getvalue()
                        
                        st.image(collage_bytes, caption=f"QA Hero Collage - {qa_hero_name}")
                        
                        st.download_button(
                            label="📥 Download & Share Collage",
                            data=collage_bytes,
                            file_name=f"QA_Collage_{st.session_state['store_name'].replace(' ', '_')}.jpg",
                            mime="image/jpeg"
                        )
                    except Exception as e:
                        st.error(f"Could not generate collage: {e}")

    # ==========================================
    # TAB 2: STORE READINESS PROOFS (Photos Only)
    # ==========================================
    with tab2:
        st.subheader("📸 Opening Hygiene & Readiness Proofs")
        st.caption("Upload required photo verification for morning setup compliance.")
        
        with st.form("readiness_form"):
            st.markdown("Ensure stations are set up before submitting.")
            
            p1 = st.camera_input("Sanitizer Prepared & Metered", key="proof_sanitizer")
            p2 = st.camera_input("Dusters Dipped in Sanitizer Solution", key="proof_dusters")
            p3 = st.camera_input("Wash Sink Loaded with Soap Solution", key="proof_sink")
            p4 = st.camera_input("General Station Readiness / Counter Setup", key="proof_general")
            
            readiness_photos = [p for p in [p1, p2, p3, p4] if p is not None]
            
            st.markdown("---")
            if st.form_submit_button("🚀 Submit Readiness Proofs", type="primary"):
                if not readiness_photos:
                    st.error("❌ Please capture at least one readiness photo.")
                else:
                    with st.spinner("Uploading proofs securely..."):
                        image_urls = []
                        if cloudinary_configured:
                            for photo in readiness_photos:
                                url = upload_photo(photo, st.session_state["store_id"], "readiness")
                                if url:
                                    image_urls.append(url)
                        
                        try:
                            if supabase:
                                supabase.table("store_readiness_logs").insert({
                                    "store_id": st.session_state["store_id"],
                                    "photo_urls": json.dumps(image_urls)
                                }).execute()
                            st.success("✅ Readiness proofs successfully uploaded to the vault!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Database error: {e}")

    # ==========================================
    # TAB 3: RECEIVING & INVOICE LOG
    # ==========================================
    with tab3:
        st.subheader("📦 Goods Receiving & Verification")
        st.caption("Log incoming deliveries, verify core temperatures, and archive vendor challans.")
        
        with st.form("receiving_form"):
            vendor_name = st.text_input("Vendor Name / Supplier")
            invoice_number = st.text_input("Invoice / Chalan Number")
            received_temp = st.number_input("Delivery Core Temperature (°C)", step=0.1, format="%.1f")
            
            st.markdown("### 📸 Invoice / Chalan Upload")
            
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
            
            if st.form_submit_button("✅ Save Receiving Log", type="primary"):
                if not vendor_name or not invoice_number:
                    st.error("❌ Please fill in the Vendor Name and Invoice Number.")
                else:
                    with st.spinner("Uploading proof and saving receiving log..."):
                        try:
                            image_url = ""
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
    # TAB 4: STOCK & INTERNAL TRANSFERS
    # ==========================================
    with tab4:
        st.subheader("🔄 Stock Transfer & Thaw Log")
        st.caption("Manage Inter-Store dispatch and strict FDU Chiller shelf-life protocols.")
        
        transfer_type = st.radio("Select Transfer Protocol", ["Freezer to FDU Chiller (Internal Thaw)", "Inter-Store Dispatch (External)"])
        
        if transfer_type == "Freezer to FDU Chiller (Internal Thaw)":
            master_data = load_master_reference()
            
            ITEM_MAPPING = {item['warehouse_item_name']: item['store_retail_name'] for item in master_data}
            SHELF_LIFE_HOURS = {item['store_retail_name']: item['shelf_life_hours'] for item in master_data}
            TEMP_ZONES = {item['store_retail_name']: item['temperature_zone'] for item in master_data}
            
            with st.form("fdu_transfer_form"):
                wh_item = st.selectbox("Select Warehouse Item (Invoice Name)", ["Select Item..."] + list(ITEM_MAPPING.keys()))
                
                if wh_item != "Select Item...":
                    store_name = ITEM_MAPPING[wh_item]
                    shelf_life = SHELF_LIFE_HOURS.get(store_name, 24)
                    temp_zone = TEMP_ZONES.get(store_name, "Chiller Zone (1-5°C)")
                    
                    now = datetime.datetime.now()
                    expiry_time = now + datetime.timedelta(hours=shelf_life)
                    
                    st.info(f"🏷️ **Store Retail Name:** {store_name}\n⏳ **FSSAI Shelf Life:** {shelf_life} hours\n🌡️ **Storage Requirement:** {temp_zone}")
                    
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
    # TAB 5: WASTAGE & DISCARD
    # ==========================================
    with tab5:
        st.subheader("🗑️ Wastage & Quality Discard Log")
        st.caption("Record expired or damaged goods strictly per NSF standards.")
        
        with st.form("wastage_form"):
            waste_item = st.text_input("Item Name")
            col_w1, col_w2 = st.columns(2)
            with col_w1:
                waste_qty = st.number_input("Quantity Discarded", min_value=0.0, step=0.5)
            with col_w2:
                waste_reason = st.selectbox("Reason for Discard", [
                    "Expired / Out of Date", "Temperature Abuse", "Physical Damage", "Quality Standard Failure"
                ])
            
            st.markdown("### 📸 Wastage Evidence")
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

# ==========================================
    # TAB 6: RESOURCES & COMPLIANCE VAULT
    # ==========================================
    with tab6:
        st.subheader("📚 Operational Resources & Vault")
        st.caption("Access official SOPs, safety guides, and operational charts instantly.")
        
        # Nested sub-tabs for clean categorization
        res_tab1, res_tab2, res_tab3, res_tab4 = st.tabs([
            "🛡️ QA SOPs & Safety", 
            "📋 Menu & Nutrition", 
            "⏳ Shelf Life Chart", 
            "🧪 Chemical Info Sheet"
        ])
        
        with res_tab1:
            st.markdown("### Quality Assurance SOPs")
            st.markdown("Ensure adherence to standard operating procedures across all shifts.")
            # Example document view/download block
            st.info("📄 **Master QA Manual & Audit Guidelines (PDF)**")
            st.download_button("📥 Download QA Manual", data=b"Dummy PDF Content", file_name="CBTL_QA_SOP.pdf", mime="application/pdf")
            
        with res_tab2:
            st.markdown("### Menu & Nutrition Booklets")
            st.markdown("Reference guides for beverage and food items.")
            st.info("📄 **Latest Beverage & Pastry Menu Spec Sheet**")
            st.download_button("📥 Download Menu Specs", data=b"Dummy PDF Content", file_name="CBTL_Latest_Menu.pdf", mime="application/pdf")
            
        with res_tab3:
            st.markdown("### Shelf Life & Storage Charts")
            st.markdown("Strict timelines for thawing, holding, and disposal.")
            st.info("📄 **FDU & Chiller Shelf Life Matrix**")
            st.download_button("📥 Download Shelf Life Chart", data=b"Dummy PDF Content", file_name="CBTL_Shelf_Life_Chart.pdf", mime="application/pdf")
            
        with res_tab4:
            st.markdown("### Chemical Safety Information Sheets")
            st.markdown("SDS sheets for sanitizers and cleaning agents used in-store.")
            st.info("📄 **Sanitizer & Detergent Safety Data Sheet (SDS)**")
            st.download_button("📥 Download Chemical Info", data=b"Dummy PDF Content", file_name="Chemical_Info_Sheet.pdf", mime="application/pdf")
# --- APP ROUTING ---
if st.session_state["logged_in"]:
    store_dashboard()
else:
    login_screen()
