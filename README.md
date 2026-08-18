
# 🛡️ QA & Compliance Intelligence Dashboard

**"Cloud-based QA & Compliance Dashboard for internal audit tracking, food safety documentation, real-time pest control monitoring, and store-level daily FSSAI/NSF compliance across all locations."**

## 📋 Project Overview

This repository hosts a centralized dashboard and integrated outlet application designed to streamline Quality Assurance and Regulatory Compliance for our retail operations. The tool transitions our entire audit process—from central management tracking to daily shift-level checklists—from manual paper logs to a real-time, data-driven cloud environment.

## 🚀 Key Features

### Central QA & Management (HO)

* **Audit Scoring:** Monthly internal QA and Quarterly NSF audit tracking for all 12 stores.
* **Outstation Flexibility:** Intelligent logic to handle audit skips for outstation locations without impacting performance metrics.
* **Compliance Vault:** Centralized storage for FSSAI Licenses and Water Test Reports with automated expiry countdowns.
* **Pest Control Tracker:** Weekly frequency monitoring with agency-specific assignment (IGPC & Eco Sol).
* **Management Alert System:** High-priority highlighting of critical issues requiring immediate intervention.

### Store Outlet Operations (Front-End)

* **FSSAI & NSF Daily Checklists:** Mandatory, shift-by-shift digital compliance checklists for store managers to verify critical failure points (expired items, pest sightings, equipment hygiene) in real-time.
* **FDU & Shelf-Life Tracking:** Digitized inventory ledgers for Food Display Unit (FDU) items. Features intelligent dual shelf-life tracking that automatically activates a chilled expiry countdown the moment items are transferred from the freezer.
* **Camera-Mandated Audit Trails:** Strict camera integration (`st.camera_input`) requiring staff to capture photographic proof when receiving specific warehouse deliveries and registering product wastage or damage.
* **Seamless Outlet Login:** Frictionless, password-free login mechanism using the store's email ID and manager's phone number for quick access on busy floors.

## 🛠️ Technology Stack

* **Frontend:** Streamlit (Python-based interactive UI optimized for both desktop and mobile/tablet browsers)
* **Backend/Database:** Supabase (PostgreSQL)
* **Storage:** Supabase Storage (S3-compatible bucket for PDF reports and camera-captured audit photos)
* **Cloud Hosting:** Streamlit Community Cloud

## 📂 Project Structure
app.py: Main application logic housing both the Central QA Dashboard and the Outlet Staff UI via role-based tab routing.

requirements.txt: Python dependencies (configured for auto-updates to the latest Streamlit version).

sql_setup/: Database schema, initial store data scripts, and table definitions for checklists and FDU inventory
* `app.py`: Main application logic housing both the Central QA Dashboard and the Outlet Staff UI via role-based tab routing.
* `requirements.txt`: Python dependencies (configured for auto-updates to the latest Streamlit version).
* `sql_setup/`: Database schema, initial store data scripts, and table definitions for checklists and FDU inventory.
