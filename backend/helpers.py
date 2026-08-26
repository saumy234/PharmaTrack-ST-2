from datetime import datetime, date
from flask import request  # type: ignore[import-not-found]
from .database import get_connection

COLD_CHAIN_MAX_TEMPERATURE = 28.0

def get_json_body():
    data = request.get_json(silent=True)
    if data is None or not isinstance(data, dict):
        raise ValueError("Request body must contain valid JSON")
    return data

def parse_positive_int(value, field_name):
    if isinstance(value, bool):
        raise ValueError(f"{field_name} must be a positive integer")
    try:
        number = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field_name} must be a positive integer")
    if number <= 0:
        raise ValueError(f"{field_name} must be a positive integer")
    return number

def parse_non_negative_int(value, field_name):
    if isinstance(value, bool):
        raise ValueError(f"{field_name} must be a non-negative integer")
    try:
        number = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field_name} must be a non-negative integer")
    if number < 0:
        raise ValueError(f"{field_name} must be a non-negative integer")
    return number

def validate_date(date_text):
    if not isinstance(date_text, str):
        return False
    try:
        datetime.strptime(date_text, "%Y-%m-%d")
        return True
    except ValueError:
        return False

def validate_future_expiry(expiry_date):
    if not validate_date(expiry_date):
        return False, "Invalid expiry date format. Use YYYY-MM-DD"
    entered = datetime.strptime(expiry_date, "%Y-%m-%d").date()
    if entered <= date.today():
        return False, "Expired or same-day expiry cannot enter inventory"
    return True, None

def get_total_stock(conn, medicine_id):
    row = conn.execute("SELECT COALESCE(SUM(quantity), 0) AS total_stock FROM medicine_batches WHERE medicine_id = ?", (medicine_id,)).fetchone()
    return row["total_stock"]

def create_alert(alert_type, message, dedupe_key=None):
    conn = get_connection()
    try:
        target = dedupe_key or message
        existing = conn.execute("""SELECT id FROM alerts WHERE type=? AND status IN ('active','acknowledged') AND message LIKE ?""", (alert_type, f"%{target}%")).fetchone()
        if existing:
            return
        conn.execute("""INSERT INTO alerts(type,message,timestamp,status,acknowledged_at,resolved_at) VALUES(?,?,?,?,?,?)""", (alert_type, message, datetime.now().isoformat(), "active", None, None))
        conn.commit()
    finally:
        conn.close()

def resolve_inventory_alerts_for_medicine(medicine_name):
    conn = get_connection()
    try:
        conn.execute("""UPDATE alerts SET status='resolved', resolved_at=? WHERE type='Inventory' AND status IN ('active','acknowledged') AND message LIKE ?""", (datetime.now().isoformat(), f"%{medicine_name}%"))
        conn.commit()
    finally:
        conn.close()

def build_medicine_response(conn, medicine):
    batches = conn.execute("""SELECT id,batch_code,quantity,expiry_date,created_at FROM medicine_batches WHERE medicine_id=? AND quantity>0 ORDER BY expiry_date ASC,id ASC""", (medicine["id"],)).fetchall()
    stock = get_total_stock(conn, medicine["id"])
    return {
        "id": medicine["id"],
        "name": medicine["name"],
        "min_stock": medicine["min_stock"],
        "stock": stock,
        "batches": [dict(row) for row in batches]
    }
