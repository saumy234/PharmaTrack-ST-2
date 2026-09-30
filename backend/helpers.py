
import math
from datetime import datetime, date
from flask import request  # type: ignore[import-not-found]
from .database import get_connection


# =========================================================
# COLD CHAIN CONFIGURATION
# =========================================================

COLD_CHAIN_MAX_TEMPERATURE = 28.0


# =========================================================
# JSON BODY
# =========================================================

def get_json_body():

    data = request.get_json(silent=True)

    if data is None or not isinstance(data, dict):
        raise ValueError(
            "Request body must contain valid JSON"
        )

    return data


# =========================================================
# POSITIVE INTEGER
# =========================================================

def parse_positive_int(value, field_name):

    if isinstance(value, bool):
        raise ValueError(
            f"{field_name} must be a positive integer"
        )

    try:
        number = int(value)

    except (TypeError, ValueError):

        raise ValueError(
            f"{field_name} must be a positive integer"
        )

    if number <= 0:

        raise ValueError(
            f"{field_name} must be a positive integer"
        )

    return number


# =========================================================
# NON-NEGATIVE INTEGER
# =========================================================

def parse_non_negative_int(value, field_name):

    if isinstance(value, bool):
        raise ValueError(
            f"{field_name} must be a non-negative integer"
        )

    try:
        number = int(value)

    except (TypeError, ValueError):

        raise ValueError(
            f"{field_name} must be a non-negative integer"
        )

    if number < 0:

        raise ValueError(
            f"{field_name} must be a non-negative integer"
        )

    return number


# =========================================================
# DATE VALIDATION
# =========================================================

def validate_date(date_text):

    if not isinstance(date_text, str):
        return False

    try:

        datetime.strptime(
            date_text,
            "%Y-%m-%d"
        )

        return True

    except ValueError:

        return False


# =========================================================
# FUTURE EXPIRY VALIDATION
# =========================================================

def validate_future_expiry(expiry_date):

    if not validate_date(expiry_date):

        return (
            False,
            "Invalid expiry date format. Use YYYY-MM-DD"
        )

    entered = datetime.strptime(
        expiry_date,
        "%Y-%m-%d"
    ).date()

    if entered <= date.today():

        return (
            False,
            "Expired or same-day expiry cannot enter inventory"
        )

    return True, None


# =========================================================
# TOTAL STOCK
# =========================================================

def get_total_stock(conn, medicine_id):

    row = conn.execute(
        """
        SELECT
            COALESCE(SUM(quantity), 0)
            AS total_stock
        FROM medicine_batches
        WHERE medicine_id = ?
        """,
        (medicine_id,)
    ).fetchone()

    return row["total_stock"]


# =========================================================
# CREATE ALERT
# =========================================================

