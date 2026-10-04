"""
Data Mining Module: Supervised Classification
Predicts destination spend tier (High vs Moderate/Budget) using infrastructure,
duration, geography, and ratings.
Enforces strict zero-leakage policy (all cost measures excluded from features)
and compares Random Forest, Logistic Regression, and Decision Tree with cross-validation.
"""

import os
import sys
import json
import logging
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sql.database import db

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

NUMERIC_FEATURES = [
    "ideal_duration_days",
    "min_duration_days",
    "max_duration_days",
    "altitude_m",
    "popularity_score",
    "safety_rating",
    "airport_distance_km",
    "city_distance_km",
    "has_railway_access"
]

CATEGORICAL_FEATURES = [
    "region",
    "accessibility",
    "permits_required"
]


def run_classification_models(random_state=42):
    logger.info("Starting supervised classification pipeline with zero-leakage enforcement...")

    # 1. Fetch data from Warehouse
    query = """
        SELECT 
            f.destination_key,
            d.destination_name,
            g.region,
            c.accessibility,
            c.has_railway_access,
            d.permits_required,
            f.ideal_duration_days,
            f.min_duration_days,
            f.max_duration_days,
            f.altitude_m,
            f.popularity_score,
            f.safety_rating,
            f.airport_distance_km,
            f.city_distance_km,
            f.mid_daily_avg
        FROM fact_destination_metrics f
        JOIN dim_destination d ON f.destination_key = d.destination_key
        JOIN dim_geography g ON f.geography_key = g.geography_key
        JOIN dim_connectivity c ON f.connectivity_key = c.connectivity_key
        ORDER BY f.destination_key
    """
    rows = db.fetch_all(query)
    if not rows:
        raise ValueError("No records found in database for classification.")

    df = pd.DataFrame(rows)

    # 2. Define Binary Target: High-Spend vs Budget/Moderate (Median Split)
    # Median is computed strictly to split classes evenly
    median_spend = float(df["mid_daily_avg"].median())
    df["target"] = (df["mid_daily_avg"] >= median_spend).astype(int)
    class_distribution = df["target"].value_counts().to_dict()
    logger.info(f"Target spend threshold: >= ₹{median_spend:,.2f}. Class distribution: {class_distribution}")

    # ZERO-LEAKAGE ENFORCEMENT: drop mid_daily_avg and all spend keys completely
    X = df[NUMERIC_FEATURES + CATEGORICAL_FEATURES].copy()
    y = df["target"].values

    # 3. Stratified Train / Test Split (Strict ML Best Practice: Split BEFORE any fitting)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=random_state, stratify=y
    )
    logger.info(f"Dataset split: Train={len(X_train)} samples, Test={len(X_test)} samples.")

    # 4. Build Preprocessing Pipeline
    preprocessor = ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), NUMERIC_FEATURES),
            ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), CATEGORICAL_FEATURES)
        ]
    )

    # Fit preprocessor strictly on training data
    preprocessor.fit(X_train)
    feature_names = NUMERIC_FEATURES + list(preprocessor.named_transformers_["cat"].get_feature_names_out(CATEGORICAL_FEATURES))

    # 5. Define Candidate Algorithms
    models = {
        "Random Forest": RandomForestClassifier(n_estimators=100, max_depth=6, random_state=random_state),
        "Logistic Regression": LogisticRegression(max_iter=1000, random_state=random_state),
        "Decision Tree": DecisionTreeClassifier(max_depth=4, random_state=random_state)
    }

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=random_state)
    results = {}
    db_rows = []

    for name, clf in models.items():
        pipeline = Pipeline([
            ("preprocessor", preprocessor),
            ("classifier", clf)
        ])

        # 5-fold cross-validation on training data
        cv_scores = cross_val_score(pipeline, X_train, y_train, cv=cv, scoring="accuracy")
        cv_mean = float(np.mean(cv_scores))
        cv_std = float(np.std(cv_scores))

        # Train on full train set and evaluate on test set
        pipeline.fit(X_train, y_train)
        y_pred = pipeline.predict(X_test)

        acc = float(accuracy_score(y_test, y_pred))
        prec = float(precision_score(y_test, y_pred, zero_division=0))
        rec = float(recall_score(y_test, y_pred, zero_division=0))
        f1 = float(f1_score(y_test, y_pred, zero_division=0))
        cm = confusion_matrix(y_test, y_pred).tolist()

        # Extract Feature Importance / Coefficients
        importance_dict = {}
        fitted_clf = pipeline.named_steps["classifier"]
        if hasattr(fitted_clf, "feature_importances_"):
            importances = fitted_clf.feature_importances_
            importance_dict = {
                f: round(float(imp), 4)
                for f, imp in sorted(zip(feature_names, importances), key=lambda x: x[1], reverse=True)[:10]
            }
        elif hasattr(fitted_clf, "coef_"):
            coefs = np.abs(fitted_clf.coef_[0])
            importance_dict = {
                f: round(float(c), 4)
                for f, c in sorted(zip(feature_names, coefs), key=lambda x: x[1], reverse=True)[:10]
            }

        results[name] = {
            "model_name": name,
            "accuracy": round(acc, 4),
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "f1_score": round(f1, 4),
            "cv_accuracy_mean": round(cv_mean, 4),
            "cv_accuracy_std": round(cv_std, 4),
            "confusion_matrix": cm,
            "feature_importance": importance_dict
        }

        db_rows.append((
            name,
            round(acc, 4),
            round(prec, 4),
            round(rec, 4),
            round(f1, 4),
            json.dumps(cm),
            json.dumps(importance_dict)
        ))

    # 6. Persist Metrics to Database
    db.execute("DELETE FROM mining_classification_metrics;")
    db.executemany(
        """
        INSERT INTO mining_classification_metrics (
            model_name, accuracy, precision_score, recall_score, f1_score,
            confusion_matrix_json, feature_importance_json
        ) VALUES (%s, %s, %s, %s, %s, %s, %s);
        """,
        db_rows
    )
    logger.info(f"Persisted comparison metrics for {len(db_rows)} classification algorithms.")

    return {
        "target_definition": f"Mid-Range Daily Spend >= ₹{median_spend:,.2f} (Median Split)",
        "train_size": len(X_train),
        "test_size": len(X_test),
        "models": results,
        "features_evaluated": NUMERIC_FEATURES + CATEGORICAL_FEATURES
    }


if __name__ == "__main__":
    res = run_classification_models()
    print("Classification comparison complete.")
    for m_name, m_res in res["models"].items():
        print(f"[{m_name}] Accuracy: {m_res['accuracy']:.4f} | F1: {m_res['f1_score']:.4f} | CV: {m_res['cv_accuracy_mean']:.4f}")
        print("  Top Features:", list(m_res["feature_importance"].keys())[:4])
