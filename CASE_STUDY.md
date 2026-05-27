# Freelance Case Study: E-Commerce Automated Data Integration & Quality Reporting

*This document serves as a copy-pasteable case study structure for freelance platforms (Upwork, Contra, PeoplePerHour, etc.) to showcase how you can automate data engineering pipelines and create reporting dashboards for clients.*

---

## 1. Project Title
**Production-Grade API Automation, ETL Data Pipeline & Analytics Dashboard**

## 2. Executive Summary
A retail client's sales team was spending over 15 hours a week manually exporting CSV reports from an order partner, correcting invalid formats, deduplicating order keys, and copying numbers into internal Excel spreadsheets.

To eliminate this operational bottleneck, I built **FluxETL**: an automated, self-healing data pipeline that fetches raw partner payloads, runs strict quality checks via Pydantic, loads cleaned records into a SQLite data warehouse, and populates an internal control dashboard.

**Results:**
* **100% reduction** in manual data preparation time.
* **100% downstream data integrity** by isolating and quarantining invalid leads/orders automatically.
* **Real-time visibility** into pipeline health, revenue aggregates, and integration logs.

---

## 3. The Challenge & Core Requirements
The client's external sales API was notoriously inconsistent, returning:
1. **Duplicate Transaction IDs** that created ledger errors.
2. **Malformed Emails** causing automated drip campaigns to bounce.
3. **Invalid Price Formats** (e.g. `$49.99USD` string variants rather than raw floats).
4. **Calculated Column Discrepancies** where `total_amount` did not match `price * quantity`.
5. **Future Timestamps** due to server clock desynchronization.

The solution had to be self-healing, run automatically, provide simple administrative dashboard views, and remain easy to deploy without heavy infrastructure costs.

---

## 4. Technical Architecture Decisions

### A. Python & Pydantic Validation (The Core Engine)
I chose Python for its rich data manipulation libraries. Instead of fragile conditional checks, I used **Pydantic v2** models to enforce strict schema validation. This isolates type coercion rules (converting string prices to floats) and syntax checks (email regexes) into a central declarative file (`app/validator.py`), making it simple to modify rules if the client's business logic changes.

### B. FastAPI + Background Scheduler
FastAPI was selected for its exceptional speed, asynchronous lifecycle managers, and built-in interactive OpenAPI docs. Using `APScheduler` directly within the ASGI container allowed us to host the automated cron job in the same environment as the API and Web server, removing the need for external cron utilities or heavy message brokers.

### C. SQLite Portable Data Warehouse
Instead of deploying a costly cloud database instance, I architected the storage engine on **SQLite**. This keeps the application highly portable (single-file database), enables simple local backup strategies, and cuts infrastructure costs to zero for small-to-medium datasets, while allowing easy transition to PostgreSQL down the line.

### D. Single-Page Glassmorphic UI (Vanilla Stack)
Rather than introducing complex React/Next.js build scripts and node module packages, I crafted the admin dashboard with semantic HTML5, Vanilla CSS variables, and modular ES6 JavaScript. It pulls metrics from the API and uses Chart.js to render sleek vector graphs. This makes the system compile-free and immediately runnable with a single command.

---

## 5. Implementation Breakdown & Schema Design

The system relies on a multi-stage database structure to prevent raw errors from contaminating operational stats:
1. **`pipeline_runs`**: Logs when each run executes, the durations, success statuses, and metrics.
2. **`raw_ingestion_log`**: Saves the untouched JSON blob from the external source for audit compliance.
3. **`cleaned_orders`**: Stores standard database tables containing validated, query-ready records.
4. **`validation_errors`**: Stores rejected records, indexing precisely where they failed and linking to Pydantic validation trace arrays.

---

## 6. How I Handled Data Quality Anomalies

* **Strict Casing:** Title-cases customer names and standardizes status categories to uppercase (`COMPLETED`, `PENDING`, `CANCELLED`).
* **Financial Scrubbing:** A custom parser strips symbols (`$`, `USD`, spaces) from raw price strings before validating values.
* **Recalculations:** Re-evaluates `total_amount` using the audited `price * quantity` to guarantee financial consistency.
* **Intelligent Deduplication:** Tracks ids already stored in the database as well as duplicate keys within the incoming batch.
* **Auto-Correction & Quarantining:** A single corrupt record does not fail the sync. Valid rows are committed; corrupted items are logged in the errors database and flagged on the dashboard.

---

## 7. Deliverables & Fictional Impact Metrics
If a client hires you for this service, this project proves you can deliver:
1. **Fully Documented ETL Script**: Run-ready python engine with advanced error fallback logic.
2. **SQL Schema Initialization Script**: Auto-generating database setup code.
3. **Responsive Web UI Dashboard**: Complete control center, with charts, search filters, and triggering controls.
4. **Automated Spreadsheet Downloader**: Live CSV exporter.

*Use this project as your centerpiece to target automated reporting, API integration, and python automation gigs on freelance markets!*