def create_alert(
    alert_type,
    message,
    dedupe_key=None
):

    conn = get_connection()

    try:

        target = dedupe_key or message

        existing = conn.execute(
            """
            SELECT id
            FROM alerts
            WHERE type = ?
            AND status IN ('active', 'acknowledged')
            AND message LIKE ?
            """,
            (
                alert_type,
                f"%{target}%"
            )
        ).fetchone()

        if existing:
            return

        conn.execute(
            """
            INSERT INTO alerts
            (
                type,
                message,
                timestamp,
                status,
                acknowledged_at,
                resolved_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                alert_type,
                message,
                datetime.now().isoformat(),
                "active",
                None,
                None
            )
        )

        conn.commit()

    finally:

        conn.close()


# =========================================================
# RESOLVE INVENTORY ALERTS
# =========================================================

def resolve_inventory_alerts_for_medicine(
    medicine_name
):

    conn = get_connection()

    try:

        conn.execute(
            """
            UPDATE alerts
            SET
                status = 'resolved',
                resolved_at = ?
            WHERE type = 'Inventory'
            AND status IN ('active', 'acknowledged')
            AND message LIKE ?
            """,
            (
                datetime.now().isoformat(),
                f"%{medicine_name}%"
            )
        )

        conn.commit()

    finally:

        conn.close()


# =========================================================
# ALERT COMMAND CENTER
# =========================================================

def get_alert_command_center(conn):

    alerts = conn.execute("""
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
    """).fetchall()

    # -----------------------------------------------------
    # BASIC COUNTS
    # -----------------------------------------------------

    active = 0
    acknowledged = 0
    resolved = 0
    critical = 0
    sla_breaches = 0

    temperature_alerts = 0
    inventory_alerts = 0

    timeline = []
    incident_feed = []

    for alert in alerts:

        status = (
            alert["status"] or ""
        ).lower()

        created = datetime.fromisoformat(
            alert["timestamp"]
        )

        minutes_open = int(
            (
                datetime.now() - created
            ).total_seconds() / 60
        )

        # -------------------------------------------------
        # SLA
        # -------------------------------------------------

        if (
            minutes_open > 30
            and status != "resolved"
        ):
            sla_breaches += 1

        # -------------------------------------------------
        # TYPE
        # -------------------------------------------------

        type_text = (
            alert["type"] or ""
        ).lower()

        message_text = (
            alert["message"] or ""
        ).lower()

        if "temperature" in type_text:
            temperature_alerts += 1

        elif any(
            keyword in (
                type_text + " " + message_text
            )
            for keyword in [
                "inventory",
                "stock",
                "low stock",
                "expiry",
                "expired",
                "shortage",
                "procurement",
                "medicine shortage"
            ]
        ):
            inventory_alerts += 1

        # -------------------------------------------------
        # STATUS
        # -------------------------------------------------

        if status == "active":

            active += 1
            critical += 1

        elif status == "acknowledged":

            acknowledged += 1

        elif status == "resolved":

            resolved += 1

        # -------------------------------------------------
        # TIMELINE
        # -------------------------------------------------

        timeline.append({
            "id": alert["id"],
            "type": alert["type"],
            "message": alert["message"],
            "status": status,
            "timestamp": alert["timestamp"],
            "minutes_open": minutes_open
        })

        # -------------------------------------------------
        # INCIDENT FEED
        # -------------------------------------------------

        incident_feed.append({
            "id": alert["id"],
            "type": alert["type"],
            "message": alert["message"],
            "status": status,
            "timestamp": alert["timestamp"],
            "minutes_open": minutes_open
        })

    # -----------------------------------------------------
    # INVENTORY / FEFO DATA
    # -----------------------------------------------------

    inventory_alerts_data = (
        get_inventory_alert_center(conn)
    )

    fefo_risk = get_fefo_analysis(conn)

    inventory_count = (
        len(inventory_alerts_data)
        +
        fefo_risk["near_expiry_batch_count"]
    )

    # -----------------------------------------------------
    # HEALTH SCORE
    # -----------------------------------------------------

    health = max(
        100
        - (critical * 20)
        - (acknowledged * 10),
        10
    )

    # -----------------------------------------------------
    # AVERAGE RESPONSE
    # -----------------------------------------------------

    average_response = (
        critical * 7
        +
        acknowledged * 4
    )

    # -----------------------------------------------------
    # CLUSTERS
    # -----------------------------------------------------

    clusters = []

    if temperature_alerts >= 2:

        clusters.append({
            "title":
                "Cold Chain Failure Cluster",
            "count":
                temperature_alerts
        })

    if inventory_count >= 2:

        clusters.append({
            "title":
                "Inventory Disruption Cluster",
            "count":
                inventory_count
        })

    if sla_breaches >= 2:

        clusters.append({
            "title":
                "Operational Delay Cluster",
            "count":
                sla_breaches
        })

    if not clusters:

        clusters.append({
            "title":
                "No correlated clusters detected",
            "count":
                0
        })

    # -----------------------------------------------------
    # IMPACT
    # -----------------------------------------------------

    impact = {
        "revenue_exposure":
            active * 5000,

        "affected_medicines":
            temperature_alerts * 3,

        "operational_risk":
            (
                "High"
                if health < 60
                else "Moderate"
            )
    }

    # -----------------------------------------------------
    # RISK HEATMAP
    # -----------------------------------------------------

    heatmap = [
        {
            "category": "Cold Chain",
            "value": temperature_alerts * 20,
            "level": "high"
        },
        {
            "category": "Inventory",
            "value": inventory_count * 15,
            "level": "medium"
        },
        {
            "category": "Expiry",
            "value": acknowledged * 10,
            "level": "medium"
        },
        {
            "category": "Procurement",
            "value": max(
                5,
                inventory_count * 5
            ),
            "level": "low"
        }
    ]

    # -----------------------------------------------------
    # OPERATIONAL RECOMMENDATIONS
    # -----------------------------------------------------

    recommendations = []

    if temperature_alerts > 0:

        recommendations.append(
            "Inspect refrigeration unit immediately"
        )

    if temperature_alerts >= 2:

        recommendations.append(
            "Transfer stock to backup cold storage"
        )

    if inventory_count > 0:

        recommendations.append(
            "Trigger emergency procurement workflow"
        )

    if (
        fefo_risk["near_expiry_batch_count"]
        > 0
    ):

        recommendations.append(
            "Review "
            + str(
                fefo_risk[
                    "near_expiry_batch_count"
                ]
            )
            + " near-expiry batches"
        )

    if sla_breaches > 2:

        recommendations.append(
            "Escalate unresolved incidents to supervisor"
        )

    if not recommendations:

        recommendations.append(
            "System healthy — continue monitoring"
        )

    # -----------------------------------------------------
    # CHART DATA
    # -----------------------------------------------------

    trend = [
        2,
        4,
        3,
        5,
        active + acknowledged
    ]

    status_distribution = {
        "active": active,
        "acknowledged": acknowledged,
        "resolved": resolved
    }

    type_distribution = {
        "temperature": temperature_alerts,
        "inventory": inventory_count
    }

    # -----------------------------------------------------
    # FINAL RESPONSE
    # -----------------------------------------------------

    return {

        "summary": {

            "active": active,

            "acknowledged":
                acknowledged,

            "resolved":
                resolved,

            "critical":
                critical,

            "sla_breaches":
                sla_breaches,

            "average_response":
                average_response,

            "health_score":
                health,

            "temperature_alerts":
                temperature_alerts,

            "inventory_alerts":
                inventory_count
        },

        "incident_feed":
            incident_feed,

        "timeline":
            timeline,

        "clusters":
            clusters,

        "impact":
            impact,

        "heatmap":
            heatmap,

        "recommendations":
            recommendations,

        "charts": {

            "trend":
                trend,

            "status":
                status_distribution,

            "types":
                type_distribution
        }
    }

# =========================================================
# BUILD MEDICINE RESPONSE
# =========================================================

def build_medicine_response(
    conn,
    medicine
):

    batches = conn.execute(
        """
        SELECT
            id,
            batch_code,
            quantity,
            expiry_date,
            created_at
        FROM medicine_batches
        WHERE medicine_id = ?
        AND quantity > 0
        ORDER BY expiry_date ASC, id ASC
        """,
        (medicine["id"],)
    ).fetchall()

    stock = get_total_stock(
        conn,
        medicine["id"]
    )

    return {
        "id": medicine["id"],
        "name": medicine["name"],
        "min_stock": medicine["min_stock"],
        "stock": stock,
        "batches": [
            dict(row)
            for row in batches
        ]
    }


# =========================================================
# FEFO ANALYSIS ENGINE
# =========================================================

def get_fefo_analysis(conn):

    today = datetime.now().date()

    rows = conn.execute(
        """
        SELECT
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

    near_expiry_batches = []

    total_near_expiry_units = 0

    for row in rows:

        expiry_date = datetime.strptime(
            row["expiry_date"],
            "%Y-%m-%d"
        ).date()

        days_remaining = (
            expiry_date - today
        ).days

        # -------------------------------------------------
        # NEAR EXPIRY WINDOW
        # -------------------------------------------------

        if days_remaining <= 30:

            total_near_expiry_units += row["quantity"]

            near_expiry_batches.append({

                "medicine":
                    row["name"],

                "batch_code":
                    row["batch_code"],

                "quantity":
                    row["quantity"],

                "expiry_date":
                    row["expiry_date"],

                "days_remaining":
                    days_remaining
            })

    return {

        "near_expiry_batches":
            near_expiry_batches,

        "near_expiry_batch_count":
            len(near_expiry_batches),

        "total_near_expiry_units":
            total_near_expiry_units
    }


# =========================================================
# INVENTORY HEALTH CLASSIFIER
# =========================================================

def classify_inventory_health(
    stock,
    min_stock
):

    if stock <= min_stock:

        return "critical"

    elif stock <= (min_stock * 1.5):

        return "warning"

    elif stock >= (min_stock * 5):

        return "overstocked"

    return "healthy"


# =========================================================
# INVENTORY ANALYTICS ENGINE
# =========================================================

def get_inventory_analytics(conn):

    medicines = conn.execute(
        """
        SELECT *
        FROM medicines
        ORDER BY name ASC
        """
    ).fetchall()

    total_medicines = len(medicines)

    total_inventory_units = 0

    low_stock_count = 0

    overstock_count = 0

    critical_risk_count = 0

    inventory_health_score = 100

    highest_stock = None

    lowest_stock = None

    health_breakdown = {

        "healthy": 0,

        "warning": 0,

        "critical": 0,

        "overstocked": 0
    }

    for medicine in medicines:

        stock = get_total_stock(
            conn,
            medicine["id"]
        )

        total_inventory_units += stock

        health_status = classify_inventory_health(
            stock,
            medicine["min_stock"]
        )

        health_breakdown[
            health_status
        ] += 1

        if health_status == "critical":

            low_stock_count += 1

            critical_risk_count += 1

            inventory_health_score -= 15

        elif health_status == "warning":

            inventory_health_score -= 5

        elif health_status == "overstocked":

            overstock_count += 1

            inventory_health_score -= 3

        medicine_data = {

            "name":
                medicine["name"],

            "stock":
                stock
        }

        if (
            highest_stock is None
            or stock > highest_stock["stock"]
        ):

            highest_stock = medicine_data

        if (
            lowest_stock is None
            or stock < lowest_stock["stock"]
        ):

            lowest_stock = medicine_data

    inventory_health_score = max(
        inventory_health_score,
        0
    )

    return {

        "total_medicines":
            total_medicines,

        "total_inventory_units":
            total_inventory_units,

        "low_stock_count":
            low_stock_count,

        "overstock_count":
            overstock_count,

        "critical_risk_count":
            critical_risk_count,

        "inventory_health_score":
            inventory_health_score,

        "highest_stock_medicine":
            (
                highest_stock["name"]
                if highest_stock
                else "--"
            ),

        "lowest_stock_medicine":
            (
                lowest_stock["name"]
                if lowest_stock
                else "--"
            ),

        "health_breakdown":
            health_breakdown
    }


# =========================================================
# INVENTORY DISTRIBUTION ENGINE
# =========================================================

def get_inventory_distribution(conn):

    medicines = conn.execute(
        """
        SELECT *
        FROM medicines
        ORDER BY name ASC
        """
    ).fetchall()

    distribution = []

    for medicine in medicines:

        stock = get_total_stock(
            conn,
            medicine["id"]
        )

        health_status = classify_inventory_health(
            stock,
            medicine["min_stock"]
        )

        color = "#4ade80"

        if health_status == "critical":

            color = "#ef4444"

        elif health_status == "warning":

            color = "#facc15"

        elif health_status == "overstocked":

            color = "#3b82f6"

        distribution.append({

            "medicine":
                medicine["name"],

            "stock":
                stock,

            "health_status":
                health_status,

            "color":
                color
        })

    return distribution


# =========================================================
# INVENTORY ALERT CENTER
# =========================================================

def get_inventory_alert_center(conn):

    medicines = conn.execute(
        """
        SELECT *
        FROM medicines
        ORDER BY name ASC
        """
    ).fetchall()

    alerts = []

    for medicine in medicines:

        stock = get_total_stock(
            conn,
            medicine["id"]
        )

        health_status = classify_inventory_health(
            stock,
            medicine["min_stock"]
        )

        if health_status == "critical":

            alerts.append({

                "severity":
                    "critical",

                "title":
                    "Critical Stock Alert",

                "message":
                    (
                        f"{medicine['name']} "
                        f"is critically low "
                        f"({stock} remaining)"
                    )
            })

        elif health_status == "warning":

            alerts.append({

                "severity":
                    "warning",

                "title":
                    "Low Stock Warning",

                "message":
                    (
                        f"{medicine['name']} "
                        f"is approaching "
                        f"minimum threshold"
                    )
            })

        elif health_status == "overstocked":

            alerts.append({

                "severity":
                    "info",

                "title":
                    "Overstock Detected",

                "message":
                    (
                        f"{medicine['name']} "
                        f"may be overstocked"
                    )
            })

    return alerts

# =========================================================
# =========================================================
# SALES ANALYTICS HELPERS
# =========================================================
# =========================================================


# =========================================================
# GET MEDICINE SALES MAP
#
# PURPOSE:
# Returns medicine-wise sales aggregation.
#
# USED FOR:
# - top selling medicines
# - movement analysis
# - risk calculations
# - sales intelligence
# =========================================================

def get_medicine_sales_map(conn):

    rows = conn.execute(
        """
        SELECT
            medicines.name,
            COALESCE(
                SUM(sales.quantity),
                0
            ) AS total_units

        FROM sales

        JOIN medicines
        ON sales.medicine_id = medicines.id

        GROUP BY medicines.name

        ORDER BY total_units DESC
        """
    ).fetchall()

    medicine_map = {}

    for row in rows:

        medicine_map[row["name"]] = (
            row["total_units"]
        )

    return medicine_map


# =========================================================
# GET DAILY SALES MAP
#
# PURPOSE:
# Creates date-wise sales intelligence.
#
# USED FOR:
# - sales charts
# - sales trends
# - peak day analysis
# =========================================================

def get_daily_sales_map(conn):

    rows = conn.execute(
        """
        SELECT
            DATE(timestamp) AS sale_day,
            COALESCE(
                SUM(quantity),
                0
            ) AS total_units

        FROM sales

        GROUP BY sale_day

        ORDER BY sale_day ASC
        """
    ).fetchall()

    daily_map = {}

    for row in rows:

        daily_map[row["sale_day"]] = (
            row["total_units"]
        )

    return daily_map


# =========================================================
# CALCULATE INVENTORY MOVEMENT
#
# PURPOSE:
# Calculate operational movement intelligence.
#
# LOGIC:
# Higher sold units + lower current stock
# produces a higher movement score.
# =========================================================

def calculate_inventory_movement(conn):

    medicines = conn.execute(
        """
        SELECT *
        FROM medicines
        ORDER BY name ASC
        """
    ).fetchall()

    movement_data = []

    medicine_sales = get_medicine_sales_map(
        conn
    )

    for medicine in medicines:

        medicine_name = medicine["name"]

        medicine_id = medicine["id"]

        current_stock = get_total_stock(
            conn,
            medicine_id
        )

        total_sold = medicine_sales.get(
            medicine_name,
            0
        )

        # =================================================
        # MOVEMENT SCORE
        # =================================================

        if current_stock <= 0:

            risk_score = total_sold

        else:

            risk_score = round(
                total_sold / current_stock,
                2
            )

        movement_data.append({

            "medicine":
            medicine_name,

            "current_stock":
            current_stock,

            "units_sold":
            total_sold,

            "movement_score":
            risk_score
        })

    movement_data.sort(
        key=lambda x: x["movement_score"],
        reverse=True
    )

    return movement_data


# =========================================================
# DEMAND PREDICTION ENGINE
#
# PURPOSE:
# Centralize the demand-forecast business rules that were
# previously calculated inside the Demand Prediction page.
#
# RULES PRESERVED FROM THE EXISTING FRONTEND:
# - Average daily demand = total sold / 7
# - Zero-sales medicines use a 0.1 daily baseline
# - Predicted demand = ceil(average daily demand * 7)
# - Risk is based on estimated days of stock remaining
# - Confidence depends on the number of historical sales records
# =========================================================

def get_demand_predictions(conn):

    medicines = conn.execute(
        """
        SELECT
            id,
            name,
            min_stock
        FROM medicines
        ORDER BY name ASC
        """
    ).fetchall()

    sales_rows = conn.execute(
        """
        SELECT
            medicines.id AS medicine_id,
            medicines.name AS medicine_name,
            sales.quantity
        FROM sales
        JOIN medicines
        ON sales.medicine_id = medicines.id
        """
    ).fetchall()

    sales_map = {}
    sales_count_map = {}

    for row in sales_rows:

        medicine_name = row["medicine_name"]

        sales_map[medicine_name] = (
            sales_map.get(medicine_name, 0)
            + row["quantity"]
        )

        sales_count_map[medicine_name] = (
            sales_count_map.get(medicine_name, 0)
            + 1
        )

    predictions = []

    total_predicted = 0
    total_confidence = 0
    high_risk_count = 0
    critical_count = 0
    warning_count = 0
    stable_count = 0

    peak_item = "--"
    peak_value = 0

    for medicine in medicines:

        medicine_name = medicine["name"]

        sold = sales_map.get(
            medicine_name,
            0
        )

        sale_count = sales_count_map.get(
            medicine_name,
            0
        )

        # -------------------------------------------------
        # EXISTING DEMAND RULE
        # -------------------------------------------------

        avg_daily = (
            sold / 7
            if sold > 0
            else 0.1
        )

        predicted = math.ceil(
            avg_daily * 7
        )

        current_stock = get_total_stock(
            conn,
            medicine["id"]
        )

        days_left = (
            current_stock / avg_daily
        )

        # -------------------------------------------------
        # RISK CLASSIFICATION
        # -------------------------------------------------

        if days_left <= 3:

            risk = "High"
            risk_class = "high"
            critical_count += 1
            high_risk_count += 1

        elif days_left <= 7:

            risk = "Medium"
            risk_class = "medium"
            warning_count += 1

        else:

            risk = "Low"
            risk_class = "low"
            stable_count += 1

        # -------------------------------------------------
        # CONFIDENCE RULE
        # -------------------------------------------------

        confidence = 40

        if sale_count >= 10:
            confidence = 95
        elif sale_count >= 5:
            confidence = 75

        total_predicted += predicted
        total_confidence += confidence

        if predicted > peak_value:

            peak_value = predicted
            peak_item = medicine_name

        predictions.append({
            "medicine": medicine_name,
            "medicine_id": medicine["id"],
            "current_stock": current_stock,
            "units_sold": sold,
            "sales_count": sale_count,
            "average_daily_demand": round(avg_daily, 2),
            "predicted_demand": predicted,
            "days_left": round(days_left, 1),
            "risk": risk,
            "risk_class": risk_class,
            "confidence": confidence
        })

    medicine_count = len(medicines)

    average_confidence = (
        round(
            total_confidence / medicine_count
        )
        if medicine_count > 0
        else 0
    )

    return {
        "summary": {
            "total_predicted_demand": total_predicted,
            "average_confidence": average_confidence,
            "high_risk_medicines": high_risk_count,
            "peak_forecast_item": peak_item,
            "critical_count": critical_count,
            "warning_count": warning_count,
            "stable_count": stable_count
        },
        "predictions": predictions,
        "chart": {
            "labels": [
                item["medicine"]
                for item in predictions
            ],
            "predicted_demand": [
                item["predicted_demand"]
                for item in predictions
            ],
            "demand_velocity": [
                item["average_daily_demand"]
                for item in predictions
            ]
        }
    }


# =========================================================
# REORDER SUGGESTION ENGINE
#
# PURPOSE:
# Centralize procurement/reorder business rules that were
# previously calculated inside the Reorder Suggestions page.
#
# RULES PRESERVED FROM THE EXISTING FRONTEND:
# - predicted = ceil((sold + movement_score + min_stock) * 1.15)
# - reorder = max(ceil(predicted * 1.3 - current_stock), 0)
# - cost = reorder quantity * 50
# - priority = reorder*2 + low-stock bonus + movement score
# - priority >= 25 => critical, >= 10 => warning
#
# Lead time was previously random in the browser. It is now a
# deterministic 3-day operational default so the API does not
# produce different procurement results on every refresh.
# =========================================================

def get_reorder_suggestions(conn):

    medicines = conn.execute(
        """
        SELECT
            id,
            name,
            min_stock
        FROM medicines
        ORDER BY name ASC
        """
    ).fetchall()

    sales_map = get_medicine_sales_map(conn)

    movement_data = calculate_inventory_movement(conn)

    movement_map = {}

    for item in movement_data:

        movement_map[item["medicine"]] = (
            item["movement_score"]
        )

    reorder_items = []

    total_units_needed = 0
    total_budget = 0
    total_priority = 0
    urgent_count = 0
    critical_risk = 0

    for medicine in medicines:

        medicine_name = medicine["name"]

        sold = sales_map.get(
            medicine_name,
            0
        )

        movement_score = movement_map.get(
            medicine_name,
            0
        )

        current_stock = get_total_stock(
            conn,
            medicine["id"]
        )

        # -------------------------------------------------
        # EXISTING SMART PREDICTION RULE
        # -------------------------------------------------

        predicted = math.ceil(
            (
                sold
                + movement_score
                + medicine["min_stock"]
            ) * 1.15
        )

        if predicted <= 0:
            predicted = 2

        # -------------------------------------------------
        # REORDER QUANTITY
        # -------------------------------------------------

        reorder = max(
            math.ceil(
                (predicted * 1.3)
                - current_stock
            ),
            0
        )

        if reorder <= 0:
            continue

        cost = reorder * 50

        priority = (
            (reorder * 2)
            + (
                20
                if current_stock <= medicine["min_stock"]
                else 0
            )
            + math.ceil(movement_score)
        )

        if priority >= 25:

            badge = "critical"
            urgent_count += 1
            critical_risk += 1

        elif priority >= 10:

            badge = "warning"

        else:

            badge = "safe"

        lead_time_days = 3

        reorder_items.append({
    "medicine": medicine_name,
    "medicine_id": medicine["id"],
    "current_stock": current_stock,
    "min_stock": medicine["min_stock"],
    "units_sold": sold,
    "movement_score": movement_score,
    "predicted_demand": predicted,
    "reorder_quantity": reorder,
    "priority": priority,
    "badge": badge,
    "lead_time_days": lead_time_days,
    "cost": cost
})

        total_units_needed += reorder
        total_budget += cost
        total_priority += priority

    average_priority = (
        round(
            total_priority / len(reorder_items)
        )
        if reorder_items
        else 0
    )

    top_reorder_medicine = (
        reorder_items[0]["medicine"]
        if reorder_items
        else ""
    )

    inventory_analytics = get_inventory_analytics(
        conn
    )

    return {
        "summary": {
            "reorder_count": len(reorder_items),
            "urgent_count": urgent_count,
            "total_units_needed": total_units_needed,
            "estimated_budget": total_budget,
            "average_priority": average_priority,
            "critical_risk": critical_risk,
            "top_reorder_medicine": top_reorder_medicine,
            "overstock_count": inventory_analytics[
                "overstock_count"
            ]
        },
        "reorders": reorder_items,
        "chart": {
            "labels": [
                item["medicine"]
                for item in reorder_items
            ],
            "priority": [
                item["priority"]
                for item in reorder_items
            ],
            "budget": [
                item["cost"]
                for item in reorder_items
            ]
        }
    }


# =========================================================
# GET SALES SUMMARY
#
# PURPOSE:
# Central sales intelligence engine.
#
# RETURNS:
# - KPI metrics
# - sales insights
# - movement intelligence
# =========================================================

def get_sales_summary(conn):

    sales_rows = conn.execute(
        """
        SELECT *
        FROM sales
        """
    ).fetchall()

    total_sales_records = len(
        sales_rows
    )

    total_units_sold = sum([
        row["quantity"]
        for row in sales_rows
    ])

    # =====================================================
    # TEMPORARY REVENUE ENGINE
    #
    # Current system does not have a medicine price field.
    # Therefore the existing monolithic logic uses ₹50
    # per unit as an estimated value.
    # =====================================================

    estimated_revenue = (
        total_units_sold * 50
    )

    medicine_map = get_medicine_sales_map(
        conn
    )

    daily_map = get_daily_sales_map(
        conn
    )

    top_selling = "--"

    slowest_selling = "--"

    peak_day = "--"

    avg_units = 0

    # =====================================================
    # MEDICINE SALES ANALYSIS
    # =====================================================

    if medicine_map:

        sorted_medicines = sorted(
            medicine_map.items(),
            key=lambda x: x[1],
            reverse=True
        )

        top_selling = (
            sorted_medicines[0][0]
        )

        slowest_selling = (
            sorted_medicines[-1][0]
        )

    # =====================================================
    # PEAK SALES DAY
    # =====================================================

    if daily_map:

        peak_day = max(
            daily_map,
            key=daily_map.get
        )

    # =====================================================
    # AVERAGE UNITS PER SALE
    # =====================================================

    if total_sales_records > 0:

        avg_units = round(
            total_units_sold /
            total_sales_records,
            1
        )

    # =====================================================
    # MOVEMENT ANALYSIS
    # =====================================================

    movement_data = (
        calculate_inventory_movement(
            conn
        )
    )

    highest_risk = "--"

    if movement_data:

        highest_risk = (
            movement_data[0]["medicine"]
        )

    return {

        "total_sales_records":
        total_sales_records,

        "total_units_sold":
        total_units_sold,

        "estimated_revenue":
        estimated_revenue,

        "top_selling_medicine":
        top_selling,

        "peak_sales_day":
        peak_day,

        "average_units_per_sale":
        avg_units,

        "fastest_moving":
        top_selling,

        "slowest_moving":
        slowest_selling,

        "highest_consumption_risk":
        highest_risk
    }
