"""Load the mock data (hospitals, doctors, patients, organs, waitlist, transplants ...).

    python seed_db.py            # only if the tables are empty
    python seed_db.py --reset    # wipe all rows first (schema is kept), then reload
"""
import argparse
import sys
from pathlib import Path

import check_db
from db import get_connection

SEED_FILE = Path(__file__).parent / "sql" / "02_seed.sql"
# blood_compat is reference data loaded by init_db.py, so it is NOT wiped.
DATA_TABLES = [
    "recovery", "transplant", "waitlist", "organ", "organ_type", "doctor_hospital",
    "doctor_spec", "specialization", "doctor", "recipient", "donor", "patient",
    "hospital", "pincode_area",
]


def seed_db(reset: bool = False) -> bool:
    conn = get_connection(autocommit=True)   # the SQL file manages its own BEGIN/COMMIT
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM information_schema.tables "
                        "WHERE table_schema='public' AND table_name = ANY(%s)",
                        (check_db.EXPECTED_TABLES,))
            if cur.fetchone()[0] < len(check_db.EXPECTED_TABLES):
                print("Tables are missing. Run  python init_db.py  first.")
                return False

            cur.execute("SELECT (SELECT count(*) FROM patient) + (SELECT count(*) FROM hospital)")
            if cur.fetchone()[0] > 0:
                if not reset:
                    print("Refusing to run: the database already contains data.")
                    print("Re-run with --reset to wipe the rows and reload the mock data.")
                    return False
                cur.execute("TRUNCATE " + ", ".join(DATA_TABLES) + " RESTART IDENTITY CASCADE")
                print("Existing rows removed.")

            try:
                cur.execute(SEED_FILE.read_text(encoding="utf-8"))
            except Exception as exc:
                cur.execute("ROLLBACK")      # leave nothing half-loaded
                print(f"Seeding failed and was rolled back:\n{exc}")
                return False
        print("Mock data loaded. Running all checks ...\n")
        return check_db.run_all_checks(conn, expect_seed=True)
    finally:
        conn.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--reset", action="store_true", help="delete all rows first, then reload")
    sys.exit(0 if seed_db(ap.parse_args().reset) else 1)