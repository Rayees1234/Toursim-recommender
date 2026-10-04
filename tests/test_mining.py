"""
Tests for Data Mining modules: K-Means, Association Rules, Classification, Outliers, Trends, Recommender.
"""

import pytest
from mining.kmeans_clustering import run_kmeans_clustering
from mining.association_rules import run_association_rules
from mining.classification import run_classification_models
from mining.outlier_detection import run_outlier_detection
from mining.trend_analysis import run_trend_analysis
from mining.recommender import recommend_destinations


def test_kmeans_clustering():
    res = run_kmeans_clustering(random_state=42)
    assert res["optimal_k"] in (2, 3, 4, 5, 6)
    assert len(res["clusters"]) == res["optimal_k"]
    # Check that each cluster has a programmatic label and explanation
    for c in res["clusters"]:
        assert len(c["cluster_label"]) > 0
        assert len(c["summary_explanation"]) > 0
        assert c["destination_count"] > 0


def test_association_rules():
    res = run_association_rules(min_support=0.08, min_confidence=0.5, min_lift=1.1)
    assert "rules" in res
    assert res["total_rules"] >= 0
    for r in res["rules"]:
        assert r["lift"] > 1.0  # Trivial rules filtered out
        assert len(r["plain_english_rule"]) > 0


def test_classification_zero_leakage():
    res = run_classification_models(random_state=42)
    models = res["models"]
    assert "Random Forest" in models
    assert "Logistic Regression" in models
    assert "Decision Tree" in models

    for m_name, m_data in models.items():
        assert 0.0 <= m_data["accuracy"] <= 1.0
        assert 0.0 <= m_data["f1_score"] <= 1.0
        assert len(m_data["confusion_matrix"]) == 2

    # Check zero leakage: no monetary feature in feature importance
    rf_features = list(models["Random Forest"]["feature_importance"].keys())
    for f in rf_features:
        assert "mid_daily" not in f
        assert "budget_daily" not in f
        assert "luxury_daily" not in f
        assert "cost" not in f


def test_outlier_detection():
    res = run_outlier_detection(contamination=0.05, random_state=42)
    assert res["total_anomalies_detected"] > 0
    assert len(res["destination_names"]) > 0
    for o in res["records"]:
        assert len(o["reason"]) > 0
        assert o["anomaly_score"] >= 0


def test_trend_analysis():
    res = run_trend_analysis()
    assert "seasonal_trends" in res
    assert "regional_trends" in res
    assert "tier_stepup_rates" in res
    # Budget to Mid-Range stepup must be positive
    assert res["tier_stepup_rates"]["budget_to_mid_stepup_pct"] > 0


def test_recommender():
    rec = recommend_destinations(budget_max=6000, duration_days=4, trip_type="Beach", season="Winter")
    assert "recommendations" in rec
    assert len(rec["recommendations"]) <= 5
    for r in rec["recommendations"]:
        assert r["mid_daily_avg"] <= 6000
        assert r["match_score"] >= 0
        assert len(r["match_reasons"]) > 0
