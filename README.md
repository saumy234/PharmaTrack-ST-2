PharmaTrack

Smart Pharmaceutical Inventory and Cold Chain Monitoring System

PharmaTrack is a web-based system for managing pharmaceutical inventory, medicine batches, sales, expiry, cold-chain monitoring, and operational alerts. It combines a frontend application, modular Flask REST APIs, a SQLite database, and an ESP32-based temperature monitoring unit.

Features

Area

Functionality

Medicine Management

Onboarding, batch management, restocking, medicine details

Inventory

Stock monitoring, analytics, FEFO, movement analysis

Sales

Sales recording, history, trends, analytics

Expiry

Expired and near-expiry batch tracking

Demand & Reorder

Demand prediction and reorder suggestions

Cold Chain

ESP32 temperature and humidity monitoring

Alerts

Temperature/inventory alerts, acknowledgement, resolution

Assistant

Operational inventory queries

Tech Stack

Layer

Technology

Frontend

HTML5, CSS3, JavaScript, Bootstrap, Chart.js

Backend

Python, Flask, Flask Blueprints, REST APIs

Database

SQLite

IoT

ESP32 / NodeMCU, DS18B20

Communication

Wi-Fi, HTTP/JSON

Testing

Postman

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

Medicine onboarding, details, restocking and batch operations

inventory_api.py

Stock analytics, FEFO, expiry, demand and reorder

sales_api.py

Sales transactions, history and analytics

cold_chain_api.py

Temperature monitoring and alert operations

assistant_api.py

Assistant queries

helpers.py

Shared business logic and calculations

database.py

SQLite connection management

API Reference

Medicines

Method

Endpoint

Purpose

GET

/medicines

Fetch medicines

POST

/medicines

Add medicine

GET

/medicine/<id>

Medicine details

PUT

/medicines/restock/<id>

Restock medicine

DELETE

/medicines/<id>

Delete medicine

DELETE

/batches/<batch_id>

Delete batch

Inventory

Method

Endpoint

Purpose

GET

/inventory/analytics

Inventory analytics

GET

/inventory/distribution

Stock distribution

GET

/inventory/alerts

Inventory alerts

GET

/inventory/fefo-risk

FEFO risk analysis

GET

/inventory/movement

Inventory movement

GET

/expiry-batches

Expiry tracking

GET

/inventory/demand-prediction

Demand analysis

GET

/inventory/reorder-suggestions

Reorder suggestions

Sales

Method

Endpoint

Purpose

POST

/sales

Record sale

GET

/sales

Sales history

GET

/sales/analytics

Sales analytics

GET

/sales/trends

Sales trends

GET

/sales/activity

Sales activity

GET

/sales/fefo-analysis

FEFO sales analysis

Cold Chain & Alerts

Method

Endpoint

Purpose

GET

/temperature

Fetch temperature data

POST

/temperature

Add temperature reading

GET

/alerts

Fetch alerts

GET

/alerts/command-center

Alert command center

PUT

/acknowledge_alert/<alert_id>

Acknowledge alert

PUT

/resolve_alert/<alert_id>

Resolve alert

Assistant & System

Method

Endpoint

Purpose

POST

/ai-assistant

Assistant query

GET

/

Backend status

GET

/health

Health check

IoT Integration

The cold-chain unit uses an ESP32 with a DS18B20 temperature sensor.

Parameter

Value

Temperature sensor

DS18B20

Sensor pin

GPIO 19

Alert LED

GPIO 18

Temperature threshold

28°C

Reading interval

5 seconds

Device ID

ESP32_ROOM_1

How it works

DS18B20 measures the temperature.

ESP32 checks the reading against the 28°C threshold.

ESP32 sends the reading to POST /temperature using Wi-Fi and HTTP/JSON.

Flask stores the reading in temperature_logs.

If the temperature is above 28°C, the backend creates a temperature alert.

The alert appears on the PharmaTrack cold-chain/alert pages.

When the temperature returns to 28°C or below, active/acknowledged temperature alerts are resolved.

Example payload:

{
  "device_id": "ESP32_ROOM_1",
  "temperature": 30,
  "humidity": 55,
  "sensor_status": "ACTIVE"
}

Database

PharmaTrack uses one SQLite database:

database/database.db

Table

Purpose

medicines

Medicine master data

medicine_batches

Batch, quantity and expiry data

sales

Sales transactions

temperature_logs

IoT temperature readings

alerts

System alerts and status

predictions

Demand prediction records

Database setup:

database/database_setup.py

Database connection is managed through:

backend/database.py

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

Run the Project

From the project root:

pip install -r requirements.txt
python -m backend.app

Backend URL:

http://127.0.0.1:5001

Health check:

http://127.0.0.1:5001/health

For ESP32 testing, set the backend URL in the IoT code to the laptop's local IP address:

const char* serverUrl = "http://<HOTSPOT IP>:5001/temperature";

The ESP32 and laptop must be connected to the same network.

Project Status

Completed

PharmaTrack integrates medicine and batch management, inventory and sales operations, FEFO and expiry tracking, demand and reorder analysis, ESP32-based cold-chain monitoring, alert management, medicine details, and the operational Assistant through a modular Flask backend and a centralized SQLite database.
