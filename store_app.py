import streamlit as st
import datetime

from supabase import create_client, Client

# Initialize Supabase client
@st.cache_resource
def init_supabase() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_supabase()
    # --- CLEAN SUPABASE CONNECTION TEST ---
try:
    # Attempt a simple lightweight query to check connection
    response = supabase.table("store_inventory").select("*", count="exact").limit(1).execute()
    st.success("✅ Supabase Database: Connected Successfully!")
except Exception as e:
    st.error(f"❌ Supabase Connection Failed. Check URL and Key. Details: {e}")
# --- QUICK CONNECTION DIAGNOSTIC ---
with st.sidebar:
    st.markdown("### 🔍 System Diagnostics")
    if st.button("Test Cloud & DB Connections"):
        # Test Supabase
        try:
            supabase.table("store_inventory").select("count", count="exact").execute()
            st.success("✅ Supabase Database: Connected")
        except Exception as e:
            st.error(f"❌ Supabase Error: {e}")
            
        # Test Cloudinary
        try:
            import cloudinary.api
            ping_res = cloudinary.api.ping()
            if ping_res.get("status") == "ok":
                st.success("✅ Cloudinary Storage: Connected")
            else:
                st.warning("⚠️ Cloudinary responded, check credentials.")
        except Exception as e:
            st.error(f"❌ Cloudinary Error: {e}")
# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="CBTL Store Operations", layout="centered", initial_sidebar_state="collapsed")

# --- SESSION STATE INITIALIZATION ---
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "store_id" not in st.session_state:
    st.session_state["store_id"] = ""

# --- MOCK DATABASE FUNCTIONS (To be replaced with Supabase) ---
def sync_to_supabase(table, data):
    st.success(f"✅ Data securely logged to central QA ({table}).")

# --- LOGIN SCREEN (SIMPLIFIED FOR STORE TEAM) ---
def login_screen():
    st.title("☕ CBTL Store Login")
    st.caption("FSSAI & NSF Operational Compliance Portal")
    
    with st.form("login_form"):
        # List all 12 stores
        stores_list = [
            "Store-1", "Store-2", "Store-3", "Store-4", 
            "Store-5", "Store-6", "Store-7", "Store-8", 
            "Store-9", "Store-10", "Store-11", "Store-12"
        ]
        selected_store = st.selectbox("Select Your Store", stores_list)
        
        # Confirmation and Static PIN
        confirm_store = st.checkbox(f"I confirm I am logging in for {selected_store}")
        pin = st.text_input("Enter Store PIN", type="password", placeholder="Enter 4-digit PIN")
        
        submitted = st.form_submit_button("Proceed to Outlet")
        
        if submitted:
            if not confirm_store:
                st.error("❌ Please check the confirmation box to verify your store location.")
            elif pin != "0000":
                st.error("❌ Incorrect PIN. Please enter the valid store PIN (0000).")
            else:
                st.session_state["logged_in"] = True
                st.session_state["store_id"] = selected_store
                st.rerun()
