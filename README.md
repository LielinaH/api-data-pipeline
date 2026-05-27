# API Data Pipeline & Automated Reporting System (FluxETL)

A production-grade, highly visual data engineering and full-stack automation project. This system fetches raw transactional data from an API source, runs a structured cleaning and validation engine, stores transactions in a query-ready SQLite database, updates an interactive glassmorphic dashboard, and exports report sheets automatically.

Designed to showcase capability in **API Integration**, **Data Validation (Pydantic)**, **Database Architecture**, **Task Scheduling**, and **Internal Dashboard Tooling**.

---

## Key Features

1. **Self-Healing API Fetch**: Simulated partner endpoint feeding real-time orders. If the API is offline, the ingestion engine falls back to an intelligent in-memory mock generator.
2. **Strict Cleaning & Pydantic Validation**:
   - Sanitizes and title-cases name strings.
   - Normalizes email formats and lowers casing.
   - Cleans financial strings (e.g., removes currency symbols, commas).
   - Recalculates and verifies totals for ledger consistency.
   - Flags duplicate order keys and future transaction dates.
3. **Data Quality Isolation**: Raw payloads and cleaned rows are written separately. Invalid payloads are captured in a dedicated validation error table alongside specific error traces.
4. **Automated Background Scheduler**: Built-in cron scheduler triggers sync cycles every 5 minutes.
5. **Interactive Dashboard Console**: Dark-themed, glassmorphic layout displaying sales KPIs, performance metrics, Chart.js run summaries, and logs.
6. **On-Demand Exporter**: Instant manual triggers and download links for Excel-compatible CSV reports.

---

## Technical Architecture

* **Backend**: Python 3.11+, FastAPI (REST API endpoints), Uvicorn (ASGI server)
* **ETL & Validation**: Pydantic v2 (Strict Schema Checking), Pandas (Data Aggregation & Output)
* **Database**: SQLite (Transacted, relational store with foreign key enforcement)
* **Frontend**: HTML5, Vanilla ES6 JavaScript (Modular structure), Custom CSS Variables (Premium layout, custom responsive grids, glassmorphism), Chart.js (Dynamic graphing)

---

## Directory Layout

```
api-data-pipeline/
├── main.py                # Entry point script
├── requirements.txt       # Core dependencies
├── app/
│   ├── __init__.py
│   ├── db.py              # SQLite schemas & connection management
│   ├── mock_api.py        # Dynamic mock order stream generator
│   ├── validator.py       # Pydantic validation rules and clean-ups
│   ├── pipeline.py        # Core Ingestion, Clean, Load ETL script
│   └── routes.py          # FastAPI router endpoints (Stats, Chart payloads, Trigger)
├── static/
│   ├── index.html         # SPA Dashboard structure
│   ├── style.css          # Dark-theme stylesheet with glassmorphism
│   └── app.js             # API caller, DOM mapper, and chart drawer
├── data/
│   └── pipeline.db        # SQLite database (auto-created)
├── logs/
│   └── pipeline.log       # Pipeline file logs (auto-created)
└── reports/
    └── cleaned_orders_latest.csv # Latest clean CSV output (auto-created)
```

---

## Setup & Running Guide

### Prerequisites
Make sure you have **Python 3.11+** installed.

### 1. Install Dependencies
Clone the repository, open a terminal in the root folder, and run:
```bash
pip install -r requirements.txt
```

### 2. Start the Server
Run the root runner script:
```bash
python main.py
```

### 3. Open the Dashboard
Open your browser and navigate to:
```text
http://127.0.0.1:8000
```
* **Interactive API Spec**: Go to `http://127.0.0.1:8000/docs` to see the automated Swagger/OpenAPI documentation.

---

## Portfolio Screenshot Checklist
If you are deploying this for a freelance portfolio, be sure to capture:
1. **The Executive Overview**: The primary dashboard showing the KPIs, the linear chart of run logs, and the product distribution doughnut.
2. **Quality Control Logs**: Navigate to "Validation Logs" to showcase how records with malformed emails, negative prices, or duplicate IDs are quarantined with red warning tags.
3. **OpenAPI Swagger Interface**: A screenshot of the `/docs` path, demonstrating clean API architecture.
4. **Trigger Flow (GIF)**: Click the "Run Pipeline" button, capturing the loading animation, the success toast, and the statistics incrementing in real-time.
