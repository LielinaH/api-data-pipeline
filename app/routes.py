import os
import json
import random
from datetime import datetime
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from app.db import get_db_conn
from app.mock_api import generate_mock_orders
from app.pipeline import run_pipeline, REPORTS_DIR

router = APIRouter()

@router.get("/api/mock-source")
def get_mock_source(count: int = 25):
    """
    Returns mock order data from the external source simulation.
    Takes an optional query parameter `count` to vary batch size.
    """
    return generate_mock_orders(count)

@router.post("/api/pipeline/trigger")
def trigger_pipeline():
    """
    Manually triggers the ETL pipeline run.
    Queries the mock API running on the local server or falls back to in-memory.
    """
    # Trigger using local path or self URL.
    # Since server is local, pipeline can fetch directly from our mock route
    api_url = "http://127.0.0.1:8000/api/mock-source"
    result = run_pipeline(api_url=api_url)
    if result["error"]:
        # Don't fail the HTTP response, return pipeline execution details indicating failure
        return result
    return result

@router.get("/api/pipeline/runs")
def get_pipeline_runs():
    """Returns the run history of the pipeline."""
    with get_db_conn() as conn:
        rows = conn.execute("""
            SELECT run_id, start_time, end_time, status, 
                   records_fetched, records_inserted, records_rejected, error_message
            FROM pipeline_runs 
            ORDER BY start_time DESC 
            LIMIT 50
        """).fetchall()
        return [dict(row) for row in rows]

@router.get("/api/pipeline/validation-errors")
def get_validation_errors():
    """Returns the details of validation failures and rejects."""
    with get_db_conn() as conn:
        rows = conn.execute("""
            SELECT id, run_id, record_index, raw_record, error_details, logged_at
            FROM validation_errors
            ORDER BY logged_at DESC
            LIMIT 50
        """).fetchall()
        
        # Parse nested JSON fields for the frontend
        result = []
        for row in rows:
            d = dict(row)
            try:
                d["raw_record"] = json.loads(d["raw_record"])
            except Exception:
                pass
            try:
                d["error_details"] = json.loads(d["error_details"])
            except Exception:
                pass
            result.append(d)
        return result

