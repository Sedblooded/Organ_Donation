# SETUP.md: Environment, Local Dev, and Deployment Checklist

Step-by-step to-do list from zero to a deployed app.
Plan: **develop locally (local Postgres) → integration-test against the shared Replit DB → deploy to Replit.**

---

## 0. Prerequisites

- [ ] Python 3.10+ (`python --version`)
- [ ] Git installed and repo access
- [ ] PostgreSQL 14+ installed locally (or Docker)
- [ ] A code editor (VS Code recommended)
- [ ] Access to the shared Replit project (for the Replit DB URL)

---

## 1. Get the code

- [ ] Clone the repo (or download the zip if there is no remote yet)
  ```bash
  git clone <repo-url>
  cd organ-donation
  ```
- [ ] Confirm `db_files/` is present with `sql/`, `db.py`, `initialize_database.py`, `seed_db.py`, `check_db.py`
- [ ] **Delete the stray file named `=2.9`** in the repo root (created by an unquoted `pip install psycopg2>=2.9`)
  ```bash
  rm "=2.9"          # Windows PowerShell: Remove-Item "=2.9"
  ```
- [ ] Open `db_files/db.py` and note **which driver it uses** (`psycopg2` or `psycopg`). Use the same one everywhere.

---

## 2. Python environment

- [ ] Create and activate a virtual environment
  ```bash
  python -m venv venv
  source venv/bin/activate        # Windows: venv\Scripts\activate
  ```
- [ ] Create `requirements.txt` (adjust the driver to match `db.py`):
  ```
  streamlit>=1.35
  psycopg[binary,pool]>=3.1      # or: psycopg2-binary>=2.9
  pandas
  plotly                          # optional, for dashboard charts
  ```
- [ ] Install (always quote version specifiers if typing them in the shell)
  ```bash
  pip install -r requirements.txt
  ```
- [ ] Verify: `streamlit hello` opens in the browser

---

## 3. Local PostgreSQL database

- [ ] Start Postgres (service running, or `docker run` below)
  ```bash
  docker run --name organ-pg -e POSTGRES_PASSWORD=postgres -p 5432:5432 -d postgres:16
  ```
- [ ] Create the database
  ```bash
  psql -U postgres -h localhost -c "CREATE DATABASE organ_donation;"
  ```
- [ ] Local connection URL:
  ```
  postgresql://postgres:postgres@localhost:5432/organ_donation
  ```
- [ ] Point the teammate's scripts at this URL (env var or the config in `db_files/db.py`, check how it reads the URL)
- [ ] Build the schema
  ```bash
  python db_files/initialize_database.py
  ```
- [ ] Load sample data
  ```bash
  python db_files/seed_db.py
  ```
- [ ] Verify
  ```bash
  python db_files/check_db.py
  ```
  Expected: all 12 tables listed (10 entities + `Doctor_Hospital` + `Doctor_Spec`) with seed rows.

---

## 4. Secrets and config

- [ ] Create `.streamlit/secrets.toml` (local only):
  ```toml
  [db]
  url = "postgresql://postgres:postgres@localhost:5432/organ_donation"
  ```
- [ ] Create `.streamlit/secrets.toml.example` (committed, dummy values):
  ```toml
  [db]
  url = "postgresql://USER:PASSWORD@HOST:5432/DBNAME"
  ```
- [ ] Add to `.gitignore`:
  ```
  venv/
  __pycache__/
  .streamlit/secrets.toml
  .env
  *.pyc
  ```
- [ ] Confirm `git status` does **not** list `secrets.toml`
- [ ] Never paste the Replit DB URL in a public repo, screenshot, or open chat

---

## 5. Connection layer

- [ ] Create `queries/__init__.py` and `utils/__init__.py`
- [ ] Write a root-level `db_conn.py` (or extend `db_files/db.py`) that:
  - reads `st.secrets["db"]["url"]`
  - builds a **cached connection pool** with `@st.cache_resource`
  - exposes `fetch_all`, `fetch_one`, `execute`, and a transaction helper
  - uses dict rows
- [ ] Write `test_conn.py` to verify outside Streamlit:
  ```python
  import psycopg, tomllib
  url = tomllib.load(open(".streamlit/secrets.toml", "rb"))["db"]["url"]
  with psycopg.connect(url) as conn:
      print(conn.execute("SELECT current_database(), now()").fetchone())
      print(conn.execute(
          "SELECT table_name FROM information_schema.tables WHERE table_schema='public'"
      ).fetchall())
  ```
- [ ] Run `python test_conn.py` → should print the DB name and table list

---

## 6. Build order (frontend)

Tick each only when it works end to end against the local DB.

