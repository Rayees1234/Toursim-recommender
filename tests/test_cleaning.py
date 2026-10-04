"""
Unit tests for Data Cleaning and Sanitization functions.
"""

import pytest
from etl.clean import sanitize_text, standardize_region, parse_temperature_range, clean_destination_records
from etl.extract import extract_raw_data


def test_sanitize_text_citations():
    raw = "Popular in winter weeks.[web:269][web:185] Check festival dates."
    cleaned = sanitize_text(raw)
    assert "[web:" not in cleaned
    assert "Popular in winter weeks. Check festival dates." == cleaned


def test_sanitize_text_unicode_dashes():
    raw = "April\u2013June and December\u2014January \u00a0season"
    cleaned = sanitize_text(raw)
    assert "\u2013" not in cleaned
    assert "\u2014" not in cleaned
    assert "\u00a0" not in cleaned
    assert "April-June and December-January season" == cleaned


def test_standardize_region():
    assert standardize_region("North East India") == "Northeast India"
    assert standardize_region("Northeast India") == "Northeast India"
    assert standardize_region("South India") == "South India"
    assert standardize_region("Island Territory") == "Island Territory"


def test_parse_temperature_range():
    t1 = parse_temperature_range("20-32°C")
    assert t1["min_c"] == 20.0
    assert t1["max_c"] == 32.0
    assert t1["avg_c"] == 26.0

    t2 = parse_temperature_range("-15 to -5°C")
    assert t2["min_c"] == -15.0
    assert t2["max_c"] == -5.0
    assert t2["avg_c"] == -10.0

    t3 = parse_temperature_range("data_not_available")
    assert t3["avg_c"] is None
    assert t3["raw_desc"] == "Data Not Available"


def test_clean_destination_records_islands():
    raw_data = extract_raw_data()
    cleaned, stats = clean_destination_records(raw_data)
    assert len(cleaned) == 100
    assert stats["islands_imputed"] == 8
    # Check that island destinations have railway_distance_km = -1 and has_railway_access = 0
    islands = [r for r in cleaned if r["destination_name"].startswith("Havelock") or "Lakshadweep" in r["destination_name"]]
    assert len(islands) > 0
    for isl in islands:
        assert isl["railway_distance_km"] == -1
        assert isl["has_railway_access"] == 0
