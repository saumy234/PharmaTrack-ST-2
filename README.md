

This package keeps the four selected frontend pages unchanged and reorganizes the backend into small API modules.

## Four selected pages
1. Smart Medicine Onboarding
2. Inventory Management
3. Medicine Operations Center
4. Cold Chain Monitoring

## API surface
- GET /medicines
- POST /medicines
- PUT /medicines/restock/<id>
- DELETE /batches/<batch_id>
- POST /sales
- DELETE /medicines/<id>
- GET /temperature
- POST /temperature
- GET /alerts
- GET /health (diagnostic)

## Port
The supplied frontend pages hard-code `http://127.0.0.1:5001`, so this backend intentionally runs on port **5001**. The frontend is not changed.

## Database — one database only
There is exactly **one SQLite database file** in this package:

`database/database.db`

`database/database_setup.py` is only the setup/seed Python script supplied for the database. It is **not** a second database.

The included `database.db` was generated from that supplied setup script so the backend can be checked against the supplied schema/data. It contains the five medicines, six batches, ten temperature readings, one alert, and one prediction created by that script.

The backend connects to `database/database.db` through `backend/database.py`.

## Verified database schema
The backend-required tables and columns were checked successfully:
- medicines
- medicine_batches
- sales
- temperature_logs
- alerts

The supplied database also contains `predictions`; this is preserved and is not required by the four selected frontend pages.

## Important business-rule finding
The supplied seed data contains already-expired medicine batches. That is useful for testing expiry handling. During review, the current sales logic orders all positive-quantity batches by expiry but does not itself exclude expired batches. Therefore, before treating this version as final production/submission logic, the sale/stock calculation should be reviewed so expired stock cannot be sold or counted as usable stock.

## Run
From the project root:

```bash
pip install -r requirements.txt
python -m backend.app
```
