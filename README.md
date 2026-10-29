# Employee Performance Management System

A Python/FastAPI project for managing employee goals, check-ins, performance reviews, competency feedback, approvals, evidence links, audit history, and record-version snapshots. The included data generators create a deterministic synthetic dataset.

## Tech stack

- Python 3.11+
- FastAPI and Uvicorn
- SQLite
- pandas and Faker
- pytest and HTTPX

## Setup

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
```

## Build the synthetic database

Run from the repository root in this order. The database and generated backups are intentionally ignored by Git.

```bash
python scripts/setup_db.py
python scripts/generate_data.py
python scripts/generate_goals.py
python scripts/generate_checkins.py
python scripts/generate_reviews.py
python scripts/generate_traceability.py
python scripts/update_goal_statuses.py
python scripts/detect_anomalies.py
```

The scripts create `data/employee_performance.db` and write the anomaly report to `reports/anomaly_report.json`. The dataset is synthetic.

## Run the API

```bash
uvicorn app.main:app --reload
```

Useful endpoints:

- `http://127.0.0.1:8000/` — API root
- `http://127.0.0.1:8000/health` — health check
- `http://127.0.0.1:8000/docs` — interactive API documentation
- `http://127.0.0.1:8000/dashboard/summary` — dashboard summary

## Run tests

The tests expect the generated database, so build it first using the commands above.

```bash
pytest -q
```

GitHub Actions runs the database-generation pipeline and test suite on pushes and pull requests.

## Repository layout

- `app/` — FastAPI application
- `docs/schema.sql` — SQLite schema
- `docs/data_dictionary.md` — table and field reference
- `scripts/` — database setup, synthetic data generation, traceability, and anomaly detection
- `tests/` — API, anomaly detector, and database integrity tests
- `reports/` — reviewed anomaly report
- `data/` — generated local database files (not committed)

## Notes

- Do not commit local virtual environments, bytecode, database backups, or secrets.
- The generators are intended for a fresh database. If you want to rebuild the data, remove the local database first and rerun the pipeline.
