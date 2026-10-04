"""
Data Mining Module: Outlier & Anomaly Detection
Detects anomalies using both univariate methods (IQR, Z-Score) and multivariate Isolation Forest.
Provides clear threshold explanations and persists flagged records to the warehouse.
"""

import os
import sys
import logging
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sql.database import db

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

NUM_OUTLIER_COLS = [
    ("altitude_m", "Elevation / Altitude (m)"),
    ("mid_daily_avg", "Mid-Range Daily Spend (INR)"),
    ("luxury_daily_max", "Luxury Daily Max Spend (INR)"),
    ("airport_distance_km", "Airport Distance (km)"),
    ("ideal_duration_days", "Ideal Duration (Days)")
]


def run_outlier_detection(z_threshold=2.5, iqr_multiplier=1.5, contamination=0.05, random_state=42):
    logger.info("Executing Outlier Detection (IQR, Z-Score, and Isolation Forest)...")

    query = """
        SELECT 
            f.destination_key,
            d.destination_name,
            g.region,
            g.state,
            f.altitude_m,
            f.mid_daily_avg,
            f.luxury_daily_max,
            f.airport_distance_km,
            f.ideal_duration_days
        FROM fact_destination_metrics f
        JOIN dim_destination d ON f.destination_key = d.destination_key
        JOIN dim_geography g ON f.geography_key = g.geography_key
        ORDER BY f.destination_key
    """
    rows = db.fetch_all(query)
    if not rows:
        raise ValueError("No records found in database for outlier detection.")

    df = pd.DataFrame(rows)
    flagged_records = []
    outlier_rows_to_persist = []
    outlier_id = 1

    # 1. Univariate IQR & Z-Score Detection
    for col, display_name in NUM_OUTLIER_COLS:
        vals = df[col].astype(float)
        mean_val = vals.mean()
        std_val = vals.std()

        # Z-Scores
        z_scores = (vals - mean_val) / (std_val if std_val > 0 else 1.0)
        
        # IQR
        q25 = vals.quantile(0.25)
        q75 = vals.quantile(0.75)
        iqr = q75 - q25
        lower_bound = q25 - (iqr_multiplier * iqr)
        upper_bound = q75 + (iqr_multiplier * iqr)

        for idx, row in df.iterrows():
            v = float(row[col])
            z = float(z_scores.iloc[idx])
            
            # Check Upper IQR Outlier
            if v > upper_bound or v < lower_bound:
                reason = (
                    f"Value of {v:,.1f} lies outside IQR bounds [{lower_bound:,.1f}, {upper_bound:,.1f}] "
                    f"for {display_name} (Z-Score: {z:+.2f})."
                )
                flagged_records.append({
                    "outlier_id": outlier_id,
                    "destination_key": int(row["destination_key"]),
                    "destination_name": row["destination_name"],
                    "method": "IQR Outlier",
                    "feature_name": col,
                    "feature_value": round(v, 2),
                    "threshold_value": round(upper_bound if v > upper_bound else lower_bound, 2),
                    "anomaly_score": round(abs(z), 4),
                    "reason": reason
                })
                outlier_rows_to_persist.append((
                    outlier_id,
                    int(row["destination_key"]),
                    row["destination_name"],
                    "IQR Outlier",
                    col,
                    round(v, 2),
                    round(upper_bound if v > upper_bound else lower_bound, 2),
                    round(abs(z), 4),
                    reason
                ))
                outlier_id += 1

    # 2. Multivariate Isolation Forest Detection
    features_for_iforest = [c for c, _ in NUM_OUTLIER_COLS]
    X = df[features_for_iforest].values

    iso_forest = IsolationForest(
        contamination=contamination,
        random_state=random_state,
        n_estimators=100
    )
    preds = iso_forest.fit_predict(X)  # -1 for anomaly, 1 for inlier
    scores = -iso_forest.decision_function(X)  # Higher score = more anomalous

    for idx, row in df.iterrows():
        if preds[idx] == -1:
            anomaly_score = float(scores[idx])
            # Determine most deviant feature for this row
            row_deviations = []
            for col, dname in NUM_OUTLIER_COLS:
                dev = abs(float(row[col]) - df[col].mean()) / df[col].std()
                row_deviations.append((col, dname, float(row[col]), dev))
            top_col, top_name, top_val, top_dev = sorted(row_deviations, key=lambda x: x[3], reverse=True)[0]

            reason = (
                f"Multivariate Isolation Forest identified destination as an anomalous combination. "
                f"Primary contributing feature is {top_name} ({top_val:,.1f}, deviation: {top_dev:.1f} standard deviations from mean)."
            )

            flagged_records.append({
                "outlier_id": outlier_id,
                "destination_key": int(row["destination_key"]),
                "destination_name": row["destination_name"],
                "method": "Isolation Forest",
                "feature_name": top_col,
                "feature_value": round(top_val, 2),
                "threshold_value": 0.0,
                "anomaly_score": round(anomaly_score, 4),
                "reason": reason
            })
            outlier_rows_to_persist.append((
                outlier_id,
                int(row["destination_key"]),
                row["destination_name"],
                "Isolation Forest",
                top_col,
                round(top_val, 2),
                0.0,
                round(anomaly_score, 4),
                reason
            ))
            outlier_id += 1

    # 3. Persist to Database
    db.execute("DELETE FROM mining_outliers;")
    if outlier_rows_to_persist:
        db.executemany(
            """
            INSERT INTO mining_outliers (
                outlier_id, destination_key, destination_name, method, feature_name,
                feature_value, threshold_value, anomaly_score, reason
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
            """,
            outlier_rows_to_persist
        )
    logger.info(f"Detected and persisted {len(outlier_rows_to_persist)} outlier instances.")

    # Deduplicate flagged destination names for summary
    unique_outlier_destinations = sorted(list(set(r["destination_name"] for r in flagged_records)))

    return {
        "total_anomalies_detected": len(flagged_records),
        "unique_destinations_flagged": len(unique_outlier_destinations),
        "destination_names": unique_outlier_destinations,
        "records": flagged_records
    }


if __name__ == "__main__":
    res = run_outlier_detection()
    print(f"Total anomaly instances flagged: {res['total_anomalies_detected']} across {res['unique_destinations_flagged']} destinations.")
    for o in res["records"][:6]:
        print(f"[{o['method']}] {o['destination_name']} - {o['feature_name']} = {o['feature_value']}: {o['reason']}")
