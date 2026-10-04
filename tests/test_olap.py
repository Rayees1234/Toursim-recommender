"""
Unit and functional tests for the 5 OLAP operations.
"""

import pytest
from olap.queries import olap


def test_olap_rollup():
    res = olap.rollup_geography()
    assert "rows" in res
    assert "total" in res
    assert len(res["rows"]) >= 5
    # Total destinations across all regions must sum to 100
    sum_dests = sum(r["destination_count"] for r in res["rows"])
    assert sum_dests == 100
    assert res["total"]["destination_count"] == 100


def test_olap_drilldown():
    drill = olap.drilldown_geography("South India")
    assert len(drill) > 0
    for d in drill:
        assert d["region"] == "South India"
        assert "destination_name" in d
        assert "mid_daily_avg" in d


def test_olap_slice():
    slice_easy = olap.slice_dimension("accessibility", "Easy")
    assert len(slice_easy) > 0
    for s in slice_easy:
        assert s["accessibility"] == "Easy"

    # Invalid dimension must raise ValueError
    with pytest.raises(ValueError):
        olap.slice_dimension("invalid_dim", "val")


def test_olap_dice():
    dice_res = olap.dice_dimensions(region="North India", min_safety=8, max_spend=6000)
    assert isinstance(dice_res, list)
    for r in dice_res:
        assert r["region"] == "North India"
        assert r["safety_rating"] >= 8
        assert r["mid_daily_avg"] <= 6000.0


def test_olap_pivot():
    pivot_res = olap.pivot_cube(row_dim="region", col_dim="accessibility", measure="mid_daily_avg", agg_func="AVG")
    assert "matrix" in pivot_res
    assert "col_headers" in pivot_res
    assert len(pivot_res["matrix"]) > 0
    # Check that columns contain accessibility values like 'Easy' or 'Moderate'
    assert any(h in pivot_res["col_headers"] for h in ["Easy", "Moderate", "Difficult"])

    # Invalid row dimension must raise ValueError
    with pytest.raises(ValueError):
        olap.pivot_cube(row_dim="invalid_col")
