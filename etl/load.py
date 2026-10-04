"""
ETL Module: Load
Idempotently creates warehouse schema and populates dimensions, bridges, and fact tables.
Validates referential integrity and checks for zero orphan facts.
"""

import os
import sys
import logging

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sql.database import db

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def load_star_schema(transformed_data):
    logger.info("Initializing Data Warehouse schema and tables...")
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    schema_path = os.path.join(base_dir, "sql", "schema.sql")
    
    with open(schema_path, "r", encoding="utf-8") as f:
        schema_sql = f.read()

    # 1. Execute DDL Script
    db.execute_script(schema_sql)
    logger.info(f"Schema created successfully using engine: {db.engine_type.upper()}")

    # 2. Insert Helper
    def insert_rows(table_name, rows):
        if not rows:
            return 0
        cols = list(rows[0].keys())
        col_str = ", ".join(cols)
        placeholder_str = ", ".join(["%s"] * len(cols))
        query = f"INSERT INTO {table_name} ({col_str}) VALUES ({placeholder_str})"
        data_tuples = [tuple(r[c] for c in cols) for r in rows]
        db.executemany(query, data_tuples)
        logger.info(f"Loaded {len(rows)} rows into {table_name}.")
        return len(rows)

    # 3. Load Master Dimensions
    insert_rows("dim_date", transformed_data["dim_date"])
    insert_rows("dim_geography", transformed_data["dim_geography"])
    insert_rows("dim_destination", transformed_data["dim_destination"])
    insert_rows("dim_connectivity", transformed_data["dim_connectivity"])
    insert_rows("dim_seasonality", transformed_data["dim_seasonality"])
    insert_rows("dim_trip_type", transformed_data["dim_trip_type"])
    insert_rows("dim_activity", transformed_data["dim_activity"])
    insert_rows("dim_accommodation", transformed_data["dim_accommodation"])
    insert_rows("dim_season", transformed_data["dim_season"])

    # 4. Load Bridge Tables
    insert_rows("bridge_destination_trip_type", transformed_data["bridge_destination_trip_type"])
    insert_rows("bridge_destination_activity", transformed_data["bridge_destination_activity"])
    insert_rows("bridge_destination_accommodation", transformed_data["bridge_destination_accommodation"])
    insert_rows("bridge_destination_season", transformed_data["bridge_destination_season"])

    # 5. Load Fact Table
    fact_count = insert_rows("fact_destination_metrics", transformed_data["fact_destination_metrics"])

    # 6. Referential Integrity & Reconciliation Verification
    logger.info("Executing referential integrity and orphan fact checks...")
    orphan_query = """
        SELECT COUNT(*) AS orphan_count
        FROM fact_destination_metrics f
        LEFT JOIN dim_date dt ON f.date_key = dt.date_key
        LEFT JOIN dim_destination d ON f.destination_key = d.destination_key
        LEFT JOIN dim_geography g ON f.geography_key = g.geography_key
        LEFT JOIN dim_connectivity c ON f.connectivity_key = c.connectivity_key
        LEFT JOIN dim_seasonality s ON f.seasonality_key = s.seasonality_key
        WHERE dt.date_key IS NULL 
           OR d.destination_key IS NULL 
           OR g.geography_key IS NULL 
           OR c.connectivity_key IS NULL 
           OR s.seasonality_key IS NULL
    """
    orphan_res = db.fetch_one(orphan_query)
    orphan_count = orphan_res["orphan_count"] if orphan_res else 0

    reconciliation = {
        "engine": db.engine_type,
        "fact_rows": fact_count,
        "orphan_facts": orphan_count,
        "integrity_status": "PASS" if orphan_count == 0 else "FAIL"
    }
    logger.info(f"Reconciliation Status: {reconciliation}")
    if orphan_count > 0:
        raise ValueError(f"Integrity check failed: found {orphan_count} orphan fact records!")

    return reconciliation


if __name__ == "__main__":
    from extract import extract_raw_data
    from clean import clean_destination_records
    from transform import transform_to_star_schema
    raw = extract_raw_data()
    clean, _ = clean_destination_records(raw)
    td = transform_to_star_schema(clean)
    rec = load_star_schema(td)
    print("ETL Load test completed successfully:", rec)