**Phase 1: Foundation**
- [ ] `app.py` with sidebar, role selector, DB status indicator
- [ ] `utils/ui.py` helpers (select_from_rows, show_db_error, require_role)
- [ ] `utils/rules.py` (status constants, ABO compatibility, viability calc)

**Phase 2: Core data entry**
- [ ] `2_Patients.py`: register, make donor, make recipient, search/list
- [ ] `8_Doctors_Hospitals.py`: hospitals, doctors, specializations, affiliations
- [ ] `3_Organs.py`: organ types, add organ, available organs with time remaining
- [ ] `4_Waitlist.py`: add and view

**Phase 3: The important part**
- [ ] `5_Matching.py`: eligibility + ranking
- [ ] `6_Transplants.py`: transaction with row lock and rollback
- [ ] `7_Recovery.py`: checkups + timeline

**Phase 4: Polish**
- [ ] `1_Dashboard.py`: metrics, charts, expiry alerts
- [ ] Friendly error messages everywhere
- [ ] Empty-state messages ("No recipients waiting")
- [ ] README with screenshots

Run the app any time with:
```bash
streamlit run app.py
```

---

## 7. Team git workflow

- [ ] Branch per feature: `git checkout -b feature/patients-page`
- [ ] Small commits with clear messages
- [ ] Pull before you push: `git pull --rebase origin main`
- [ ] Ownership to avoid conflicts:
  - **DB teammate:** `db_files/`, `sql/`
  - **You:** `app.py`, `pages/`, `queries/`, `utils/`
- [ ] **Schema changes:** update `sql/` in git first, announce it, and everyone re-runs `initialize_database.py` (and `seed_db.py`) locally
- [ ] Keep `requirements.txt` updated whenever you add a package

---

## 8. Integration test against the shared Replit DB

Do this once the local app works.

- [ ] Get the Replit Postgres connection URL from the Replit Database tool
  - Make sure everyone uses the **same** database (Replit may have separate dev and production DBs)
  - URL needs `sslmode=require`
- [ ] Temporarily replace the URL in your local `.streamlit/secrets.toml`
- [ ] Run `python test_conn.py`. If it times out or errors with SSL, check:
  - the host is the externally reachable one
  - `sslmode=require` is in the URL
  - no firewall/VPN is blocking port 5432
- [ ] Click through every page and run the test scenarios from `workflow.md` section 7
- [ ] Switch your `secrets.toml` back to the local URL afterwards
- [ ] Don't run destructive tests (delete/drop) on the shared DB; keep a reset path (`initialize_database.py` + `seed_db.py`)

---

## 9. Deploy the app to Replit

- [ ] Upload or import the repo into a Replit project (or connect GitHub)
- [ ] Add the DB URL in **Replit Secrets** (not in files)
- [ ] Make `db_conn.py` read from either source:
  ```python
  import os, streamlit as st
  url = os.environ.get("DATABASE_URL") or st.secrets["db"]["url"]
  ```
- [ ] Install dependencies in Replit from `requirements.txt`
- [ ] Set the run command:
  ```bash
  streamlit run app.py --server.port 8080 --server.address 0.0.0.0
  ```
  (use the port Replit expects; check the project's port settings)
- [ ] Open the Replit webview URL and run through the happy-path scenario
- [ ] Share the live link with your team

---

## 10. Troubleshooting

| Problem | Likely cause | Fix |
|---|---|---|
| `ModuleNotFoundError` | venv not activated or package missing | activate venv; `pip install -r requirements.txt` |
| `connection refused` (local) | Postgres isn't running | start the service/container |
| `password authentication failed` | wrong URL credentials | recheck `secrets.toml` |
| `SSL` error on Replit DB | missing `sslmode=require` | add it to the URL |
| `connection closed` / `server closed the connection` after idle | remote DB dropped the connection | use the pool with `check=ConnectionPool.check_connection` |
| `relation "x" does not exist` | schema not initialised or out of date | rerun `initialize_database.py` |
| `duplicate key value violates unique constraint` | inserting existing `med_bar_id`/`reg_id` etc. | show friendly error; use a different value |
| Page shows stale data after a write | cached query | `st.cache_data.clear()` after writes |
| Widgets reset on every click | missing `st.form` or session state | wrap inputs in `st.form`; store selections in `st.session_state` |
| `StreamlitSecretNotFoundError` | no `secrets.toml` | create it in `.streamlit/` next to where you run the command |

---

## 11. Final pre-demo checklist

- [ ] All 8 pages load without errors
- [ ] Happy-path scenario works on the Replit-hosted app
- [ ] Transaction rollback demonstrated
- [ ] Seed data reset script tested
- [ ] README explains setup in 5 steps
- [ ] No credentials in git history (`git log -p | grep -i password`)
- [ ] ER diagram + schema screenshot ready for the report
