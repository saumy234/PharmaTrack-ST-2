PharmaTrack

Smart Pharmaceutical Inventory and Cold Chain Monitoring System

PharmaTrack is a web-based system for managing pharmaceutical inventory, medicine batches, sales, expiry, cold-chain conditions, and operational alerts. The project uses a modular Flask backend, a single SQLite database, frontend pages connected through REST APIs, and an ESP32-based temperature monitoring unit.

Features

Medicine onboarding and batch management

FEFO (First Expiry, First Out) inventory management

Stock monitoring and inventory analytics

Sales recording, history, and analytics

Expiry and near-expiry batch tracking

Demand prediction and consumption analysis

Reorder suggestions and stock priorities

ESP32-based temperature monitoring

Automatic high-temperature alerts

Inventory and temperature alerts

Alert acknowledgement, resolution, and command center

Medicine details and batch-level intelligence

Operational Assistant for inventory queries

Tech Stack

Frontend: HTML5, CSS3, JavaScript, Bootstrap, Chart.js

Backend: Python, Flask, Flask Blueprints, REST APIs

Database: SQLite

IoT: ESP32 / NodeMCU, DS18B20 temperature sensor, OneWire, DallasTemperature

Communication: Wi-Fi + HTTP/JSON

Testing: Postman

Project Structure

PharmaTrack/
│
├── backend/
│   ├── app.py
│   ├── database.py
│   ├── helpers.py
│   └── api/
│       ├── medicines_api.py
│       ├── inventory_api.py
│       ├── sales_api.py
│       ├── cold_chain_api.py
│       └── assistant_api.py
│
├── database/
│   ├── database.db
│   └── database_setup.py
│
├── frontend/
│   └── HTML / CSS / JS pages
│
├── iot/
│   └── ESP32 temperature monitoring code
│
├── requirements.txt
└── README.md

Backend Modules

Module

Responsibility

medicines_api.py

Medicine onboarding, details, restocking, batch operations

inventory_api.py

Stock analytics, FEFO, expiry, demand, reorder

sales_api.py

Sales transactions, history, trends, analytics

cold_chain_api.py

Temperature monitoring and alert operations

assistant_api.py

Operational Assistant queries

helpers.py

Shared business logic and calculations

database.py

SQLite connection management

Main API Endpoints

Medicines

GET    /medicines
POST   /medicines
GET    /medicine/<id>
PUT    /medicines/restock/<id>
DELETE /medicines/<id>
DELETE /batches/<batch_id>

Inventory

GET /inventory/analytics
GET /inventory/distribution
GET /inventory/alerts
GET /inventory/fefo-risk
GET /inventory/movement
GET /expiry-batches
GET /inventory/demand-prediction
GET /inventory/reorder-suggestions

Sales

POST /sales
GET  /sales
GET  /sales/analytics
GET  /sales/trends
GET  /sales/activity
GET  /sales/fefo-analysis

Cold Chain & Alerts

GET /temperature
POST /temperature
GET /alerts
GET /alerts/command-center
PUT /acknowledge_alert/<alert_id>
PUT /resolve_alert/<alert_id>

Assistant & System

POST /ai-assistant
GET  /
GET  /health

IoT Integration

The cold-chain monitoring unit uses an ESP32 connected to a DS18B20 temperature sensor.

Working

DS18B20
   │
   │ Temperature Reading
   ▼
ESP32
   │
   │ Wi-Fi
   ▼
HTTP POST /temperature
   │
   ▼
Flask Backend
   │
   ├── Store reading
   ├── Check threshold
   └── Create / resolve alert
   │
   ▼
PharmaTrack Website
   │
   ▼
Cold Chain & Alert Dashboard

Temperature Monitoring

The IoT code uses:

Sensor Pin : GPIO 19
LED Pin    : GPIO 18
Threshold  : 28°C

The ESP32 reads the temperature every 5 seconds and sends JSON data to the backend.

Example payload:

{
  "device_id": "ESP32_ROOM_1",
  "temperature": 30,
  "humidity": 55,
  "sensor_status": "ACTIVE"
}

Alert Flow

When the sensor reports a temperature above 28°C:

The ESP32 turns its LED on.

The ESP32 sends the reading to POST /temperature.

The backend stores the temperature reading.

The backend creates a temperature alert.

The alert appears on the PharmaTrack website.

When the temperature returns to 28°C or below:

The ESP32 turns the LED off.

The new reading is sent to the backend.

Active/acknowledged temperature alerts are resolved by the backend.

The alert status is updated on the website.

Database

PharmaTrack uses one SQLite database:

database/database.db

Main tables:

medicines
medicine_batches
sales
temperature_logs
alerts
predictions

database/database_setup.py is used for database setup and seed data.

Architecture

Frontend
   │
   ▼
Flask REST APIs
   │
   ├── Medicines API
   ├── Inventory API
   ├── Sales API
   ├── Cold Chain API
   └── Assistant API
   │
   ▼
Shared Business Logic
(helpers.py)
   │
   ├───────────────┐
   ▼               ▼
SQLite          IoT Data
Database        (ESP32)
   ▲               │
   └────── HTTP ───┘

Frontend Sections

Smart Medicine Onboarding

Inventory Management

Medicine Operations Center

Cold Chain Monitoring

Stock Report

Sales Intelligence

Expiry Tracking

Demand Prediction

Reorder Suggestions

Alert Command Center

Medicine Details

Assistant

Running the Project

From the project root:

pip install -r requirements.txt
python -m backend.app

Backend:

http://127.0.0.1:5001

Health check:

http://127.0.0.1:5001/health

For ESP32 testing, the serverUrl in the IoT code should point to the laptop's local IP address on the same network:

const char* serverUrl = "http://<LAPTOP-IP>:5001/temperature";

Project Status

Completed

The PharmaTrack system includes medicine, batch, inventory, sales, expiry, FEFO, demand, reorder, IoT cold-chain monitoring, alerts, medicine-details, and Assistant functionality with a modular Flask backend and centralized SQLite database.
