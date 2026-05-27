import os
import sqlite3
from contextlib import contextmanager

# Define database directory and path relative to this file
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DB_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DB_DIR, "pipeline.db")

# Ensure the data directory exists
os.makedirs(DB_DIR, exist_ok=True)

@contextmanager
def get_db_conn():
    """Context manager for SQLite database connection."""
    conn = sqlite3.connect(DB_PATH)
    # Enable foreign keys and dictionary-like row factory
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def init_db():
    """Initializes the database schema and creates tables if they don't exist."""
    with get_db_conn() as conn:
        # 1. Pipeline Runs Table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS pipeline_runs (
                run_id TEXT PRIMARY KEY,
                start_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                end_time DATETIME,
                status TEXT CHECK(status IN ('SUCCESS', 'FAILED', 'PARTIAL')),
                records_fetched INTEGER DEFAULT 0,
                records_inserted INTEGER DEFAULT 0,
                records_rejected INTEGER DEFAULT 0,
                error_message TEXT
            );
        """)
        
        # 2. Raw Ingestion Log Table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS raw_ingestion_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT,
                raw_payload TEXT,
                ingested_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(run_id) REFERENCES pipeline_runs(run_id) ON DELETE CASCADE
            );
        """)
        
        # 3. Cleaned Orders Table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS cleaned_orders (
                order_id TEXT PRIMARY KEY,
                run_id TEXT,
                customer_name TEXT NOT NULL,
                customer_email TEXT NOT NULL,
                product_name TEXT NOT NULL,
                price REAL NOT NULL,
                quantity INTEGER NOT NULL,
                total_amount REAL NOT NULL,
                order_date DATETIME NOT NULL,
                status TEXT NOT NULL,
                cleaned_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(run_id) REFERENCES pipeline_runs(run_id) ON DELETE SET NULL
            );
        """)
        
        # 4. Validation Errors Table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS validation_errors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT,
                record_index INTEGER,
                raw_record TEXT,
                error_details TEXT,
                logged_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(run_id) REFERENCES pipeline_runs(run_id) ON DELETE CASCADE
            );
        """)
        
    print(f"Database initialized successfully at: {DB_PATH}")

if __name__ == "__main__":
    init_db()
