# PharmaTrack

## Smart Pharmaceutical Inventory and Cold Chain Monitoring System

PharmaTrack is a web-based pharmaceutical management system that combines inventory management, batch tracking, sales analytics, expiry monitoring, demand analysis, reorder support, cold-chain monitoring, and operational alerts in a single platform.

The system integrates a web-based frontend, modular Flask REST APIs, a centralized SQLite database, and an ESP32-based temperature monitoring unit.

---

## Key Features

| Module              | Functionality                                                         |
| ------------------- | --------------------------------------------------------------------- |
| Medicine Management | Medicine onboarding, batch creation, restocking, and medicine details |
| Inventory           | Stock monitoring, FEFO, movement analysis, and inventory analytics    |
| Sales               | Sales recording, history, trends, and analytics                       |
| Expiry              | Expired and near-expiry batch tracking                                |
| Demand and Reorder  | Demand analysis and reorder suggestions                               |
| Cold Chain          | ESP32-based temperature and humidity monitoring                       |
| Alerts              | Inventory and temperature alerts, acknowledgement, and resolution     |
| Assistant           | Operational inventory queries                                         |

---

## Technology Stack

| Layer         | Technology                                   |
| ------------- | -------------------------------------------- |
| Frontend      | HTML5, CSS3, JavaScript, Bootstrap, Chart.js |
| Backend       | Python, Flask, Flask Blueprints, REST APIs   |
| Database      | SQLite                                       |
| IoT           | ESP32 / NodeMCU, DS18B20                     |
| Communication | Wi-Fi, HTTP/JSON                             |
| Testing       | Postman                                      |

---

## Backend Modules

| Module              | Responsibility                                                          |
| ------------------- | ----------------------------------------------------------------------- |
| `medicines_api.py`  | Medicine onboarding, medicine details, restocking, and batch operations |
| `inventory_api.py`  | Stock, FEFO, expiry, demand, reorder, and inventory analytics           |
| `sales_api.py`      | Sales transactions, history, trends, and analytics                      |
| `cold_chain_api.py` | Temperature monitoring and alert operations                             |
| `assistant_api.py`  | Operational Assistant queries                                           |
| `helpers.py`        | Shared business logic and calculations                                  |
| `database.py`       | SQLite connection management                                            |

---

# API Reference

## Medicine APIs

| Method   | Endpoint                  | Purpose               |
| -------- | ------------------------- | --------------------- |
| `GET`    | `/medicines`              | Fetch medicines       |
| `POST`   | `/medicines`              | Add medicine          |
| `GET`    | `/medicine/<id>`          | View medicine details |
| `PUT`    | `/medicines/restock/<id>` | Restock medicine      |
| `DELETE` | `/medicines/<id>`         | Delete medicine       |
| `DELETE` | `/batches/<batch_id>`     | Delete batch          |

---

## Inventory APIs

| Method | Endpoint                         | Purpose             |
| ------ | -------------------------------- | ------------------- |
| `GET`  | `/inventory/analytics`           | Inventory analytics |
| `GET`  | `/inventory/distribution`        | Stock distribution  |
| `GET`  | `/inventory/alerts`              | Inventory alerts    |
| `GET`  | `/inventory/fefo-risk`           | FEFO risk analysis  |
| `GET`  | `/inventory/movement`            | Inventory movement  |
| `GET`  | `/expiry-batches`                | Expiry tracking     |
| `GET`  | `/inventory/demand-prediction`   | Demand analysis     |
| `GET`  | `/inventory/reorder-suggestions` | Reorder suggestions |

---

## Sales APIs

| Method | Endpoint               | Purpose             |
| ------ | ---------------------- | ------------------- |
| `POST` | `/sales`               | Record sale         |
| `GET`  | `/sales`               | Sales history       |
| `GET`  | `/sales/analytics`     | Sales analytics     |
| `GET`  | `/sales/trends`        | Sales trends        |
| `GET`  | `/sales/activity`      | Sales activity      |
| `GET`  | `/sales/fefo-analysis` | FEFO sales analysis |

---

## Cold Chain and Alert APIs

| Method | Endpoint                        | Purpose                    |
| ------ | ------------------------------- | -------------------------- |
| `GET`  | `/temperature`                  | Fetch temperature readings |
| `POST` | `/temperature`                  | Add temperature reading    |
| `GET`  | `/alerts`                       | Fetch alerts               |
| `GET`  | `/alerts/command-center`        | Alert command center       |
| `PUT`  | `/acknowledge_alert/<alert_id>` | Acknowledge alert          |
| `PUT`  | `/resolve_alert/<alert_id>`     | Resolve alert              |

---

## Assistant and System APIs

