# Organ Donation & Transplant Management System

A normalized (BCNF), PostgreSQL-backed web application built with **Streamlit** and **Python** to streamline the end-to-end organ donation, waitlist ranking, matching, surgical allocation, and recovery monitoring workflows.

---

## Quick Start (Local Setup)

### 1. Requirements
- Python 3.10+
- PostgreSQL 14+ (or running PostgreSQL instance)

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Database Credentials Configuration
Ensure `.streamlit/secrets.toml` contains your PostgreSQL connection string:
```toml
[db]
url = "postgresql://postgres:password@localhost:5432/organ_donation"
```

### 4. Run the Streamlit Application
```bash
streamlit run app.py
```
Open your browser at `http://localhost:8501`.

---

## Architecture & Directory Structure

```
.
├── app.py                      # Landing page + metrics overview + navigation
├── db_conn.py                  # Threaded PostgreSQL connection pool & transaction manager
├── requirements.txt
├── README.md
├── .streamlit/
│   ├── secrets.toml            # Local DB credentials (git-ignored)
│   └── secrets.toml.example    # Template credentials file
├── db_files/                   # Database schemas and validation suites
│   ├── sql/
│   │   ├── 01_schema.sql       # 15 tables, 5 triggers, stored procedures
│   │   └── 02_seed.sql         # Reference data and realistic seed records
│   ├── check_db.py             # Database integrity & rule testing suite
│   └── seed_db.py              # Seed loading script
├── queries/                    # Pure SQL abstraction layer
│   ├── dashboard.py            # Aggregations, metrics, expiring organs
│   ├── patients.py             # Patient, donor & recipient CRUD
│   ├── organs.py               # Harvest logging & live viability calculation
│   ├── waitlist.py             # Active waitlist queuing & priority management
│   ├── matching.py             # Compatibility evaluation & find_matches()
│   ├── transplants.py          # Atomic surgical allocation with row locks
│   ├── recovery.py             # Post-operative checkup logs & timelines
│   └── staff.py                # Hospitals, physicians, affiliations, specializations
├── utils/
│   ├── rules.py                # Status constants, ABO rules, viability maths
│   └── ui.py                   # Form helpers, role gates, error translation
└── pages/                      # Multipage Streamlit interface
    ├── 1_Dashboard.py          # Visual analytics & urgent expiry countdowns
    ├── 2_Patients.py           # Patient enrolment & donor/recipient designation
    ├── 3_Organs.py             # Organ registry & real-time viability timers
    ├── 4_Waitlist.py           # Priority-ranked waiting queues
    ├── 5_Matching.py           # Algorithmic blood & urgency matching engine
    ├── 6_Transplants.py        # Concurrency-safe surgical execution
    ├── 7_Recovery.py           # Longitudinal healing trajectories
    └── 8_Doctors_Hospitals.py  # Facility & healthcare professional network
```

---

## 🔒 Role-Based Access Control

The app includes an instant role switcher in the sidebar to simulate access levels:
- **Admin**: Full administrative permissions across all pages, facilities, and staff.
- **Doctor**: Clinical access for waitlist evaluation, algorithmic matching, transplant recording, and post-op care.
- **Hospital Staff**: Patient intake, donor legal consent recording, organ harvest entry, and waitlist management.
