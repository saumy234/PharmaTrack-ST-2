import sqlite3
import os
from datetime import datetime, timedelta
import random

print("Starting database setup...")


# =========================================================
# DATABASE PATH
# =========================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database.db")

print(" Database path:", DB_PATH)


# =========================================================
# CONNECT DATABASE
# =========================================================
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Enable Foreign Key Support
cursor.execute("PRAGMA foreign_keys = ON")

print(" Connected to database")


# =========================================================
# CREATE TABLES
# =========================================================

# =========================================================
# MEDICINES TABLE
#
# IMPORTANT:
# This table now stores ONLY medicine master data.
#
# We NO LONGER store:
# - stock
# - expiry_date
#
# Because:
# expiry belongs to batches
# not medicines.
# =========================================================
cursor.execute("""
CREATE TABLE IF NOT EXISTS medicines (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    name TEXT NOT NULL UNIQUE,

    min_stock INTEGER NOT NULL
)
""")


# =========================================================
# MEDICINE BATCHES TABLE
#
# THIS IS THE NEW CORE INVENTORY TABLE
#
# Every restock creates a NEW batch.
#
# Example:
#
# Paracetamol
# ├── Batch A → 30 → Expiry 2026
# └── Batch B → 100 → Expiry 2027
#
# This solves your expiry overwrite problem.
# =========================================================
cursor.execute("""
CREATE TABLE IF NOT EXISTS medicine_batches (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    medicine_id INTEGER NOT NULL,

    batch_code TEXT,

    quantity INTEGER NOT NULL,

    expiry_date TEXT,

    created_at TEXT,

    FOREIGN KEY (medicine_id)
    REFERENCES medicines(id)
    ON DELETE CASCADE
)
""")


# =========================================================
# SALES TABLE
# =========================================================
cursor.execute("""
CREATE TABLE IF NOT EXISTS sales (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    medicine_id INTEGER,

    quantity INTEGER,

    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (medicine_id)
    REFERENCES medicines(id)
)
""")


# =========================================================
# TEMPERATURE LOGS TABLE
# =========================================================
cursor.execute("""
CREATE TABLE IF NOT EXISTS temperature_logs (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    device_id TEXT,

    temperature REAL,

    humidity REAL,

    timestamp TEXT
)
""")


# =========================================================
# ALERTS TABLE
# =========================================================
cursor.execute("""
CREATE TABLE IF NOT EXISTS alerts (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    type TEXT,

    message TEXT,

    timestamp TEXT,

    status TEXT DEFAULT 'active',

    acknowledged_at TEXT,

    resolved_at TEXT
)
""")


# =========================================================
# PREDICTIONS TABLE
# =========================================================
cursor.execute("""
CREATE TABLE IF NOT EXISTS predictions (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    medicine_id INTEGER,

    predicted_demand REAL,

    risk_level TEXT,

    FOREIGN KEY (medicine_id)
    REFERENCES medicines(id)
)
""")


print(" Tables created / verified")


# =========================================================
# CHECK EXISTING MEDICINES
# =========================================================
cursor.execute("SELECT COUNT(*) FROM medicines")

count = cursor.fetchone()[0]

print(" Existing medicine rows:", count)


