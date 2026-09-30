import sqlite3

from datetime import datetime

from flask import Blueprint, jsonify  # type: ignore[import-not-found]

from ..database import get_connection

from ..helpers import (
    get_json_body,
    parse_positive_int,
    get_total_stock,
    create_alert,
    resolve_inventory_alerts_for_medicine,
    get_medicine_sales_map,
    get_daily_sales_map,
    get_sales_summary,
    get_fefo_analysis
)


bp = Blueprint("sales_api", __name__)


# =========================================================
# ADD SALE
# =========================================================
@bp.post("/sales")
def add_sale():

    try:

        data = get_json_body()

        medicine_id = data.get("medicine_id")

        if medicine_id is None:
            return jsonify({
                "error": "Medicine ID is required"
            }), 400

        try:

            medicine_id = int(medicine_id)

            quantity = parse_positive_int(
                data.get("quantity"),
                "Quantity"
            )

        except (ValueError, TypeError) as error:

            return jsonify({
                "error": str(error)
            }), 400

        conn = get_connection()

        try:

            medicine = conn.execute(
                """
                SELECT
                    id,
                    name,
                    min_stock
                FROM medicines
                WHERE id = ?
                """,
                (medicine_id,)
            ).fetchone()

            if not medicine:

                return jsonify({
                    "error": "Medicine not found"
                }), 404

            # =================================================
            # CHECK TOTAL STOCK
            # =================================================

            total_stock = get_total_stock(
                conn,
                medicine_id
            )

            if total_stock < quantity:

                return jsonify({
                    "error": "Insufficient stock",
                    "available_stock": total_stock
                }), 400

            # =================================================
            # FEFO STOCK DEDUCTION
            #
            # Earliest expiry batch is consumed first.
            # =================================================

            remaining = quantity

            batches = conn.execute(
                """
                SELECT
                    id,
                    quantity
                FROM medicine_batches
                WHERE medicine_id = ?
                AND quantity > 0
                ORDER BY expiry_date ASC, id ASC
                """,
                (medicine_id,)
            ).fetchall()

            for batch in batches:

                if remaining <= 0:
                    break

                if batch["quantity"] >= remaining:

                    new_quantity = (
                        batch["quantity"] - remaining
                    )

                    if new_quantity == 0:

                        conn.execute(
                            """
                            DELETE FROM medicine_batches
                            WHERE id = ?
                            """,
                            (batch["id"],)
                        )

                    else:

                        conn.execute(
                            """
                            UPDATE medicine_batches
                            SET quantity = ?
                            WHERE id = ?
                            """,
                            (
                                new_quantity,
                                batch["id"]
                            )
                        )

                    remaining = 0

                else:

                    conn.execute(
                        """
                        DELETE FROM medicine_batches
                        WHERE id = ?
                        """,
                        (batch["id"],)
                    )

                    remaining -= batch["quantity"]

            # =================================================
            # SAFETY CHECK
            # =================================================

            if remaining != 0:

                conn.rollback()

                return jsonify({
                    "error":
                    "Sale could not be completed safely"
                }), 500

            # =================================================
            # RECORD SALE
            # =================================================

            conn.execute(
                """
                INSERT INTO sales
                (
                    medicine_id,
                    quantity,
                    timestamp
                )
                VALUES (?, ?, ?)
                """,
                (
                    medicine_id,
                    quantity,
                    datetime.now().strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                )
            )

            updated_stock = get_total_stock(
                conn,
                medicine_id
            )

            conn.commit()

        except sqlite3.IntegrityError as error:

            conn.rollback()

            return jsonify({
                "error": "Database constraint failed",
                "details": str(error)
            }), 409

        finally:

            conn.close()

        # =====================================================
        # LOW STOCK ALERT
        # =====================================================

        if updated_stock <= medicine["min_stock"]:

            create_alert(
                "Inventory",
                (
                    f"Low stock detected for "
                    f"{medicine['name']}: "
                    f"{updated_stock} remaining"
                ),
                dedupe_key=medicine["name"]
            )

        else:

            resolve_inventory_alerts_for_medicine(
                medicine["name"]
            )

        return jsonify({
            "message":
            "Sale recorded successfully",

            "remaining_stock":
            updated_stock
        })

    except ValueError as error:

        return jsonify({
            "error": str(error)
        }), 400


# =========================================================
# GET SALES
#
# Returns complete sales history.
# =========================================================

@bp.get("/sales")
def get_sales():

    conn = get_connection()

    try:

        rows = conn.execute(
            """
            SELECT
                sales.id,
                medicines.name,
                sales.quantity,
                sales.timestamp

            FROM sales

            JOIN medicines
            ON sales.medicine_id = medicines.id

            ORDER BY sales.id DESC
            """
        ).fetchall()

        return jsonify([
            dict(row)
            for row in rows
        ])

    finally:

        conn.close()


# =========================================================
# SALES ANALYTICS
#
# Returns:
# - total sales records
# - total units sold
# - estimated revenue
# - top selling medicine
# - peak sales day
# - average units per sale
# - fastest moving
# - slowest moving
# - highest movement risk
# =========================================================

@bp.get("/sales/analytics")
def sales_analytics():

    conn = get_connection()

    try:

        analytics = get_sales_summary(conn)

        return jsonify(analytics)

    finally:

        conn.close()


# =========================================================
# SALES TRENDS
#
# Returns:
# - daily sales
# - medicine-wise sales
# =========================================================

@bp.get("/sales/trends")
def sales_trends():

    conn = get_connection()

    try:

        daily_map = get_daily_sales_map(conn)

        medicine_map = get_medicine_sales_map(conn)

        daily_sales = []

        top_medicines = []

        for day, units in daily_map.items():

            daily_sales.append({
                "date": day,
                "units": units
            })

        for medicine, units in medicine_map.items():

            top_medicines.append({
                "medicine": medicine,
                "units": units
            })

        return jsonify({
            "daily_sales": daily_sales,
            "top_medicines": top_medicines
        })

    finally:

        conn.close()


# =========================================================
# SALES ACTIVITY FEED
#
# Returns the latest 10 sales events.
# =========================================================

@bp.get("/sales/activity")
def sales_activity():

    conn = get_connection()

    try:

        rows = conn.execute(
            """
            SELECT
                sales.id,
                medicines.name,
                sales.quantity,
                sales.timestamp

            FROM sales

            JOIN medicines
            ON sales.medicine_id = medicines.id

            ORDER BY sales.id DESC

            LIMIT 10
            """
        ).fetchall()

        activity_feed = []

        for row in rows:

            activity_feed.append({

                "type":
                "sale",

                "title":
                "FEFO Sale Executed",

                "medicine":
                row["name"],

                "quantity":
                row["quantity"],

                "message":
                (
                    f"{row['name']} sold "
                    f"({row['quantity']} units)"
                ),

                "timestamp":
                row["timestamp"]
            })

        return jsonify(activity_feed)

    finally:

        conn.close()


# =========================================================
# FEFO ANALYTICS
#
# Used by Sales History / Sales Intelligence.
#
# Returns:
# - near expiry batches
# - near expiry batch count
# - total near expiry units
# =========================================================

@bp.get("/sales/fefo-analysis")
def sales_fefo_analysis():

    conn = get_connection()

    try:

        analysis = get_fefo_analysis(conn)

        return jsonify(analysis)

    finally:

        conn.close()
