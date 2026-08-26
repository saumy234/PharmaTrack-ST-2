import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(os.path.dirname(BASE_DIR), "database", "database.db")

REQUIRED_TABLES = {
    "medicines": {"id", "name", "min_stock"},
    "medicine_batches": {"id", "medicine_id", "batch_code", "quantity", "expiry_date", "created_at"},
    "sales": {"id", "medicine_id", "quantity", "timestamp"},
    "temperature_logs": {"id", "device_id", "temperature", "humidity", "timestamp"},
    "alerts": {"id", "type", "message", "timestamp", "status", "acknowledged_at", "resolved_at"},
}

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def check_database_schema():
    if not os.path.exists(DB_PATH):
        raise RuntimeError(f"Database file not found: {DB_PATH}")
    conn = get_connection()
    try:
        for table, required in REQUIRED_TABLES.items():
            exists = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone()
            if not exists:
                raise RuntimeError(f"Required table '{table}' does not exist.")
            actual = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
            missing = required - actual
            if missing:
                raise RuntimeError(f"Table '{table}' is missing columns: {sorted(missing)}")
    finally:
        conn.close()
