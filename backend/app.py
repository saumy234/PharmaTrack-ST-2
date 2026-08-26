from flask import Flask, request, jsonify # pyright: ignore[reportMissingImports]
from flask_cors import CORS  # pyright: ignore[reportMissingModuleSource]
from .database import check_database_schema, DB_PATH, get_connection
from .api.medicines_api import bp as medicines_bp
from .api.inventory_api import bp as inventory_bp
from .api.sales_api import bp as sales_bp
from .api.cold_chain_api import bp as cold_chain_bp

app = Flask(__name__)
CORS(app)

app.register_blueprint(medicines_bp)
app.register_blueprint(inventory_bp)
app.register_blueprint(sales_bp)
app.register_blueprint(cold_chain_bp)

@app.get("/")
def home():
    return "Backend Running!"

@app.get("/health")
def health():
    try:
        check_database_schema()
        conn = get_connection()
        counts = {
            "medicines": conn.execute("SELECT COUNT(*) AS count FROM medicines").fetchone()["count"],
            "active_batches": conn.execute("SELECT COUNT(*) AS count FROM medicine_batches WHERE quantity > 0").fetchone()["count"],
            "temperature_readings": conn.execute("SELECT COUNT(*) AS count FROM temperature_logs").fetchone()["count"],
            "active_alerts": conn.execute("SELECT COUNT(*) AS count FROM alerts WHERE status != 'resolved'").fetchone()["count"],
        }
        conn.close()
        return jsonify({"status":"healthy","database":"connected","tables":"valid","counts":counts})
    except Exception as error:
        return jsonify({"status":"unhealthy","database":"not ready","error":str(error)}), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error":"API endpoint not found"}), 404

@app.errorhandler(405)
def method_not_allowed(error):
    return jsonify({"error":"HTTP method not allowed for this endpoint"}), 405

@app.errorhandler(500)
def internal_server_error(error):
    return jsonify({"error":"Internal server error"}), 500

def startup_check():
    print("\n" + "=" * 60)
    print("BACKEND")
    print("=" * 60)
    print(f"Database: {DB_PATH}")
    check_database_schema()
    print("Database schema check: PASSED")
    print("Required API surface: READY")
    print("Server: http://127.0.0.1:5001")
    print("=" * 60 + "\n")

if __name__ == "__main__":
    startup_check()
    app.run(host="0.0.0.0", port=5001, debug=True)