@router.get("/api/dashboard/stats")
def get_dashboard_stats():
    """Aggregates database metrics for the KPIs panels."""
    try:
        with get_db_conn() as conn:
            # Sales stats
            sales_row = conn.execute("SELECT SUM(total_amount) as sales, COUNT(*) as counts FROM cleaned_orders").fetchone()
            total_sales = sales_row["sales"] or 0.0
            total_orders = sales_row["counts"] or 0
            avg_order_value = total_sales / total_orders if total_orders > 0 else 0.0
            
            # Pipeline run stats
            runs_row = conn.execute("""
                SELECT 
                    COUNT(*) as total_runs,
                    SUM(records_fetched) as total_fetched,
                    SUM(records_inserted) as total_inserted,
                    SUM(records_rejected) as total_rejected,
                    SUM(CASE WHEN status = 'SUCCESS' THEN 1 ELSE 0 END) as success_runs,
                    SUM(CASE WHEN status = 'PARTIAL' THEN 1 ELSE 0 END) as partial_runs
                FROM pipeline_runs
            """).fetchone()
            
            total_runs = runs_row["total_runs"] or 0
            total_fetched = runs_row["total_fetched"] or 0
            total_inserted = runs_row["total_inserted"] or 0
            total_rejected = runs_row["total_rejected"] or 0
            success_runs = runs_row["success_runs"] or 0
            partial_runs = runs_row["partial_runs"] or 0
            
            # Health calculations
            success_rate = ((success_runs + partial_runs) / total_runs * 100) if total_runs > 0 else 0.0
            data_quality_rate = (total_inserted / total_fetched * 100) if total_fetched > 0 else 0.0
            
            # Last run status
            last_run = conn.execute("""
                SELECT run_id, start_time, end_time, status, records_fetched, records_inserted, records_rejected
                FROM pipeline_runs 
                ORDER BY start_time DESC 
                LIMIT 1
            """).fetchone()
            
            return {
                "total_sales": round(total_sales, 2),
                "total_orders": total_orders,
                "avg_order_value": round(avg_order_value, 2),
                "pipeline_health": {
                    "total_runs": total_runs,
                    "success_rate": round(success_rate, 1),
                    "data_quality_rate": round(data_quality_rate, 1)
                },
                "last_run": dict(last_run) if last_run else None
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database aggregation failed: {e}")

@router.get("/api/dashboard/charts")
def get_dashboard_charts():
    """Generates structured chart payloads for UI visualization."""
    try:
        with get_db_conn() as conn:
            # 1. Pipeline execution history (last 10 runs, sorted chronologically)
            run_rows = conn.execute("""
                SELECT run_id, start_time, records_inserted, records_rejected
                FROM pipeline_runs
                ORDER BY start_time DESC
                LIMIT 10
            """).fetchall()
            
            history_data = []
            for row in reversed(run_rows):  # Reverse to read left-to-right (chronological)
                # Format time string for charts
                dt_str = row["start_time"]
                try:
                    dt = datetime.fromisoformat(dt_str)
                    formatted_time = dt.strftime("%H:%M")
                except Exception:
                    formatted_time = dt_str.split("T")[-1][:5] if "T" in dt_str else dt_str[-5:]
                
                history_data.append({
                    "run_id": row["run_id"],
                    "time": formatted_time,
                    "inserted": row["records_inserted"],
                    "rejected": row["records_rejected"]
                })

            # 2. Product distribution (revenue per product)
            product_rows = conn.execute("""
                SELECT product_name, SUM(total_amount) as revenue, COUNT(*) as count
                FROM cleaned_orders
                GROUP BY product_name
                ORDER BY revenue DESC
                LIMIT 5
            """).fetchall()
            
            product_data = [
                {
                    "name": row["product_name"],
                    "revenue": round(row["revenue"], 2),
                    "orders_count": row["count"]
                }
                for row in product_rows
            ]

            # 3. Validation error categories
            error_rows = conn.execute("SELECT error_details FROM validation_errors").fetchall()
            error_counts = {}
            for r in error_rows:
                try:
                    details = json.loads(r["error_details"])
                    for item in details:
                        locs = item.get("loc", ["general"])
                        field = locs[-1] if locs else "general"
                        err_type = item.get("type", "")
                        
                        if "duplicate" in err_type:
                            cat = "Duplicate ID"
                        elif field == "customer_email":
                            cat = "Malformed Email"
                        elif field == "customer_name":
                            cat = "Missing Name"
                        elif field in ("price", "quantity"):
                            cat = "Invalid Price/Qty"
                        elif field == "order_date":
                            cat = "Future Date"
                        else:
                            cat = f"Invalid {field.title()}"
                        
                        error_counts[cat] = error_counts.get(cat, 0) + 1
                except Exception:
                    error_counts["Format Error"] = error_counts.get("Format Error", 0) + 1
                    
            error_data = [{"label": k, "count": v} for k, v in error_counts.items()]

            return {
                "pipeline_history": history_data,
                "product_distribution": product_data,
                "error_breakdown": error_data
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chart generation failed: {e}")

@router.get("/api/dashboard/export")
def download_csv_report():
    """Generates the latest clean order dataset and sends it as a CSV attachment."""
    csv_file = os.path.join(REPORTS_DIR, "cleaned_orders_latest.csv")
    
    # If the file does not exist, trigger a pipeline run to populate database and create it
    if not os.path.exists(csv_file):
        run_pipeline(api_url="http://127.0.0.1:8000/api/mock-source")
        
    if not os.path.exists(csv_file):
        raise HTTPException(status_code=404, detail="No pipeline data available to export.")
        
    return FileResponse(
        path=csv_file,
        media_type="text/csv",
        filename=f"cleaned_orders_report_{datetime.now().strftime('%Y%m%d%H%M%S')}.csv"
    )
