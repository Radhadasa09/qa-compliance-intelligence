# qa-compliance-intelligence
"Cloud-based QA &amp; Compliance Dashboard for internal audit tracking, food safety documentation, and real-time pest control monitoring across store locations."
🛡️ QA & Compliance Intelligence Dashboard
📋 Project Overview
This repository hosts a centralized dashboard designed to streamline Quality Assurance and Regulatory Compliance for our retail operations. The tool transitions our audit process from manual tracking to a real-time, data-driven cloud environment.

🚀 Key Features
Audit Scoring: Monthly internal QA and Quarterly NSF audit tracking for all 12 stores.

Outstation Flexibility: Intelligent logic to handle audit skips for outstation locations without impacting performance metrics.

Compliance Vault: Centralized storage for FSSAI Licenses and Water Test Reports with automated expiry countdowns.

Pest Control Tracker: Weekly frequency monitoring with agency-specific assignment (IGPC & Eco Sol).

Management Alert System: High-priority highlighting of critical issues requiring immediate intervention.

🛠️ Technology Stack
Frontend: Streamlit (Python-based interactive UI)

Backend/Database: Supabase (PostgreSQL)

Storage: Supabase Storage (S3-compatible bucket for PDF reports)

Cloud Hosting: Streamlit Community Cloud

📂 Project Structure
app.py: Main application logic and UI.

requirements.txt: Python dependencies.

sql_setup/: Database schema and initial store data scripts.
