"""Create (or re-create) every table, constraint, trigger and function.

    python init_db.py            # first-time setup
    python init_db.py --force    # DROP everything and rebuild (all data is lost)
"""
import argparse
import sys
from pathlib import Path

import check_db
from db import get_connection

SCHEMA_FILE = Path(__file__).parent / "sql" / "01_schema.sql"


def existing_tables(cur):
    cur.execute(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = 'public' AND table_name = ANY(%s)",
        (check_db.EXPECTED_TABLES,),
    )
    return [r[0] for r in cur.fetchall()]


def init_db(force: bool = False) -> bool:
    conn = get_connection(autocommit=True)
    try:
        with conn.cursor() as cur:
            found = existing_tables(cur)
            if found and not force:
                print(f"Refusing to run: {len(found)} project tables already exist.")
                print("Re-run with --force to DROP them and rebuild (all data will be lost).")
                return False
            if found:
                print(f"--force given: dropping and recreating {len(found)} existing tables.")
            cur.execute(SCHEMA_FILE.read_text(encoding="utf-8"))
        print("Schema created. Running schema + rule checks ...\n")
        return check_db.run_all_checks(conn, include_invariants=False)
    finally:
        conn.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--force", action="store_true", help="drop and recreate existing tables")
    sys.exit(0 if init_db(ap.parse_args().force) else 1)