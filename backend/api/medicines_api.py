import sqlite3
from flask import Blueprint, jsonify  # type: ignore[import-not-found]
from ..database import get_connection
from ..helpers import (get_json_body, parse_positive_int, parse_non_negative_int, validate_future_expiry, build_medicine_response)

bp = Blueprint("medicines_api", __name__)

@bp.get("/medicines")
def get_medicines():
    conn = get_connection()
    try:
        medicines = conn.execute("SELECT id,name,min_stock FROM medicines ORDER BY name ASC").fetchall()
        return jsonify([build_medicine_response(conn, medicine) for medicine in medicines])
    finally:
        conn.close()

@bp.post("/medicines")
def add_medicine():
    try:
        data = get_json_body()
        name = str(data.get("name", "")).strip()
        batch_code = str(data.get("batch_code", "")).strip()
        expiry_date = data.get("expiry_date")
        if not name:
            return jsonify({"error":"Medicine name is required"}), 400
        if not batch_code:
            return jsonify({"error":"Batch code is required"}), 400
        if expiry_date is None:
            return jsonify({"error":"Expiry date is required"}), 400
        stock = parse_positive_int(data.get("stock"), "Stock")
        min_stock = parse_non_negative_int(data.get("min_stock"), "Minimum stock")
        valid, error = validate_future_expiry(expiry_date)
        if not valid:
            return jsonify({"error":error}), 400
        conn = get_connection()
        try:
            if conn.execute("SELECT id FROM medicines WHERE LOWER(TRIM(name))=LOWER(TRIM(?)) LIMIT 1", (name,)).fetchone():
                return jsonify({"error":"Medicine already exists. Use Restock instead."}), 409
            if conn.execute("SELECT id FROM medicine_batches WHERE LOWER(TRIM(batch_code))=LOWER(TRIM(?)) LIMIT 1", (batch_code,)).fetchone():
                return jsonify({"error":"Batch code already exists"}), 409
            cursor = conn.execute("INSERT INTO medicines(name,min_stock) VALUES(?,?)", (name, min_stock))
            medicine_id = cursor.lastrowid
            from datetime import datetime
            conn.execute("INSERT INTO medicine_batches(medicine_id,batch_code,quantity,expiry_date,created_at) VALUES(?,?,?,?,?)", (medicine_id,batch_code,stock,expiry_date,datetime.now().isoformat()))
            conn.commit()
            return jsonify({"message":"Medicine added successfully","medicine_id":medicine_id,"stock":stock,"batch_code":batch_code}), 201
        except sqlite3.IntegrityError as error:
            conn.rollback()
            return jsonify({"error":"Database constraint failed","details":str(error)}), 409
        finally:
            conn.close()
    except ValueError as error:
        return jsonify({"error":str(error)}), 400

@bp.delete("/medicines/<int:id>")
def delete_medicine(id):
    conn = get_connection()
    try:
        medicine = conn.execute("SELECT id FROM medicines WHERE id=?", (id,)).fetchone()
        if not medicine:
            return jsonify({"error":"Medicine not found"}), 404
        conn.execute("DELETE FROM medicines WHERE id=?", (id,))
        conn.commit()
        return jsonify({"message":"Medicine deleted successfully"})
    except sqlite3.IntegrityError as error:
        conn.rollback()
        return jsonify({"error":"Medicine could not be deleted","details":str(error)}), 409
    finally:
        conn.close()
