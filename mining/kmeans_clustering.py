"""
Data Mining Module: K-Means Clustering
Segments destinations using scaled multi-dimensional continuous features.
Optimizes k via Elbow & Silhouette, generates programmatic cluster names, and persists results.
"""

import os
import sys
import logging
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sql.database import db

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

FEATURE_COLS = [
    "mid_daily_avg",
    "ideal_duration_days",
    "popularity_score",
    "safety_rating",
    "altitude_m",
    "airport_distance_km"
]


def run_kmeans_clustering(random_state=42):
    logger.info("Executing K-Means destination segmentation...")
    
    # 1. Fetch data from Warehouse View
    query = """
        SELECT 
            destination_key,
            destination_name,
            region,
            state,
            accessibility,
            mid_daily_avg,
            ideal_duration_days,
            popularity_score,
            safety_rating,
            altitude_m,
            airport_distance_km
        FROM vw_star_destination_full
        ORDER BY destination_key
    """
    rows = db.fetch_all(query)
    if not rows:
        raise ValueError("No destination records available in warehouse view.")

    df = pd.DataFrame(rows)
    X_raw = df[FEATURE_COLS].values

    # 2. Standardize Features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_raw)

    # 3. Optimize K: Evaluate Elbow (Inertia) and Silhouette Scores
    k_range = list(range(2, 7))
    inertias = []
    silhouette_scores = []
    models = {}

    for k in k_range:
        km = KMeans(n_clusters=k, random_state=random_state, n_init=10)
        labels = km.fit_predict(X_scaled)
        sil = silhouette_score(X_scaled, labels)
        inertias.append(float(km.inertia_))
        silhouette_scores.append(float(sil))
        models[k] = (km, labels)

    # Pick optimal k based on peak silhouette score
    best_idx = int(np.argmax(silhouette_scores))
    optimal_k = k_range[best_idx]
    best_model, best_labels = models[optimal_k]
    logger.info(f"Optimal clusters: k={optimal_k} (Silhouette={silhouette_scores[best_idx]:.4f})")

    # 4. Invert Centroids to Original Units
    centroids_raw = scaler.inverse_transform(best_model.cluster_centers_)

    # 5. Programmatic Cluster Naming & Profile Composition
    # Reference baseline medians
    median_spend = float(np.median(df["mid_daily_avg"]))
    median_dur = float(np.median(df["ideal_duration_days"]))
    median_alt = float(np.median(df["altitude_m"]))
    median_pop = float(np.median(df["popularity_score"]))

    cluster_summaries = []
    df["cluster_id"] = best_labels

    for c_id in range(optimal_k):
        c_destinations = df[df["cluster_id"] == c_id]
        c_count = len(c_destinations)
        centroid = centroids_raw[c_id]
        
        c_spend = float(centroid[0])
        c_dur = float(centroid[1])
        c_pop = float(centroid[2])
        c_safe = float(centroid[3])
        c_alt = float(centroid[4])
        c_air = float(centroid[5])

        # Formulate programmatic label components
        spend_desc = "High-Spend" if c_spend > median_spend * 1.1 else ("Budget" if c_spend < median_spend * 0.9 else "Moderate-Spend")
        dur_desc = "Extended-Stay" if c_dur > median_dur else "Short-Getaway"
        alt_desc = "Alpine/High-Altitude" if c_alt > 1500 else ("Mid-Altitude" if c_alt > 400 else "Lowland/Coastal")

        cluster_label = f"{spend_desc} {alt_desc} ({dur_desc})"

        explanation = (
            f"Cluster {c_id + 1} comprises {c_count} destinations characterized by an average daily spend of ₹{c_spend:,.0f}, "
            f"typical stay duration of {c_dur:.1f} days, and an average elevation of {c_alt:.0f}m."
        )

        cluster_summaries.append({
            "cluster_id": c_id + 1,
            "cluster_label": cluster_label,
            "centroid_mid_spend": round(c_spend, 2),
            "centroid_duration": round(c_dur, 1),
            "centroid_popularity": round(c_pop, 2),
            "centroid_safety": round(c_safe, 2),
            "centroid_altitude": round(c_alt, 1),
            "destination_count": c_count,
            "summary_explanation": explanation,
            "sample_destinations": c_destinations["destination_name"].head(5).tolist()
        })

    # 6. Calculate Distance to Assigned Centroid
    distances = np.linalg.norm(X_scaled - best_model.cluster_centers_[best_labels], axis=1)
    df["dist_to_centroid"] = distances

    # 7. Persist to Database Tables
    db.execute("DELETE FROM mining_cluster_assignments;")
    db.execute("DELETE FROM mining_clusters;")

    for c in cluster_summaries:
        db.execute(
            """
            INSERT INTO mining_clusters (
                cluster_id, cluster_label, centroid_mid_spend, centroid_duration,
                centroid_popularity, centroid_safety, centroid_altitude,
                destination_count, summary_explanation
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                c["cluster_id"],
                c["cluster_label"],
                c["centroid_mid_spend"],
                c["centroid_duration"],
                c["centroid_popularity"],
                c["centroid_safety"],
                c["centroid_altitude"],
                c["destination_count"],
                c["summary_explanation"]
            )
        )

    assignment_rows = []
    for _, row in df.iterrows():
        assignment_rows.append((
            int(row["destination_key"]),
            int(row["cluster_id"]) + 1,
            round(float(row["dist_to_centroid"]), 4)
        ))
    db.executemany(
        "INSERT INTO mining_cluster_assignments (destination_key, cluster_id, distance_to_centroid) VALUES (%s, %s, %s);",
        assignment_rows
    )
    logger.info(f"Persisted {len(cluster_summaries)} clusters and {len(assignment_rows)} cluster assignments.")

    return {
        "optimal_k": optimal_k,
        "k_range": k_range,
        "inertias": inertias,
        "silhouette_scores": silhouette_scores,
        "clusters": cluster_summaries,
        "features_used": FEATURE_COLS
    }


if __name__ == "__main__":
    res = run_kmeans_clustering()
    print("K-Means clustering finished. Optimal K:", res["optimal_k"])
    for cl in res["clusters"]:
        print(f"Cluster {cl['cluster_id']}: {cl['cluster_label']} (Count: {cl['destination_count']})")
