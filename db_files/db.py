"""Shared database connection helper.

Connection settings, in order of priority:
  1. DATABASE_URL            (Replit sets this automatically)
  2. PGHOST / PGPORT / PGDATABASE / PGUSER / PGPASSWORD   (local Postgres)
"""
import os
import sys

import psycopg2


def get_connection(autocommit: bool = False):
    dsn = os.environ.get("DATABASE_URL")
    try:
        if dsn:
            conn = psycopg2.connect(dsn)
        else:
            conn = psycopg2.connect(
                host=os.getenv("PGHOST", "localhost"),
                port=os.getenv("PGPORT", "5432"),
                dbname=os.getenv("PGDATABASE", "postgres"),
                user=os.getenv("PGUSER", "postgres"),
                password=os.getenv("PGPASSWORD", ""),
            )
    except psycopg2.OperationalError as exc:
        sys.exit(
            "Could not connect to PostgreSQL.\n"
            "  - On Replit: make sure the Database tool is enabled (DATABASE_URL must exist).\n"
            "  - Locally: set DATABASE_URL, or PGHOST/PGPORT/PGDATABASE/PGUSER/PGPASSWORD.\n"
            f"Driver message: {str(exc).strip()}"
        )
    conn.autocommit = autocommit
    return conn