from flask import Blueprint, jsonify  # type: ignore[import-not-found]

from ..database import get_connection

from ..helpers import (
    get_reorder_suggestions,
    get_alert_command_center,
    get_sales_summary,
    get_fefo_analysis
)


bp = Blueprint("assistant_api", __name__)


# =========================================================
# ASSISTANT QUERY ENGINE
# =========================================================
#
# Main endpoint used by the Assistant page.
#
# The frontend sends:
#
# {
#     "query": "Which medicines need reorder?"
# }
#
# This API determines the requested operation and calls
# the appropriate backend business-logic function.
#
# =========================================================


@bp.post("/ai-assistant")
def assistant_query():

    from flask import request # type: ignore[import-not-found]


    data = request.get_json(silent=True)

    # -----------------------------------------------------
    # VALIDATE REQUEST
    # -----------------------------------------------------

    if data is None or not isinstance(data, dict):

        return jsonify({
            "error": "Request body must contain valid JSON"
        }), 400

    query = str(
        data.get("query", "")
    ).strip()

    if not query:

        return jsonify({
            "error": "Query is required"
        }), 400

    lower = query.lower()

    conn = get_connection()

    try:

        # =================================================
        # REORDER INTELLIGENCE
        # =================================================

        if (
            "reorder" in lower
            or "low stock" in lower
            or "restock" in lower
            or "stock shortage" in lower
            or "which medicines need" in lower
        ):

            reorder_data = get_reorder_suggestions(
                conn
            )

            reorder_items = reorder_data.get(
                "reorders",
                []
            )

            return jsonify({

                "type":
                    "reorder_list",

                "title":
                    "Reorder Intelligence",

                "summary":
                    (
                        f"{len(reorder_items)} "
                        f"medicines require reorder attention."
                    ),

                "items":
                    reorder_items,

                "data":
                    reorder_data

            })


        # =================================================
        # CRITICAL ALERTS
        # =================================================

        elif (
            "critical alert" in lower
            or "critical alerts" in lower
            or "show alerts" in lower
            or "show critical" in lower
            or lower == "alerts"
            or "alert" in lower
        ):

            alert_data = get_alert_command_center(
                conn
            )

            alerts = alert_data.get(
                "alerts",
                []
            )

            # Only active alerts are considered
            # currently active incidents.

            active_alerts = [

                alert

                for alert in alerts

                if str(
                    alert.get("status", "")
                ).lower() == "active"

            ]

            return jsonify({

                "type":
                    "alert_list",

                "title":
                    "Alert Intelligence",

                "summary":
                    (
                        f"{len(active_alerts)} "
                        f"active alerts detected."
                    ),

                "items":
                    active_alerts,

                "data":
                    alert_data

            })


        # =================================================
        # HIGHEST DEMAND
        # =================================================

        elif (
            "highest demand" in lower
            or "highest selling" in lower
            or "top medicine" in lower
            or "top selling" in lower
            or "most sold" in lower
            or "demand" in lower
        ):

            sales_data = get_sales_summary(
                conn
            )

            return jsonify({

                "type":
                    "top_medicine",

                "title":
                    "Demand Intelligence",

                "medicine":
                    sales_data.get(
                        "top_selling_medicine",
                        "--"
                    ),

                "units_sold":
                    sales_data.get(
                        "total_units_sold",
                        0
                    ),

                "summary":
                    (
                        "Current sales data identifies "
                        f"{sales_data.get('top_selling_medicine', '--')} "
                        "as the top-selling medicine."
                    ),

                "data":
                    sales_data

            })


        # =================================================
        # EXPIRY / FEFO RISK
        # =================================================

        elif (
            "expire" in lower
            or "expiry" in lower
            or "near expiry" in lower
            or "expiring" in lower
            or "fefo" in lower
        ):

            fefo_data = get_fefo_analysis(
                conn
            )

            expiry_items = fefo_data.get(
                "near_expiry_batches",
                []
            )

            formatted_items = [

                {
                    "name":
                        item.get(
                            "medicine",
                            "--"
                        ),

                    "batch_code":
                        item.get(
                            "batch_code",
                            "--"
                        ),

                    "expiry_date":
                        item.get(
                            "expiry_date",
                            "--"
                        ),

                    "days_left":
                        item.get(
                            "days_remaining",
                            0
                        ),

                    "quantity":
                        item.get(
                            "quantity",
                            0
                        )
                }

                for item in expiry_items

            ]

            return jsonify({

                "type":
                    "expiry_list",

                "title":
                    "Expiry Risk Analysis",

                "summary":
                    (
                        f"{len(expiry_items)} "
                        "batches are near expiry."
                    ),

                "items":
                    formatted_items,

                "data":
                    fefo_data

            })


        # =================================================
        # DEFAULT RESPONSE
        # =================================================

        else:

            return jsonify({

                "type":
                    "default",

                "title":
                    "Assistant",

                "response":
                    (
                        "I can help with inventory "
                        "reorder status, critical alerts, "
                        "demand intelligence, and expiry "
                        "risk analysis. Try asking one "
                        "of these questions directly."
                    )

            })

    finally:

        conn.close()