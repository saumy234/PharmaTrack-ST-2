from datetime import datetime

from flask import Blueprint, jsonify  # type: ignore[import-not-found]

from ..database import get_connection

from ..helpers import (
    get_json_body,
    create_alert,
    COLD_CHAIN_MAX_TEMPERATURE,
    get_alert_command_center
)


bp = Blueprint("cold_chain_api", __name__)


# =========================================================
# ADD TEMPERATURE
# =========================================================

@bp.post("/temperature")
def add_temperature():

    try:

        data = get_json_body()

        device_id = data.get("device_id")
        temperature = data.get("temperature")
        humidity = data.get("humidity")

        # -------------------------------------------------
        # DEVICE ID VALIDATION
        # -------------------------------------------------

        if device_id is None or str(device_id).strip() == "":
            return jsonify({
                "error": "Device ID is required"
            }), 400

        # -------------------------------------------------
        # TEMPERATURE VALIDATION
        # -------------------------------------------------

        try:

            temperature = float(temperature)

        except (TypeError, ValueError):

            return jsonify({
                "error": "Temperature must be numeric"
            }), 400

        # -------------------------------------------------
        # HUMIDITY VALIDATION
        # -------------------------------------------------

        if humidity is not None:

            try:

                humidity = float(humidity)

            except (TypeError, ValueError):

                return jsonify({
                    "error": "Humidity must be numeric"
                }), 400

        # -------------------------------------------------
        # SAVE TEMPERATURE
        # -------------------------------------------------

        conn = get_connection()

        try:

            conn.execute(
                """
                INSERT INTO temperature_logs
                (
                    device_id,
                    temperature,
                    humidity,
                    timestamp
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    str(device_id),
                    temperature,
                    humidity,
                    datetime.now().isoformat()
                )
            )

            conn.commit()

        finally:

            conn.close()

        # -------------------------------------------------
        # HIGH TEMPERATURE ALERT
        # -------------------------------------------------

        if temperature > COLD_CHAIN_MAX_TEMPERATURE:

            create_alert(
                "Temperature",
                f"High temperature detected: {temperature}°C",
                dedupe_key="temperature_breach"
            )

        # -------------------------------------------------
        # TEMPERATURE RETURNED TO SAFE RANGE
        # -------------------------------------------------

        else:

            conn = get_connection()

            try:

                conn.execute(
                    """
                    UPDATE alerts
                    SET
                        status = 'resolved',
                        resolved_at = ?
                    WHERE
                        type = 'Temperature'
                        AND status IN ('active', 'acknowledged')
                    """,
                    (
                        datetime.now().isoformat(),
                    )
                )

                conn.commit()

            finally:

                conn.close()

        return jsonify({
            "message": "Temperature logged"
        }), 201

    except ValueError as error:

        return jsonify({
            "error": str(error)
        }), 400


# =========================================================
# GET TEMPERATURE
# =========================================================

@bp.get("/temperature")
def get_temperature():

    conn = get_connection()

    try:

        rows = conn.execute(
            """
            SELECT
                id,
                device_id,
                temperature,
                humidity,
                timestamp
            FROM temperature_logs
            ORDER BY id DESC
            """
        ).fetchall()

        return jsonify([
            dict(row)
            for row in rows
        ])

    finally:

        conn.close()


# =========================================================
# GET ALERTS
# =========================================================

@bp.get("/alerts")
def get_alerts():

    conn = get_connection()

    try:

        rows = conn.execute(
            """
            SELECT
                id,
                type,
                message,
                timestamp,
                status,
                acknowledged_at,
                resolved_at
            FROM alerts
            ORDER BY id DESC
            """
        ).fetchall()

        return jsonify([
            dict(row)
            for row in rows
        ])

    finally:

        conn.close()


# =========================================================
# ALERTS COMMAND CENTER
# =========================================================

@bp.get("/alerts/command-center")
def alert_command_center():

    conn = get_connection()

    try:

        data = get_alert_command_center(conn)

        return jsonify(data)

    finally:

        conn.close()


# =========================================================
# ACKNOWLEDGE ALERT
# =========================================================

@bp.put("/acknowledge_alert/<int:alert_id>")
def acknowledge_alert(alert_id):

    conn = get_connection()

    try:

        alert = conn.execute(
            """
            SELECT
                id,
                status
            FROM alerts
            WHERE id = ?
            """,
            (alert_id,)
        ).fetchone()

        # -------------------------------------------------
        # ALERT NOT FOUND
        # -------------------------------------------------

        if not alert:

            return jsonify({
                "error": "Alert not found"
            }), 404

        # -------------------------------------------------
        # CANNOT ACKNOWLEDGE RESOLVED ALERT
        # -------------------------------------------------

        if alert["status"] == "resolved":

            return jsonify({
                "error": "Resolved alert cannot be acknowledged"
            }), 400

        # -------------------------------------------------
        # ACKNOWLEDGE
        # -------------------------------------------------

        conn.execute(
            """
            UPDATE alerts
            SET
                status = 'acknowledged',
                acknowledged_at = ?
            WHERE id = ?
            """,
            (
                datetime.now().isoformat(),
                alert_id
            )
        )

        conn.commit()

        return jsonify({
            "message": "Alert acknowledged"
        })

    finally:

        conn.close()


# =========================================================
# RESOLVE ALERT
# =========================================================

@bp.put("/resolve_alert/<int:alert_id>")
def resolve_alert(alert_id):

    conn = get_connection()

    try:

        alert = conn.execute(
            """
            SELECT
                id
            FROM alerts
            WHERE id = ?
            """,
            (alert_id,)
        ).fetchone()

        # -------------------------------------------------
        # ALERT NOT FOUND
        # -------------------------------------------------

        if not alert:

            return jsonify({
                "error": "Alert not found"
            }), 404

        # -------------------------------------------------
        # RESOLVE ALERT
        # -------------------------------------------------

        conn.execute(
            """
            UPDATE alerts
            SET
                status = 'resolved',
                resolved_at = ?
            WHERE id = ?
            """,
            (
                datetime.now().isoformat(),
                alert_id
            )
        )

        conn.commit()

        return jsonify({
            "message": "Alert resolved"
        })

    finally:

        conn.close()
