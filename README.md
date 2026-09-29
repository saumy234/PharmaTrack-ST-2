# PharmaTrack — Backend

**PharmaTrack** is a smart pharmaceutical inventory and cold-chain monitoring system. This backend is organized into modular API components while maintaining compatibility with the existing frontend pages.

---

##  Selected Frontend Modules

The backend supports the following frontend modules:

* **Smart Medicine Onboarding**
* **Inventory Management**
* **Medicine Operations Center**
* **Cold Chain Monitoring**

The existing frontend is kept unchanged.

---

##  API Endpoints

|  Method  | Endpoint              | Description                           |
| :------: | --------------------- | ------------------------------------- |
|   `GET`  | `/medicines`          | Retrieve medicines and inventory data |
|  `POST`  | `/medicines`          | Add a new medicine                    |
|   `PUT`  | `/medicines/restock/` | Restock an existing medicine          |
| `DELETE` | `/batches/<batch_id>` | Delete a medicine batch               |
|  `POST`  | `/sales`              | Record a medicine sale                |
| `DELETE` | `/medicines/`         | Delete a medicine                     |
|   `GET`  | `/temperature`        | Retrieve temperature readings         |
|  `POST`  | `/temperature`        | Add a temperature reading             |
|   `GET`  | `/alerts`             | Retrieve system alerts                |
|   `GET`  | `/health`             | Check backend status                  |

---

## ⚙️ Server Configuration

The frontend communicates with:

```text
http://127.0.0.1:5001
```

Therefore, the backend runs on **port 5001**.

> The frontend does not require any changes.

---

##  Database

PharmaTrack uses a **single SQLite database**:

```text
database/database.db
```

The database setup/seed script is:

```text
database/database_setup.py
```

Database access is handled through:

```text
backend/database.py
```

### Database Tables

The main backend tables are:

* `medicines`
* `medicine_batches`
* `sales`
* `temperature_logs`
* `alerts`

A `predictions` table is also preserved in the database for compatibility, although it is not required by the selected frontend modules.

---

##  Project Structure

```text
PharmaTrack/
│
├── backend/
│   ├── app.py
│   ├── database.py
│   └── ...
│
├── database/
│   ├── database.db
│   └── database_setup.py
│
├── frontend/
│   └── selected frontend pages
│
├── requirements.txt
└── README.md
```

---

##  Business Rule

The supplied database contains expired batches for testing expiry-related functionality.

Before production deployment, the sales and inventory logic should ensure that:

* Expired batches cannot be sold.
* Expired stock is not treated as usable inventory.
* Stock calculations correctly exclude expired batches.

---

##  Installation & Setup

### 1. Install Dependencies

From the project root:

```bash
pip install -r requirements.txt
```

### 2. Start the Backend

```bash
python -m backend.app
```

### 3. Access the Backend

The server will run at:

```text
http://127.0.0.1:5001
```

---

##  Health Check

Use the following endpoint to verify that the backend is running:

```http
GET /health
```

Full URL:

```text
http://127.0.0.1:5001/health
```

A successful response confirms that the backend is running correctly.

---

##  Technology Stack

* **Backend:** Python, Flask
* **Database:** SQLite
* **API:** RESTful HTTP endpoints
* **Frontend:** HTML, CSS, JavaScript
* **Testing:** Postman / Browser

---

##  Notes

* The backend is modularized into separate API components.
* The existing frontend endpoints and port configuration are preserved.
* Only one SQLite database is used.
* `database_setup.py` is a setup script, **not a separate database**.
