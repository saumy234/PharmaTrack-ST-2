from datetime import datetime
from flask import Blueprint, jsonify  # type: ignore[import-not-found]
from ..database import get_connection
from ..helpers import get_json_body, create_alert, COLD_CHAIN_MAX_TEMPERATURE

bp = Blueprint("cold_chain_api", __name__)

@bp.post("/temperature")
def add_temperature():
    try:
        data = get_json_body()
        device_id = data.get("device_id")
        temperature = data.get("temperature")
        humidity = data.get("humidity")
        if device_id is None or str(device_id).strip() == "":
            return jsonify({"error":"Device ID is required"}), 400
        try:
            temperature = float(temperature)
        except (TypeError, ValueError):
            return jsonify({"error":"Temperature must be numeric"}), 400
        if humidity is not None:
            try:
                humidity = float(humidity)
            except (TypeError, ValueError):
                return jsonify({"error":"Humidity must be numeric"}), 400
        conn = get_connection()
        try:
            conn.execute("INSERT INTO temperature_logs(device_id,temperature,humidity,timestamp) VALUES(?,?,?,?)", (str(device_id),temperature,humidity,datetime.now().isoformat()))
            conn.commit()
        finally:
            conn.close()

        if temperature > COLD_CHAIN_MAX_TEMPERATURE:
            create_alert("Temperature", f"High temperature detected: {temperature}°C", dedupe_key="temperature_breach")
        else:
            conn = get_connection()
            try:
                conn.execute("UPDATE alerts SET status='resolved',resolved_at=? WHERE type='Temperature' AND status IN ('active','acknowledged')", (datetime.now().isoformat(),))
                conn.commit()
            finally:
                conn.close()
        return jsonify({"message":"Temperature logged"}), 201
    except ValueError as error:
        return jsonify({"error":str(error)}), 400

@bp.get("/temperature")
def get_temperature():
    conn = get_connection()
    try:
        rows = conn.execute("SELECT id,device_id,temperature,humidity,timestamp FROM temperature_logs ORDER BY id DESC").fetchall()
        return jsonify([dict(row) for row in rows])
    finally:
        conn.close()

@bp.get("/alerts")
def get_alerts():
    conn = get_connection()
    try:
        rows = conn.execute("SELECT id,type,message,timestamp,status,acknowledged_at,resolved_at FROM alerts ORDER BY id DESC").fetchall()
        return jsonify([dict(row) for row in rows])
    finally:
        conn.close()