# =========================================================
# INSERT DUMMY DATA IF DATABASE EMPTY
# =========================================================
if count == 0:

    print(" Inserting dummy seed data...")

    # =====================================================
    # MEDICINE MASTER DATA
    # =====================================================
    medicines = [
        ("Paracetamol", 20),
        ("Insulin", 5),
        ("COVID Vaccine", 3),
        ("Antibiotic", 10),
        ("Painkiller", 10)
    ]

    normalized_medicines = [
        (name.strip().title(), min_stock)
        for name, min_stock in medicines
    ]

    cursor.executemany("""
    INSERT INTO medicines
    (name, min_stock)
    VALUES (?, ?)
    """, normalized_medicines)

    conn.commit()

    # =====================================================
    # FETCH MEDICINE IDS
    # =====================================================
    cursor.execute("SELECT id, name FROM medicines")

    medicine_rows = cursor.fetchall()

    medicine_map = {
        row[1]: row[0]
        for row in medicine_rows
    }

    # =====================================================
    # INSERT BATCHES
    #
    # THIS IS NOW THE REAL INVENTORY
    # =====================================================
    batches = [

        # -------------------------------------------------
        # PARACETAMOL
        # MULTIPLE BATCHES EXAMPLE
        # -------------------------------------------------
        (
            medicine_map["Paracetamol"],
            "PCM001",
            20,
            "2026-08-01"
        ),

        (
            medicine_map["Paracetamol"],
            "PCM002",
            30,
            "2027-01-15"
        ),

        # -------------------------------------------------
        # INSULIN
        # -------------------------------------------------
        (
            medicine_map["Insulin"],
            "INS001",
            10,
            "2025-06-30"
        ),

        # -------------------------------------------------
        # COVID VACCINE
        # -------------------------------------------------
        (
            medicine_map["Covid Vaccine"],
            "VAC001",
            5,
            "2025-04-15"
        ),

        # -------------------------------------------------
        # ANTIBIOTIC
        # -------------------------------------------------
        (
            medicine_map["Antibiotic"],
            "ANT001",
            30,
            "2026-01-01"
        ),

        # -------------------------------------------------
        # PAINKILLER
        # -------------------------------------------------
        (
            medicine_map["Painkiller"],
            "PNK001",
            10,
            "2026-02-18"
        )
    ]

    for batch in batches:

        cursor.execute("""
        INSERT INTO medicine_batches
        (
            medicine_id,
            batch_code,
            quantity,
            expiry_date,
            created_at
        )
        VALUES (?, ?, ?, ?, ?)
        """, (
            batch[0],
            batch[1],
            batch[2],
            batch[3],
            datetime.now().isoformat()
        ))

    # =====================================================
    # TEMPERATURE LOGS SEED
    # =====================================================
    for i in range(10):

        temp = round(random.uniform(4.0, 10.0), 2)

        humidity = random.randint(40, 70)

        timestamp = (
            datetime.now() -
            timedelta(minutes=i * 5)
        ).isoformat()

        cursor.execute("""
        INSERT INTO temperature_logs
        (
            device_id,
            temperature,
            humidity,
            timestamp
        )
        VALUES (?, ?, ?, ?)
        """, (
            "esp32_001",
            temp,
            humidity,
            timestamp
        ))

    # =====================================================
    # DEFAULT ALERT
    # =====================================================
    cursor.execute("""
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
    """, (
        "Temperature",
        "Temperature exceeded safe limit!",
        datetime.now().isoformat(),
        "active",
        None,
        None
    ))

    # =====================================================
    # DUMMY PREDICTION
    # =====================================================
    cursor.execute("""
    INSERT INTO predictions
    (
        medicine_id,
        predicted_demand,
        risk_level
    )
    VALUES (?, ?, ?)
    """, (
        1,
        60,
        "HIGH"
    ))

    print(" Dummy data inserted")

else:

    print(" Existing data found — skipping seed insert")


# =========================================================
# VERIFY MEDICINES
# =========================================================
print("\n Medicines Data")

cursor.execute("""
SELECT *
FROM medicines
""")

medicine_rows = cursor.fetchall()

for row in medicine_rows:
    print(row)


# =========================================================
# VERIFY BATCHES
# =========================================================
print("\n Medicine Batches")

cursor.execute("""
SELECT
    medicine_batches.id,
    medicines.name,
    medicine_batches.batch_code,
    medicine_batches.quantity,
    medicine_batches.expiry_date

FROM medicine_batches

JOIN medicines
ON medicine_batches.medicine_id = medicines.id
""")

batch_rows = cursor.fetchall()

for row in batch_rows:
    print(row)


# =========================================================
# SAVE + CLOSE
# =========================================================
conn.commit()
conn.close()

print(" DATABASE SETUP COMPLETE")