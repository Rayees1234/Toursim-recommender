"""
Functional API tests for Flask REST endpoints with valid and invalid inputs.
"""

import json
import pytest
from app.app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_index_route(client):
    res = client.get("/")
    assert res.status_code == 200
    assert b"TOURISM DW" in res.data


def test_api_health(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    data = json.loads(res.data)
    assert data["status"] == "healthy"
    assert data["fact_rows"] == 100


def test_api_filters(client):
    res = client.get("/api/filters")
    assert res.status_code == 200
    data = json.loads(res.data)["data"]
    assert len(data["regions"]) > 0
    assert len(data["accessibility"]) > 0


def test_api_kpis(client):
    res = client.get("/api/kpis")
    assert res.status_code == 200
    data = json.loads(res.data)
    assert data["kpis"]["total_destinations"] == 100
    assert data["kpis"]["avg_mid_daily_inr"] > 0


def test_api_kpis_filtered(client):
    res = client.get("/api/kpis?region=South India")
    assert res.status_code == 200
    data = json.loads(res.data)
    assert data["kpis"]["total_destinations"] > 0
    assert data["kpis"]["total_destinations"] < 100


def test_api_olap_rollup(client):
    res = client.get("/api/olap/rollup?hierarchy=geography")
    assert res.status_code == 200
    data = json.loads(res.data)
    assert len(data["data"]["rows"]) > 0


def test_api_olap_slice_valid(client):
    res = client.get("/api/olap/slice?dim=accessibility&val=Easy")
    assert res.status_code == 200
    data = json.loads(res.data)
    assert data["status"] == "success"
    assert data["count"] > 0


def test_api_olap_slice_invalid_dim(client):
    res = client.get("/api/olap/slice?dim=invalid_column&val=xyz")
    assert res.status_code == 400
    data = json.loads(res.data)
    assert data["status"] == "error"


def test_api_olap_pivot_valid(client):
    res = client.get("/api/olap/pivot?row=region&col=accessibility&measure=mid_daily_avg&agg=AVG")
    assert res.status_code == 200
    data = json.loads(res.data)["data"]
    assert "matrix" in data


def test_api_olap_pivot_invalid_dim(client):
    res = client.get("/api/olap/pivot?row=malicious_col;DROP TABLE--")
    assert res.status_code == 400
    data = json.loads(res.data)
    assert data["status"] == "error"


def test_api_mining_endpoints(client):
    for ep in ["clusters", "rules", "classification", "outliers", "trends"]:
        res = client.get(f"/api/mining/{ep}")
        assert res.status_code == 200
        data = json.loads(res.data)
        assert data["status"] == "success"


def test_api_recommend(client):
    payload = {
        "budget_max": 5000,
        "duration_days": 3,
        "trip_type": "Beach",
        "season": "Winter"
    }
    res = client.post("/api/mining/recommend", json=payload)
    assert res.status_code == 200
    data = json.loads(res.data)
    assert data["status"] == "success"
    assert len(data["result"]["recommendations"]) > 0


def test_api_404_error(client):
    res = client.get("/api/unknown_endpoint")
    assert res.status_code == 404
    data = json.loads(res.data)
    assert data["status"] == "error"
