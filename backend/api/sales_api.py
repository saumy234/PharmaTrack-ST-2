import sqlite3
from datetime import datetime
from flask import Blueprint, jsonify  # type: ignore[import-not-found]
from ..database import get_connection
from ..helpers import get_json_body, parse_positive_int, get_total_stock, create_alert, resolve_inventory_alerts_for_medicine

bp = Blueprint("sales_api", __name__)

@bp.post("/sales")
def add_sale():
    try:
        data = get_json_body()
        medicine_id = data.get("medicine_id")
        if medicine_id is None:
            return jsonify({"error":"Medicine ID is required"}), 400
        try:
            medicine_id = int(medicine_id)
            quantity = parse_positive_int(data.get("quantity"), "Quantity")
        except (ValueError, TypeError) as error:
            return jsonify({"error":str(error)}), 400
        conn = get_connection()
        try:
            medicine = conn.execute("SELECT id,name,min_stock FROM medicines WHERE id=?", (medicine_id,)).fetchone()
            if not medicine:
                return jsonify({"error":"Medicine not found"}), 404
            total_stock = get_total_stock(conn, medicine_id)
            if total_stock < quantity:
                return jsonify({"error":"Insufficient stock","available_stock":total_stock}), 400
            remaining = quantity
            batches = conn.execute("SELECT id,quantity FROM medicine_batches WHERE medicine_id=? AND quantity>0 ORDER BY expiry_date ASC,id ASC", (medicine_id,)).fetchall()
            for batch in batches:
                if remaining <= 0:
                    break
                if batch["quantity"] >= remaining:
                    new_quantity = batch["quantity"] - remaining
                    if new_quantity == 0:
                        conn.execute("DELETE FROM medicine_batches WHERE id=?", (batch["id"],))
                    else:
                        conn.execute("UPDATE medicine_batches SET quantity=? WHERE id=?", (new_quantity,batch["id"]))
                    remaining = 0
                else:
                    conn.execute("DELETE FROM medicine_batches WHERE id=?", (batch["id"],))
                    remaining -= batch["quantity"]
            if remaining != 0:
                conn.rollback()
                return jsonify({"error":"Sale could not be completed safely"}), 500
            conn.execute("INSERT INTO sales(medicine_id,quantity,timestamp) VALUES(?,?,?)", (medicine_id,quantity,datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            updated_stock = get_total_stock(conn,medicine_id)
            conn.commit()
        except sqlite3.IntegrityError as error:
            conn.rollback()
            return jsonify({"error":"Database constraint failed","details":str(error)}), 409
        finally:
            conn.close()
        if updated_stock <= medicine["min_stock"]:
            create_alert("Inventory", f"Low stock detected for {medicine['name']}: {updated_stock} remaining", dedupe_key=medicine["name"])
        else:
            resolve_inventory_alerts_for_medicine(medicine["name"])
        return jsonify({"message":"Sale recorded successfully","remaining_stock":updated_stock})
    except ValueError as error:
        return jsonify({"error":str(error)}), 400