| Method | Endpoint        | Purpose         |
| ------ | --------------- | --------------- |
| `POST` | `/ai-assistant` | Assistant query |
| `GET`  | `/`             | Backend status  |
| `GET`  | `/health`       | Health check    |

---

# IoT Integration

The cold-chain monitoring module uses an ESP32/NodeMCU with a DS18B20 temperature sensor.

| Parameter             | Value          |
| --------------------- | -------------- |
| Temperature Sensor    | DS18B20        |
| Sensor Pin            | GPIO 19        |
| Alert LED             | GPIO 18        |
| Temperature Threshold | 28°C           |
| Reading Interval      | 5 seconds      |
| Device ID             | `ESP32_ROOM_1` |

## IoT Data Flow

```text
DS18B20
   |
   v
ESP32
   |
   v
Wi-Fi
   |
   v
POST /temperature
   |
   v
Flask Backend
   |
   v
SQLite Database
   |
   v
PharmaTrack Monitoring Interface
```

## Alert Behaviour

When the temperature rises above 28°C:

1. The ESP32 turns the alert LED on.
2. Temperature data is sent to the backend.
3. The reading is stored in `temperature_logs`.
4. A temperature alert is created.
5. The alert appears in the PharmaTrack monitoring interface.

When the temperature returns to 28°C or below:

1. The ESP32 turns the alert LED off.
2. The new reading is sent to the backend.
3. Active or acknowledged temperature alerts are resolved.

### Example Payload

```json
{
  "device_id": "ESP32_ROOM_1",
  "temperature": 30,
  "humidity": 55,
  "sensor_status": "ACTIVE"
}
```

---

# Database

PharmaTrack uses a centralized SQLite database.

```text
database/database.db
```

| Table              | Purpose                                 |
| ------------------ | --------------------------------------- |
| `medicines`        | Medicine master data                    |
| `medicine_batches` | Batch, quantity, and expiry information |
| `sales`            | Sales transactions                      |
| `temperature_logs` | IoT temperature readings                |
| `alerts`           | Alert records and status                |
| `predictions`      | Demand prediction records               |

## Database Setup

```text
database/database_setup.py
```

## Database Connection

```text
backend/database.py
```

---

# Frontend Modules

The completed frontend includes:

* Smart Medicine Onboarding
* Inventory Management
* Medicine Operations Center
* Cold Chain Monitoring
* Stock Report
* Sales Intelligence
* Expiry Tracking
* Demand Prediction
* Reorder Suggestions
* Alert Command Center
* Medicine Details
* Assistant

---

# Project Structure

```text
PharmaTrack/
|
+-- backend/
|   +-- app.py
|   +-- database.py
|   +-- helpers.py
|   +-- medicines_api.py
|   +-- inventory_api.py
|   +-- sales_api.py
|   +-- cold_chain_api.py
|   +-- assistant_api.py
|   +-- ...
|
+-- database/
|   +-- database.db
|   +-- database_setup.py
|
+-- frontend/
|   +-- ...
|
+-- iot/
|   +-- ...
|
+-- requirements.txt
+-- README.md
```

---

# Installation

Clone the repository:

```bash
git clone <repository-url>
cd PharmaTrack
```

Install the required Python dependencies:

```bash
pip install -r requirements.txt
```

---

# Running the Backend

Start the Flask backend using:

```bash
python -m backend.app
```

The backend runs on:

```text
http://127.0.0.1:5001
```

## Health Check

Open:

```text
http://127.0.0.1:5001/health
```

A successful response confirms that the backend is running correctly.

---

# ESP32 Configuration

For hardware testing, update the ESP32 code with the local IP address of the laptop running the Flask backend.

```cpp
const char* serverUrl = "http://<LAPTOP-IP>:5001/temperature";
```

The ESP32 and the laptop must be connected to the same network.

---

# Testing

API endpoints can be tested using Postman.

Example temperature request:

```http
POST http://127.0.0.1:5001/temperature
```

Request body:

```json
{
  "device_id": "ESP32_ROOM_1",
  "temperature": 30,
  "humidity": 55,
  "sensor_status": "ACTIVE"
}
```

The backend processes the reading, stores it in the database, and generates the corresponding alert when the configured temperature threshold is exceeded.

---

# Project Status

PharmaTrack integrates:

* Medicine and batch management
* FEFO-based inventory management
* Stock monitoring and inventory analytics
* Sales recording and analytics
* Expiry and near-expiry tracking
* Demand analysis
* Reorder suggestions
* ESP32-based cold-chain monitoring
* Temperature and inventory alerts
* Alert acknowledgement and resolution
* Medicine details
* Operational Assistant
* Modular Flask REST APIs
* Centralized SQLite database

The current system is structured as a modular pharmaceutical inventory and cold-chain management platform with web-based monitoring and ESP32 hardware integration.

---

# License

This project is developed for academic and educational purposes.
