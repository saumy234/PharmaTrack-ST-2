import sqlite3

from datetime import datetime, date

from flask import Blueprint, jsonify  # type: ignore[import-not-found]

from ..database import get_connection

from ..helpers import (
    get_json_body,
    parse_positive_int,
    validate_future_expiry,
    get_total_stock,
    resolve_inventory_alerts_for_medicine,
    get_inventory_analytics,
    get_inventory_distribution,
    get_inventory_alert_center,
    get_fefo_analysis,
    calculate_inventory_movement,
    get_demand_predictions,
    get_reorder_suggestions
)


bp = Blueprint("inventory_api", __name__)


# =========================================================
# RESTOCK MEDICINE
# =========================================================

@bp.put("/medicines/restock/<int:id>")
def restock_medicine(id):

    try:

        data = get_json_body()

        quantity = parse_positive_int(
            data.get("quantity"),
            "Quantity"
        )

        batch_code = str(
            data.get("batch_code", "")
        ).strip()

        expiry_date = data.get("expiry_date")

        if not batch_code:
            return jsonify({
                "error": "Batch code is required"
            }), 400

        if expiry_date is None:
            return jsonify({
                "error": "Expiry date is required"
            }), 400

        valid, error = validate_future_expiry(
            expiry_date
        )

        if not valid:
            return jsonify({
                "error": error
            }), 400

        conn = get_connection()

        try:

            # -------------------------------------------------
            # MEDICINE EXISTENCE CHECK
            # -------------------------------------------------

            medicine = conn.execute(
                """
                SELECT id, name, min_stock
                FROM medicines
                WHERE id = ?
                """,
                (id,)
            ).fetchone()

            if not medicine:
                return jsonify({
                    "error": "Medicine not found"
                }), 404

            # -------------------------------------------------
            # DUPLICATE BATCH CHECK
            # -------------------------------------------------

            existing_batch = conn.execute(
                """
                SELECT id
                FROM medicine_batches
                WHERE LOWER(TRIM(batch_code))
                      = LOWER(TRIM(?))
                LIMIT 1
                """,
                (batch_code,)
            ).fetchone()

            if existing_batch:
                return jsonify({
                    "error": "Batch code already exists"
                }), 409

            # -------------------------------------------------
            # CREATE NEW BATCH
            # -------------------------------------------------

            conn.execute(
                """
                INSERT INTO medicine_batches
                (
                    medicine_id,
                    batch_code,
                    quantity,
                    expiry_date,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    id,
                    batch_code,
                    quantity,
                    expiry_date,
                    datetime.now().isoformat()
                )
            )

            new_stock = get_total_stock(
                conn,
                id
            )

            conn.commit()

            # -------------------------------------------------
            # RESOLVE LOW STOCK ALERT
            # -------------------------------------------------

            if new_stock > medicine["min_stock"]:

                resolve_inventory_alerts_for_medicine(
                    medicine["name"]
                )

            return jsonify({
                "message": "Medicine restocked successfully",
                "new_stock": new_stock,
                "batch_code": batch_code
            })

        except sqlite3.IntegrityError as error:

            conn.rollback()

            return jsonify({
                "error": "Database constraint failed",
                "details": str(error)
            }), 409

        finally:

            conn.close()

    except ValueError as error:

        return jsonify({
            "error": str(error)
        }), 400


# =========================================================
# DELETE BATCH
# =========================================================
#
# Rules:
#
# 1. Expired batch -> can be deleted
# 2. Empty batch -> can be deleted
# 3. Active batch with stock -> cannot be deleted
#
# Additional rule:
#
# If deleting the batch leaves the medicine with ZERO
# remaining batches, the medicine itself is deleted.
#
# =========================================================

@bp.delete("/batches/<int:batch_id>")
def delete_batch(batch_id):

    conn = get_connection()

    try:

        # -------------------------------------------------
        # FIND BATCH
        # -------------------------------------------------

        batch = conn.execute(
            """
            SELECT
                id,
                medicine_id,
                expiry_date,
                quantity
            FROM medicine_batches
            WHERE id = ?
            """,
            (batch_id,)
        ).fetchone()

        if not batch:

            return jsonify({
                "error": "Batch not found"
            }), 404

        # -------------------------------------------------
        # FIND PARENT MEDICINE
        # -------------------------------------------------

        medicine = conn.execute(
            """
            SELECT
                id,
                name
            FROM medicines
            WHERE id = ?
            """,
            (batch["medicine_id"],)
        ).fetchone()

        if not medicine:

            return jsonify({
                "error": "Medicine associated with batch not found"
            }), 404

        # -------------------------------------------------
        # VALIDATE EXPIRY DATE
        # -------------------------------------------------

        try:

            expiry = datetime.strptime(
                batch["expiry_date"],
                "%Y-%m-%d"
            ).date()

        except (ValueError, TypeError):

            return jsonify({
                "error": "Stored batch has invalid expiry date"
            }), 500

        # -------------------------------------------------
        # PROTECT ACTIVE INVENTORY
        # -------------------------------------------------

        if (
            expiry > date.today()
            and batch["quantity"] > 0
        ):

            return jsonify({
                "error":
                    "Only expired or empty batches can be deleted"
            }), 400

        # -------------------------------------------------
        # DELETE BATCH
        # -------------------------------------------------

        conn.execute(
            """
            DELETE FROM medicine_batches
            WHERE id = ?
            """,
            (batch_id,)
        )

        # -------------------------------------------------
        # CHECK REMAINING BATCHES
        # -------------------------------------------------
        #
        # If there are no batches left for this medicine,
        # remove the medicine as well.
        #
        # -------------------------------------------------

        remaining_batches = conn.execute(
            """
            SELECT COUNT(*) AS batch_count
            FROM medicine_batches
            WHERE medicine_id = ?
            """,
            (batch["medicine_id"],)
        ).fetchone()

        medicine_deleted = False

        if remaining_batches["batch_count"] == 0:

            conn.execute(
                """
                DELETE FROM medicines
                WHERE id = ?
                """,
                (batch["medicine_id"],)
            )

            medicine_deleted = True

        # -------------------------------------------------
        # COMMIT EVERYTHING TOGETHER
        # -------------------------------------------------

        conn.commit()

        # -------------------------------------------------
        # RESPONSE
        # -------------------------------------------------

        if medicine_deleted:

            return jsonify({
                "message": "Batch and medicine deleted successfully",
                "medicine_deleted": True
            })

        return jsonify({
            "message": "Batch deleted successfully",
            "medicine_deleted": False
        })

    except sqlite3.IntegrityError as error:

        conn.rollback()

        return jsonify({
            "error": "Database constraint failed",
            "details": str(error)
        }), 409

    finally:

        conn.close()


# =========================================================
# STOCK REPORT
# INVENTORY ANALYTICS
# =========================================================

@bp.get("/inventory/analytics")
def inventory_analytics():

    conn = get_connection()

    try:

        analytics = get_inventory_analytics(
            conn
        )

        return jsonify(analytics)

    finally:

        conn.close()


# =========================================================
# STOCK REPORT
# INVENTORY DISTRIBUTION
# =========================================================

@bp.get("/inventory/distribution")
def inventory_distribution():

    conn = get_connection()

    try:

        data = get_inventory_distribution(
            conn
        )

        return jsonify(data)

    finally:

        conn.close()


# =========================================================
# STOCK REPORT
# INVENTORY ALERT CENTER
# =========================================================

@bp.get("/inventory/alerts")
def inventory_alerts():

    conn = get_connection()

    try:

        data = get_inventory_alert_center(
            conn
        )

        return jsonify(data)

    finally:

        conn.close()


# =========================================================
# STOCK REPORT
# FEFO RISK
# =========================================================

@bp.get("/inventory/fefo-risk")
def inventory_fefo_risk():

    conn = get_connection()

    try:

        analysis = get_fefo_analysis(
            conn
        )

        return jsonify(analysis)

    finally:

        conn.close()


# =========================================================
# INVENTORY MOVEMENT
#
# Used by Sales History / Sales Intelligence.
# =========================================================

@bp.get("/inventory/movement")
def inventory_movement():

    conn = get_connection()

    try:

        movement_data = (
            calculate_inventory_movement(
                conn
            )
        )

        return jsonify(movement_data)

    finally:

        conn.close()


# =========================================================
# DEMAND PREDICTION
#
# Used by the Demand Prediction page.
# Business calculations live in helpers.py.
# =========================================================

@bp.get("/inventory/demand-prediction")
def demand_prediction():

    conn = get_connection()

    try:

        data = get_demand_predictions(conn)

        return jsonify(data)

    finally:

        conn.close()


# =========================================================
# REORDER SUGGESTIONS
#
# Used by the Reorder Suggestions page.
# Business calculations live in helpers.py.
# =========================================================

@bp.get("/inventory/reorder-suggestions")
def reorder_suggestions():

    conn = get_connection()

    try:

        data = get_reorder_suggestions(conn)

        return jsonify(data)

    finally:

        conn.close()


# =========================================================
# GET EXPIRY BATCHES
#
# Returns all active batches with their expiry information.
#
# Used by:
# Expiry Tracking page
# =========================================================

@bp.get("/expiry-batches")
def get_expiry_batches():

    conn = get_connection()

    try:

        rows = conn.execute(
            """
            SELECT
                medicine_batches.id,
                medicines.name,
                medicine_batches.batch_code,
                medicine_batches.quantity,
                medicine_batches.expiry_date
            FROM medicine_batches
            JOIN medicines
            ON medicine_batches.medicine_id = medicines.id
            WHERE medicine_batches.quantity > 0
            ORDER BY medicine_batches.expiry_date ASC
            """
        ).fetchall()

        return jsonify([
            dict(row)
            for row in rows
        ])

    finally:

        conn.close()
