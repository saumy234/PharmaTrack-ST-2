import sqlite3
from datetime import datetime, date
from flask import Blueprint, jsonify  # type: ignore[import-not-found]
from ..database import get_connection
from ..helpers import get_json_body, parse_positive_int, validate_future_expiry, get_total_stock, resolve_inventory_alerts_for_medicine

bp = Blueprint("inventory_api", __name__)

@bp.put("/medicines/restock/<int:id>")
def restock_medicine(id):
    try:
        data = get_json_body()
        quantity = parse_positive_int(data.get("quantity"), "Quantity")
        batch_code = str(data.get("batch_code", "")).strip()
        expiry_date = data.get("expiry_date")
        if not batch_code:
            return jsonify({"error":"Batch code is required"}), 400
        if expiry_date is None:
            return jsonify({"error":"Expiry date is required"}), 400
        valid, error = validate_future_expiry(expiry_date)
        if not valid:
            return jsonify({"error":error}), 400
        conn = get_connection()
        try:
            medicine = conn.execute("SELECT id,name,min_stock FROM medicines WHERE id=?", (id,)).fetchone()
            if not medicine:
                return jsonify({"error":"Medicine not found"}), 404
            if conn.execute("SELECT id FROM medicine_batches WHERE LOWER(TRIM(batch_code))=LOWER(TRIM(?)) LIMIT 1", (batch_code,)).fetchone():
                return jsonify({"error":"Batch code already exists"}), 409
            conn.execute("INSERT INTO medicine_batches(medicine_id,batch_code,quantity,expiry_date,created_at) VALUES(?,?,?,?,?)", (id,batch_code,quantity,expiry_date,datetime.now().isoformat()))
            new_stock = get_total_stock(conn,id)
            conn.commit()
            if new_stock > medicine["min_stock"]:
                resolve_inventory_alerts_for_medicine(medicine["name"])
            return jsonify({"message":"Medicine restocked successfully","new_stock":new_stock,"batch_code":batch_code})
        except sqlite3.IntegrityError as error:
            conn.rollback()
            return jsonify({"error":"Database constraint failed","details":str(error)}), 409
        finally:
            conn.close()
    except ValueError as error:
        return jsonify({"error":str(error)}), 400

@bp.delete("/batches/<int:batch_id>")
def delete_batch(batch_id):
    conn = get_connection()
    try:
        batch = conn.execute("SELECT * FROM medicine_batches WHERE id=?", (batch_id,)).fetchone()
        if not batch:
            return jsonify({"error":"Batch not found"}), 404
        try:
            expiry = datetime.strptime(batch["expiry_date"], "%Y-%m-%d").date()
        except (ValueError, TypeError):
            return jsonify({"error":"Stored batch has invalid expiry date"}), 500
        if expiry > date.today() and batch["quantity"] > 0:
            return jsonify({"error":"Only expired or empty batches can be deleted"}), 400
        conn.execute("DELETE FROM medicine_batches WHERE id=?", (batch_id,))
        conn.commit()
        return jsonify({"message":"Batch deleted successfully"})
    finally:
        conn.close()
