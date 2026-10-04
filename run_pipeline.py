"""
Main Pipeline Runner for Tourism Data Warehouse and Data Mining System (DMDW)
Executes: Extract -> Clean -> Transform -> Load -> Mine (KMeans, Apriori, Classifier, Outliers, Trends)
Guarantees idempotency and complete row reconciliation.
"""

import sys
import time
import logging

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from etl.extract import extract_raw_data
from etl.clean import clean_destination_records
from etl.transform import transform_to_star_schema
from etl.load import load_star_schema
from mining.kmeans_clustering import run_kmeans_clustering
from mining.association_rules import run_association_rules
from mining.classification import run_classification_models
from mining.outlier_detection import run_outlier_detection
from mining.trend_analysis import run_trend_analysis
from sql.database import db

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def run_full_pipeline():
    start_time = time.time()
    print("=" * 70)
    print("  TOURISM DATA WAREHOUSE & DATA MINING PIPELINE (DMDW)")
    print(f"  Target Database Engine: {db.engine_type.upper()}")
    print("=" * 70)

    # Stage 1: Extract
    print("\n[Phase 3.1] Extracting Raw Data...")
    raw_records = extract_raw_data()
    source_count = len(raw_records)
    print(f"  -> Extracted {source_count} source records.")

    # Stage 2: Clean
    print("\n[Phase 3.2] Cleaning & Standardizing Data...")
    cleaned_records, clean_stats = clean_destination_records(raw_records)
    clean_count = len(cleaned_records)
    print(f"  -> Cleaned {clean_count} records. (Islands imputed: {clean_stats['islands_imputed']})")

    # Stage 3: Transform
    print("\n[Phase 3.3] Transforming into Star Schema...")
    transformed = transform_to_star_schema(cleaned_records)
    fact_count = len(transformed["fact_destination_metrics"])
    print(f"  -> Transformed {fact_count} fact rows and {len(transformed['dim_geography'])-1} geography nodes.")

    # Stage 4: Load
    print("\n[Phase 3.4] Loading Warehouse Tables & Validating FK Integrity...")
    load_summary = load_star_schema(transformed)
    print(f"  -> Loaded {load_summary['fact_rows']} fact rows into {load_summary['engine'].upper()}.")
    print(f"  -> Orphan facts detected: {load_summary['orphan_facts']}. (Status: {load_summary['integrity_status']})")

    # Row reconciliation check
    assert source_count == clean_count == fact_count, "Row reconciliation failure!"
    assert load_summary["orphan_facts"] == 0, "Referential integrity constraint failed!"
    print(f"  -> RECONCILIATION VERIFIED: {source_count} source = {clean_count} clean = {fact_count} fact rows (0 dropped).")

    # Stage 5: Data Mining Modules
    print("\n" + "=" * 70)
    print("  [Phase 5] EXECUTING DATA MINING MODULES FROM WAREHOUSE VIEWS")
    print("=" * 70)

    # 5.1 K-Means Clustering
    print("\n[5.1] K-Means Clustering...")
    km_res = run_kmeans_clustering(random_state=42)
    print(f"  -> Optimal clusters: k={km_res['optimal_k']} (Silhouette Score: {max(km_res['silhouette_scores']):.4f})")
    for cl in km_res["clusters"]:
        print(f"     * Cluster {cl['cluster_id']}: {cl['cluster_label']} ({cl['destination_count']} destinations)")

    # 5.2 Association Rule Mining
    print("\n[5.2] Association Rule Mining (FP-Growth / Apriori)...")
    rule_res = run_association_rules(min_support=0.08, min_confidence=0.5, min_lift=1.2)
    print(f"  -> Discovered {rule_res['total_rules']} high-lift association rules.")
    for r in rule_res["rules"][:3]:
        print(f"     * {r['plain_english_rule']}")

    # 5.3 Classification
    print("\n[5.3] Supervised Classification (Zero-Leakage Benchmark)...")
    clf_res = run_classification_models(random_state=42)
    for m_name, m_metrics in clf_res["models"].items():
        print(f"     * [{m_name}] Accuracy: {m_metrics['accuracy'] * 100:.1f}% | F1: {m_metrics['f1_score']:.3f} | CV: {m_metrics['cv_accuracy_mean'] * 100:.1f}%")

    # 5.4 Outlier Detection
    print("\n[5.4] Outlier Detection (IQR & Isolation Forest)...")
    outlier_res = run_outlier_detection(contamination=0.05, random_state=42)
    print(f"  -> Flagged {outlier_res['total_anomalies_detected']} anomalies across {outlier_res['unique_destinations_flagged']} destinations.")

    # 5.5 Trend & Seasonality Analysis
    print("\n[5.5] Trend & Seasonality Analysis...")
    trend_res = run_trend_analysis()
    stepup = trend_res["tier_stepup_rates"]
    print(f"  -> Daily spend tier progression: Budget ₹{stepup['budget_daily_avg']:,.0f} -> Mid ₹{stepup['mid_daily_avg']:,.0f} (+{stepup['budget_to_mid_stepup_pct']:.1f}%) -> Luxury ₹{stepup['luxury_daily_avg']:,.0f} (+{stepup['mid_to_luxury_stepup_pct']:.1f}%)")

    elapsed = time.time() - start_time
    print("\n" + "=" * 70)
    print(f"  PIPELINE EXECUTION COMPLETED SUCCESSFULLY IN {elapsed:.2f}s")
    print("=" * 70)

    return {
        "status": "SUCCESS",
        "engine": db.engine_type,
        "elapsed_seconds": round(elapsed, 2),
        "row_counts": {
            "source": source_count,
            "cleaned": clean_count,
            "fact": fact_count
        },
        "clusters": km_res["optimal_k"],
        "association_rules": rule_res["total_rules"],
        "outliers_flagged": outlier_res["total_anomalies_detected"]
    }


if __name__ == "__main__":
    run_full_pipeline()
