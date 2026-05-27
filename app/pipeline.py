import os
import uuid
import json
import logging
from datetime import datetime
import requests
import pandas as pd

from app.db import get_db_conn, init_db
from app.mock_api import generate_mock_orders
from app.validator import CleanedOrder
from pydantic import ValidationError

# Set up paths relative to this file
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LOG_DIR = os.path.join(BASE_DIR, "logs")
REPORTS_DIR = os.path.join(BASE_DIR, "reports")

os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)

# Set up logging configuration
log_file_path = os.path.join(LOG_DIR, "pipeline.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_file_path),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("data_pipeline")

def fetch_raw_data(api_url: str = None) -> list:
    """
    Fetches raw order data.
    Attempts to make an HTTP request to the mock API server.
    If the server is not running or returns an error, it falls back
    to generating the mock data in-memory to ensure the pipeline is self-healing.
    """
    if api_url:
        try:
            logger.info(f"Attempting to fetch raw data from API: {api_url}")
            response = requests.get(api_url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Successfully fetched {len(data)} records from API.")
                return data
            else:
                logger.warning(f"API returned status code {response.status_code}. Falling back to in-memory generator.")
        except Exception as e:
            logger.warning(f"Could not connect to API ({type(e).__name__}: {e}). Falling back to in-memory generator.")
            
    # Fallback generator
    # Import random locally to support counts bounds
    import random
    logger.info("Using local generator fallback to fetch data.")
    return generate_mock_orders(random.randint(15, 30))

def run_pipeline(api_url: str = None) -> dict:
    """
    Runs the full ETL Pipeline:
    1. Ingestion: Fetches raw JSON data and logs the run.
    2. Extraction: Logs the raw payload.
    3. Transformation & Validation: Cleans fields, identifies duplicates, applies business rules.
    4. Loading: Stores clean records and validation failures.
    5. Reporting: Exports updated data to CSV.
    """
    run_id = f"run_{uuid.uuid4().hex[:12]}"
    start_time = datetime.now()
    
    logger.info(f"=== Starting Pipeline Run: {run_id} ===")
    
    # Guarantee tables exist
    init_db()
    
    # Initialize the run record in the database
    with get_db_conn() as conn:
        conn.execute(
            "INSERT INTO pipeline_runs (run_id, start_time, status) VALUES (?, ?, ?)",
            (run_id, start_time.isoformat(), "FAILED")  # Default to FAILED, updated on successful completion
        )
    
    try:
        # Step 1: Ingestion
        raw_records = fetch_raw_data(api_url)
        records_fetched = len(raw_records)
        logger.info(f"Ingested {records_fetched} raw records.")
        
        # Log the raw payload for audit trails
        with get_db_conn() as conn:
            conn.execute(
                "INSERT INTO raw_ingestion_log (run_id, raw_payload) VALUES (?, ?)",
                (run_id, json.dumps(raw_records))
            )
            
        # Step 2: Validate and clean records
        valid_orders = []
        validation_errors = []
        
        # Load existing order IDs to check for database duplicates
        with get_db_conn() as conn:
            rows = conn.execute("SELECT order_id FROM cleaned_orders").fetchall()
            existing_db_ids = {row["order_id"] for row in rows}
            
        seen_ids_in_batch = set()
        
        for index, record in enumerate(raw_records):
            # Check for missing record
            if not record or not isinstance(record, dict):
                validation_errors.append({
                    "run_id": run_id,
                    "record_index": index,
                    "raw_record": json.dumps(record),
                    "error_details": json.dumps([{"loc": ["root"], "msg": "Empty or invalid record type", "type": "value_error"}])
                })
                continue
                
            order_id = record.get("order_id")
            
            # Check duplicate ID constraints
            is_duplicate = False
            dup_errors = []
            
            if order_id:
                order_id_str = str(order_id).strip()
                if order_id_str in seen_ids_in_batch:
                    is_duplicate = True
                    dup_errors.append({"loc": ["order_id"], "msg": f"Duplicate Order ID '{order_id_str}' in this batch", "type": "duplicate_error"})
                elif order_id_str in existing_db_ids:
                    is_duplicate = True
                    dup_errors.append({"loc": ["order_id"], "msg": f"Order ID '{order_id_str}' already exists in database", "type": "duplicate_error"})
                    
                seen_ids_in_batch.add(order_id_str)
            else:
                is_duplicate = True
                dup_errors.append({"loc": ["order_id"], "msg": "Order ID is missing", "type": "value_error"})
                
            if is_duplicate:
                validation_errors.append({
                    "run_id": run_id,
                    "record_index": index,
                    "raw_record": json.dumps(record),
                    "error_details": json.dumps(dup_errors)
                })
                continue
                
            # Perform fields validation using Pydantic
            try:
                cleaned = CleanedOrder(**record)
                valid_orders.append(cleaned)
            except ValidationError as ve:
                # Capture clean error messages
                errors = []
                for err in ve.errors():
                    errors.append({
                        "loc": err["loc"],
                        "msg": err["msg"],
                        "type": err["type"]
                    })
                validation_errors.append({
                    "run_id": run_id,
                    "record_index": index,
                    "raw_record": json.dumps(record),
                    "error_details": json.dumps(errors)
                })
                
        # Step 3: Load Data to SQLite
        records_inserted = 0
        records_rejected = len(validation_errors)
        
        with get_db_conn() as conn:
            # Insert cleaned orders
            for order in valid_orders:
                conn.execute(
                    """
                    INSERT INTO cleaned_orders (
                        order_id, run_id, customer_name, customer_email, 
                        product_name, price, quantity, total_amount, 
                        order_date, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        order.order_id, run_id, order.customer_name, order.customer_email,
                        order.product_name, order.price, order.quantity, order.total_amount,
                        order.order_date.isoformat(), order.status
                    )
                )
                records_inserted += 1
                
            # Insert validation errors
            for err in validation_errors:
                conn.execute(
                    """
                    INSERT INTO validation_errors (
                        run_id, record_index, raw_record, error_details
                    ) VALUES (?, ?, ?, ?)
                    """,
                    (
                        err["run_id"], err["record_index"], err["raw_record"], err["error_details"]
                    )
                )
                
        # Step 4: Finalize pipeline execution logs
        end_time = datetime.now()
        
        # Determine status
        if records_rejected == 0:
            status = "SUCCESS"
        elif records_inserted > 0:
            status = "PARTIAL"
        else:
            status = "FAILED"
            
        with get_db_conn() as conn:
            conn.execute(
                """
                UPDATE pipeline_runs 
                SET end_time = ?, status = ?, records_fetched = ?, 
                    records_inserted = ?, records_rejected = ?
                WHERE run_id = ?
                """,
                (end_time.isoformat(), status, records_fetched, records_inserted, records_rejected, run_id)
            )
            
        logger.info(f"Pipeline finished: Status={status}, Fetched={records_fetched}, Inserted={records_inserted}, Rejected={records_rejected}")
        
        # Step 5: Export updated CSV reports
        export_cleaned_data_to_csv()
        
        return {
            "run_id": run_id,
            "status": status,
            "records_fetched": records_fetched,
            "records_inserted": records_inserted,
            "records_rejected": records_rejected,
            "error": None
        }
        
    except Exception as e:
        end_time = datetime.now()
        error_msg = f"{type(e).__name__}: {str(e)}"
        logger.error(f"Pipeline crashed! {error_msg}", exc_info=True)
        
        with get_db_conn() as conn:
            conn.execute(
                """
                UPDATE pipeline_runs 
                SET end_time = ?, status = 'FAILED', error_message = ?
                WHERE run_id = ?
                """,
                (end_time.isoformat(), error_msg, run_id)
            )
            
        return {
            "run_id": run_id,
            "status": "FAILED",
            "records_fetched": 0,
            "records_inserted": 0,
            "records_rejected": 0,
            "error": error_msg
        }

def export_cleaned_data_to_csv() -> str:
    """Exports all database cleaned orders into a downloadable CSV report."""
    csv_path = os.path.join(REPORTS_DIR, "cleaned_orders_latest.csv")
    try:
        with get_db_conn() as conn:
            # Read clean orders into pandas dataframe
            df = pd.read_sql_query("SELECT * FROM cleaned_orders ORDER BY order_date DESC", conn)
            
        # Export
        df.to_csv(csv_path, index=False)
        logger.info(f"CSV Report updated successfully at: {csv_path}")
        return csv_path
    except Exception as e:
        logger.error(f"Failed to export cleaned data to CSV: {e}", exc_info=True)
        raise e

if __name__ == "__main__":
    # Test execution
    run_pipeline()
