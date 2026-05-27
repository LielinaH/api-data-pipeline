import os
import threading
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from apscheduler.schedulers.background import BackgroundScheduler

from app.db import init_db
from app.routes import router
from app.pipeline import run_pipeline

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Initialize SQLite Database
    init_db()
    
    # 2. Setup Background Scheduler for ETL
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        func=run_pipeline,
        trigger="interval",
        minutes=5,
        args=["http://127.0.0.1:8000/api/mock-source"],
        id="etl_sync_job"
    )
    scheduler.start()
    print("APScheduler started: Pipeline will sync every 5 minutes.")
    
    # 3. Spin up initial run in a separate thread so startup is non-blocking
    threading.Thread(
        target=run_pipeline, 
        args=("http://127.0.0.1:8000/api/mock-source",), 
        daemon=True
    ).start()
    print("Initial ETL pipeline run kicked off.")
    
    yield
    
    # 4. Clean up scheduler on shutdown
    scheduler.shutdown()
    print("APScheduler stopped.")

# Instantiate FastAPI application
app = FastAPI(
    title="API Data Pipeline & Automated Reporting System",
    description="Frictionless API ingestion, Pydantic validation, SQLite warehousing, and CSV reporting.",
    version="1.0.0",
    lifespan=lifespan
)

# Attach API endpoints
app.include_router(router)

# Resolve paths for static UI dashboard assets
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(BASE_DIR, "static")
os.makedirs(STATIC_DIR, exist_ok=True)

# Mount the static files directory
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/", response_class=HTMLResponse)
def get_dashboard():
    """Serves the dashboard single page interface."""
    index_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_file):
        with open(index_file, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(
        content="<h1>Dashboard layout (static/index.html) is missing!</h1><p>Please check the project directory.</p>",
        status_code=404
    )
