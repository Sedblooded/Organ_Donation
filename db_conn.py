import os
from contextlib import contextmanager
from pathlib import Path
import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
import streamlit as st


def get_db_url() -> str:
    """Resolve database URL from environment or Streamlit secrets."""
    # 1. Environment variable (e.g. Replit or custom deployment)
    if os.environ.get("DATABASE_URL"):
        return os.environ["DATABASE_URL"]

    # 2. Streamlit secrets
    try:
        if hasattr(st, "secrets") and "db" in st.secrets and "url" in st.secrets["db"]:
            return st.secrets["db"]["url"]
    except Exception:
        pass

    # 3. Direct read from .streamlit/secrets.toml if outside Streamlit runtime
    secrets_path = Path(__file__).parent / ".streamlit" / "secrets.toml"
    if secrets_path.exists():
        try:
            import tomllib
            with open(secrets_path, "rb") as f:
                data = tomllib.load(f)
                if "db" in data and "url" in data["db"]:
                    return data["db"]["url"]
        except Exception:
            pass

    # 4. Fallback to standard PG environment variables or localhost
    host = os.getenv("PGHOST", "localhost")
    port = os.getenv("PGPORT", "5432")
    dbname = os.getenv("PGDATABASE", "organ_donation")
    user = os.getenv("PGUSER", "postgres")
    password = os.getenv("PGPASSWORD", "password")
    return f"postgresql://{user}:{password}@{host}:{port}/{dbname}"


@st.cache_resource
def get_connection_pool():
    """Create and cache a threaded connection pool."""
    url = get_db_url()
    return pool.ThreadedConnectionPool(minconn=1, maxconn=10, dsn=url)


@contextmanager
def get_conn():
    """Borrow a connection from the pool and return it afterwards."""
    p = get_connection_pool()
    conn = p.getconn()
    try:
        yield conn
    finally:
        p.putconn(conn)


@contextmanager
def transaction():
    """Transaction context manager ensuring commit or rollback."""
    with get_conn() as conn:
        try:
            with conn:
                yield conn
        except Exception:
            conn.rollback()
            raise


def fetch_all(query: str, params: tuple | dict | list = None) -> list[dict]:
    """Execute a SELECT query and return list of row dicts."""
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            return [dict(row) for row in cur.fetchall()]


def fetch_one(query: str, params: tuple | dict | list = None) -> dict | None:
    """Execute a SELECT query and return a single row dict, or None."""
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            row = cur.fetchone()
            return dict(row) if row else None


def execute(query: str, params: tuple | dict | list = None) -> int:
    """Execute an INSERT, UPDATE, or DELETE query and commit."""
    with get_conn() as conn:
        with conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                return cur.rowcount


def execute_returning(query: str, params: tuple | dict | list = None) -> dict | None:
    """Execute an INSERT/UPDATE ... RETURNING and return the resulting row dict."""
    with get_conn() as conn:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, params)
                row = cur.fetchone()
                return dict(row) if row else None


def check_connection() -> bool:
    """Check if the database connection is alive."""
    try:
        res = fetch_one("SELECT 1 AS alive;")
        return bool(res and res.get("alive") == 1)
    except Exception:
        return False
