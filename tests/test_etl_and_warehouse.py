"""
Integration tests for ETL pipeline, row reconciliation, Star Schema constraints,
and referential integrity (zero orphan facts).
"""

import pytest
from etl.extract import extract_raw_data
from etl.clean import clean_destination_records
from etl.transform import transform_to_star_schema
from etl.load import load_star_schema
from sql.database import db


def test_row_count_reconciliation_and_zero_orphans():
    # 1. Extract
    raw = extract_raw_data()
    source_count = len(raw)
    assert source_count == 100

    # 2. Clean
    cleaned, _ = clean_destination_records(raw)
    clean_count = len(cleaned)
    assert clean_count == 100

    # 3. Transform
    transformed = transform_to_star_schema(cleaned)
    fact_count = len(transformed["fact_destination_metrics"])
    assert fact_count == 100

    # 4. Load
    load_rec = load_star_schema(transformed)
    assert load_rec["fact_rows"] == 100
    assert load_rec["orphan_facts"] == 0
    assert load_rec["integrity_status"] == "PASS"

    # Direct DB Verification of Row Counts
    db_fact_count = db.fetch_one("SELECT COUNT(*) AS total FROM fact_destination_metrics;")["total"]
    db_dest_count = db.fetch_one("SELECT COUNT(*) AS total FROM dim_destination WHERE destination_key > 0;")["total"]
    assert db_fact_count == 100
    assert db_dest_count == 100


def test_warehouse_views():
    # Verify full star view
    full_view_res = db.fetch_all("SELECT * FROM vw_star_destination_full LIMIT 5;")
    assert len(full_view_res) == 5
    assert "region" in full_view_res[0]
    assert "mid_daily_avg" in full_view_res[0]

    # Verify unpivoted tier view (100 destinations x 3 tiers = 300 rows)
    tier_view_cnt = db.fetch_one("SELECT COUNT(*) AS total FROM vw_fact_destination_tier_spend;")["total"]
    assert tier_view_cnt == 300


def test_etl_idempotency():
    # Running load a second time must produce exactly the same 100 fact rows
    raw = extract_raw_data()
    cleaned, _ = clean_destination_records(raw)
    transformed = transform_to_star_schema(cleaned)
    load_star_schema(transformed)

    count_after_second_run = db.fetch_one("SELECT COUNT(*) AS total FROM fact_destination_metrics;")["total"]
    assert count_after_second_run == 100