# --- MAIN OUTLET DASHBOARD ---
def store_dashboard():
    st.header(f"Store: {st.session_state['store_id']}")
    st.button("Logout", on_click=lambda: st.session_state.update({"logged_in": False}))
    
    # 4 Core Tabs for Store Operations
    tab1, tab2, tab3, tab4 = st.tabs([
        "📥 Receiving", 
        "🔄 FDU Transfer", 
        "📋 Daily Checklist", 
        "🗑️ Wastage"
    ])
    
    # --- TAB 1: RECEIVING (CAMERA MANDATED) ---
    with tab1:
        st.subheader("Receive Warehouse Delivery")
        st.info("Log incoming FDU and perishable batches into Frozen/Main storage.")
        with st.form("receiving_form"):
            batch_id = st.text_input("Batch ID (from Challan)", placeholder="e.g., WH-NOI-CHKN-170826-01")
            received_qty = st.number_input("Quantity Received", min_value=1)
            
            st.markdown("**Photographic Proof Required**")
            delivery_photo = st.camera_input("Take photo of boxes/challan")
            
            receive_submit = st.form_submit_button("Confirm Receipt")
            if receive_submit:
                if not batch_id or not delivery_photo:
                    st.error("❌ Batch ID and Delivery Photo are mandatory.")
                else:
                    sync_to_supabase("store_inventory", {"batch": batch_id, "qty": received_qty, "status": "In_Freezer"})

    # --- TAB 2: FDU TRANSFER (DUAL SHELF LIFE) ---
    with tab2:
        st.subheader("Freezer to FDU Chiller Transfer")
        st.warning("Transferring items will immediately start the Chilled Shelf-Life countdown.")
        with st.form("fdu_transfer_form"):
            item_name = st.selectbox("Select FDU Item", ["Orange Tea Cake", "Croissant", "Kadhai Paneer Fold", "Chocolate Marble"])
            transfer_qty = st.number_input("Quantity to Display", min_value=1)
            
            # Mock master data mapping for shelf life
            shelf_life_map = {"Orange Tea Cake": 3, "Croissant": 2, "Kadhai Paneer Fold": 3, "Chocolate Marble": 3}
            chilled_days = shelf_life_map.get(item_name, 2)
            
            st.write(f"**Assigned Chilled Shelf Life:** {chilled_days} Days")
            
            transfer_submit = st.form_submit_button("Execute Transfer & Start Timer")
            if transfer_submit:
                expiry_date = datetime.date.today() + datetime.timedelta(days=chilled_days)
                sync_to_supabase("fdu_active_stock", {"item": item_name, "qty": transfer_qty, "expiry": str(expiry_date)})
                st.info(f"New Expiry Date for this batch: {expiry_date.strftime('%d-%b-%Y')}")

    # --- TAB 3: DAILY FSSAI & NSF CHECKLIST (COMPLETE) ---
    with tab3:
        st.subheader("FSSAI & NSF Shift Checklist")
        st.caption("100% Clearance Required. Hold and fix any failing point on the spot.")
        with st.form("daily_checklist_form"):
            
            st.markdown("### A. Critical Facility & Entrance")
            c1 = st.checkbox("Water & Power: Facility has operating power, working water/sewage, and hot water available (>120°F/49°C)")
            c2 = st.checkbox("Audit Readiness: Store opened on time and ready to allow unannounced auditor entry")
            c3 = st.checkbox("Hygiene Stations: Hand wash sinks fully operational with soap; functioning toilet accessible")
            c4 = st.checkbox("Entrance: Air Curtain ON; Fly Catcher ON (glue pad clean); FSSAI License displayed prominently")
            
            st.markdown("### B. FOH Engine & Beverage Station")
            c5 = st.checkbox("Milk Safety: Chilled milk maintained at 2°C - 4°C; non-fat milk steamed to exactly 160°F (71°C)")
            c6 = st.checkbox("Espresso Calibration: Flow time calibrated to 18–26 seconds utilizing 14g (+-0.5g) of coffee")
            c7 = st.checkbox("Equipment Readiness: Calibrated thermometers, 3 sets of powder scoops, and 2 sets of beakers available")
            c8 = st.checkbox("Machine Hygiene: Steam wands purged/wiped before & after use; Ice Machine 100% mold-free; Blenders rinsed")
            
            st.markdown("### C. Kitchen Operations & Food Safety")
            c9 = st.checkbox("Temperature Control (Cold): Under-counter chillers and all TCS foods held at < 41°F (5°C)")
            c10 = st.checkbox("Temperature Control (Hot): Heated RTE foods (muffins/sandwiches) >65°C; Cooked from raw >76°C")
            c11 = st.checkbox("TCS Protocol: All TCS foods in use are discarded within 4 hours with documented procedures")
            c12 = st.checkbox("Cross-Contamination & Quality: Zero cross-contamination; zero mold/spoilage; all products strictly within shelf life")
            c13 = st.checkbox("Sanitization: Sanitizer available at correct dilution in two-sink system; Hot water dishwasher >180°F (82°C)")
            
            st.markdown("### D. Team Health & Hygiene")
            c14 = st.checkbox("Illness & Infection: No team member working with Hepatitis A symptoms or uncovered open sores/boils")
            c15 = st.checkbox("Handwashing: Strict handwashing protocols followed; no bandaged hands handling food without gloves")
            c16 = st.checkbox("Grooming & Uniforms: Nails trimmed (no polish), no perfumes, approved uniforms/hairnets worn, personal items on rack")
            
            st.markdown("### E. Critical Pest Failure Limits")
            c17 = st.checkbox("Rodents: ZERO live/dead rodents outside traps; ZERO evidence of droppings (10+) or multiple rodents")
            c18 = st.checkbox("Insects & General: ZERO live roaches; ZERO maggots; flies strictly under limit (<9); ZERO breeding evidence in food")
            
            st.markdown("---")
            st.markdown("*I certify that I have physically inspected all areas of this store. There are NO expired products on the premises, and all pest control measures are active and verified.*")
            manager_sign = st.text_input("Manager Signature (Type Name)")
            
            checklist_submit = st.form_submit_button("Submit Daily Audit")
            
            if checklist_submit:
                # Validation checks that all 18 boxes are ticked
                all_passed = all([
                    c1, c2, c3, c4, c5, c6, c7, c8, c9, 
                    c10, c11, c12, c13, c14, c15, c16, c17, c18
                ])
                if not all_passed or not manager_sign:
                    st.error("🚨 CRITICAL FAILURE: All points must be marked OK and signature is required. Take immediate corrective action on the floor.")
                else:
                    sync_to_supabase("daily_audits", {"manager": manager_sign, "status": "Passed 100%"})

    # --- TAB 4: WASTAGE (CAMERA MANDATED) ---
    with tab4:
        st.subheader("Register Wastage")
        st.error("Photographic proof is mandatory for all shrinkage/wastage logs.")
        with st.form("wastage_form"):
            waste_item = st.selectbox("Item Wasted", ["Orange Tea Cake", "Croissant", "Milk (1L)", "Other"])
            waste_qty = st.number_input("Quantity Wasted", min_value=1)
            waste_reason = st.selectbox("Reason", ["Expired Chilled Shelf Life", "Damaged", "Quality Issue"])
            
            waste_photo = st.camera_input("Capture Photo of Wasted Item")
            
            waste_submit = st.form_submit_button("Log Wastage")
            if waste_submit:
                if not waste_photo:
                    st.error("❌ Photographic proof is mandatory to submit wastage.")
                else:
                    sync_to_supabase("wastage_logs", {"item": waste_item, "qty": waste_qty, "reason": waste_reason})

# --- APP ROUTING ---
if st.session_state["logged_in"]:
    store_dashboard()
else:
    login_screen()
