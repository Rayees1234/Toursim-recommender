"""
Flask REST API Backend for Tourism Data Warehouse & Data Mining System
Exposes endpoints for KPIs, OLAP operations, Data Mining modules, filters, and health check.
"""

import os
import sys
import json
import logging
from flask import Flask, jsonify, request, render_template

# Ensure workspace root is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sql.database import db
from olap.queries import olap, ALLOWED_MEASURES, ALLOWED_AGGS, ALLOWED_ROW_DIMS, ALLOWED_COL_DIMS
from mining.kmeans_clustering import run_kmeans_clustering
from mining.association_rules import run_association_rules
from mining.classification import run_classification_models
from mining.outlier_detection import run_outlier_detection
from mining.trend_analysis import run_trend_analysis
from mining.recommender import recommend_destinations

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

app = Flask(
    __name__,
    template_folder=os.path.join(os.path.dirname(__file__), "templates"),
    static_folder=os.path.join(os.path.dirname(__file__), "static")
)
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0


# --- Error Handlers ---
@app.errorhandler(400)
def bad_request(e):
    return jsonify({"status": "error", "code": 400, "message": str(e.description)}), 400


@app.errorhandler(404)
def not_found(e):
    return jsonify({"status": "error", "code": 404, "message": "Endpoint or resource not found."}), 404


@app.errorhandler(500)
def internal_error(e):
    logger.error(f"Internal Server Error: {e}")
    return jsonify({"status": "error", "code": 500, "message": "An unexpected server error occurred."}), 500


# --- Frontend Route ---
@app.route("/")
def dashboard():
    return render_template("index.html")


# --- Health Check ---
@app.route("/api/health", methods=["GET"])
def health_check():
    try:
        fact_count_res = db.fetch_one("SELECT COUNT(*) AS total FROM fact_destination_metrics;")
        fact_count = fact_count_res["total"] if fact_count_res else 0
        return jsonify({
            "status": "healthy",
            "database_engine": db.engine_type.upper(),
            "warehouse_status": "connected",
            "fact_rows": fact_count
        })
    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "database_engine": getattr(db, "engine_type", "unknown"),
            "warehouse_status": "disconnected",
            "error": str(e)
        }), 503


# --- Global Filters ---
@app.route("/api/filters", methods=["GET"])
def get_filters():
    try:
        regions = db.fetch_all("SELECT DISTINCT region FROM dim_geography WHERE region != 'Unknown' ORDER BY region;")
        states = db.fetch_all("SELECT DISTINCT state FROM dim_geography WHERE state != 'Unknown' ORDER BY state;")
        access = db.fetch_all("SELECT DISTINCT accessibility FROM dim_connectivity WHERE accessibility != 'Unknown' ORDER BY accessibility;")
        trip_types = db.fetch_all("SELECT DISTINCT trip_type_name FROM dim_trip_type ORDER BY trip_type_name;")
        seasons = db.fetch_all("SELECT DISTINCT season_name FROM dim_season ORDER BY season_name;")

        spend_range = db.fetch_one("""
            SELECT 
                ROUND(MIN(budget_daily_min), 0) AS min_budget,
                ROUND(MAX(luxury_daily_max), 0) AS max_luxury
            FROM fact_destination_metrics;
        """)

        return jsonify({
            "status": "success",
            "data": {
                "regions": [r["region"] for r in regions],
                "states": [s["state"] for s in states],
                "accessibility": [a["accessibility"] for a in access],
                "trip_types": [t["trip_type_name"] for t in trip_types],
                "seasons": [s["season_name"] for s in seasons],
                "min_spend": spend_range["min_budget"] if spend_range else 500,
                "max_spend": spend_range["max_luxury"] if spend_range else 45000
            }
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# --- Executive KPIs (Computed Dynamically) ---
@app.route("/api/kpis", methods=["GET"])
def get_kpis():
    try:
        region = request.args.get("region")
        state = request.args.get("state")
        accessibility = request.args.get("accessibility")

        where_clauses = []
        params = []

        if region and region != "All":
            where_clauses.append("g.region = %s")
            params.append(region)
        if state and state != "All":
            where_clauses.append("g.state = %s")
            params.append(state)
        if accessibility and accessibility != "All":
            where_clauses.append("c.accessibility = %s")
            params.append(accessibility)

        where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

        query = f"""
            SELECT 
                COUNT(DISTINCT f.destination_key) AS total_destinations,
                COUNT(DISTINCT g.state) AS total_states,
                COUNT(DISTINCT g.region) AS total_regions,
                ROUND(AVG(f.ideal_duration_days), 1) AS avg_duration_days,
                ROUND(AVG(f.popularity_score), 2) AS avg_popularity,
                ROUND(AVG(f.safety_rating), 2) AS avg_safety,
                ROUND(AVG(f.budget_daily_avg), 0) AS avg_budget_daily_inr,
                ROUND(AVG(f.mid_daily_avg), 0) AS avg_mid_daily_inr,
                ROUND(AVG(f.luxury_daily_avg), 0) AS avg_luxury_daily_inr,
                ROUND(AVG(f.total_estimated_trip_cost_mid), 0) AS avg_total_trip_cost_inr
            FROM fact_destination_metrics f
            JOIN dim_geography g ON f.geography_key = g.geography_key
            JOIN dim_connectivity c ON f.connectivity_key = c.connectivity_key
            {where_sql};
        """
        kpi_row = db.fetch_one(query, tuple(params))

        # Top destination in current selection
        top_dest_query = f"""
            SELECT d.destination_name, f.popularity_score, f.safety_rating
            FROM fact_destination_metrics f
            JOIN dim_destination d ON f.destination_key = d.destination_key
            JOIN dim_geography g ON f.geography_key = g.geography_key
            JOIN dim_connectivity c ON f.connectivity_key = c.connectivity_key
            {where_sql}
            ORDER BY f.popularity_score DESC, f.safety_rating DESC
            LIMIT 1;
        """
        top_dest = db.fetch_one(top_dest_query, tuple(params))

        return jsonify({
            "status": "success",
            "kpis": kpi_row,
            "most_popular_destination": top_dest["destination_name"] if top_dest else "N/A"
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# --- Spend Breakdown Analytics ---
@app.route("/api/analytics/spend-breakdown", methods=["GET"])
def get_spend_breakdown():
    try:
        query = """
            SELECT 
                'Budget' AS tier,
                ROUND(AVG(budget_accom_avg), 0) AS accommodation,
                ROUND(AVG(budget_food_avg), 0) AS food,
                ROUND(AVG(budget_act_avg), 0) AS activities,
                ROUND(AVG(budget_trans_avg), 0) AS transport,
                ROUND(AVG(budget_daily_avg), 0) AS total_daily
            FROM fact_destination_metrics
            UNION ALL
            SELECT 
                'Mid-Range' AS tier,
                ROUND(AVG(mid_accom_avg), 0) AS accommodation,
                ROUND(AVG(mid_food_avg), 0) AS food,
                ROUND(AVG(mid_act_avg), 0) AS activities,
                ROUND(AVG(mid_trans_avg), 0) AS transport,
                ROUND(AVG(mid_daily_avg), 0) AS total_daily
            FROM fact_destination_metrics
            UNION ALL
            SELECT 
                'Luxury' AS tier,
                ROUND(AVG(luxury_accom_avg), 0) AS accommodation,
                ROUND(AVG(luxury_food_avg), 0) AS food,
                ROUND(AVG(luxury_act_avg), 0) AS activities,
                ROUND(AVG(luxury_trans_avg), 0) AS transport,
                ROUND(AVG(luxury_daily_avg), 0) AS total_daily
            FROM fact_destination_metrics;
        """
        rows = db.fetch_all(query)
        return jsonify({"status": "success", "data": rows})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# --- Destinations Listing ---
@app.route("/api/analytics/destinations", methods=["GET"])
def get_destinations():
    try:
        region = request.args.get("region")
        accessibility = request.args.get("accessibility")
        sort_by = request.args.get("sort_by", "popularity_score")
        limit = int(request.args.get("limit", 100))

        where_clauses = []
        params = []
        if region and region != "All":
            where_clauses.append("g.region = %s")
            params.append(region)
        if accessibility and accessibility != "All":
            where_clauses.append("c.accessibility = %s")
            params.append(accessibility)

        where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

        # Validate sort column
        safe_sort_map = {
            "popularity_score": "f.popularity_score DESC",
            "safety_rating": "f.safety_rating DESC",
            "mid_daily_avg": "f.mid_daily_avg ASC",
            "ideal_duration_days": "f.ideal_duration_days DESC",
            "altitude_m": "f.altitude_m DESC"
        }
        order_sql = safe_sort_map.get(sort_by, "f.popularity_score DESC")

        query = f"""
            SELECT 
                d.destination_key,
                d.destination_name,
                g.region,
                g.state,
                g.district,
                c.accessibility,
                f.ideal_duration_days,
                f.budget_daily_avg,
                f.mid_daily_avg,
                f.luxury_daily_avg,
                f.popularity_score,
                f.safety_rating,
                f.altitude_m,
                f.airport_distance_km
            FROM fact_destination_metrics f
            JOIN dim_destination d ON f.destination_key = d.destination_key
            JOIN dim_geography g ON f.geography_key = g.geography_key
            JOIN dim_connectivity c ON f.connectivity_key = c.connectivity_key
            {where_sql}
            ORDER BY {order_sql}
            LIMIT %s;
        """
        params.append(limit)
        destinations = db.fetch_all(query, tuple(params))
        return jsonify({"status": "success", "count": len(destinations), "data": destinations})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# --- OLAP Endpoints ---
@app.route("/api/olap/rollup", methods=["GET"])
def olap_rollup():
    try:
        hierarchy = request.args.get("hierarchy", "geography").lower()
        if hierarchy == "time":
            data = olap.rollup_time()
            return jsonify({"status": "success", "hierarchy": "time", "data": data})
        else:
            data = olap.rollup_geography()
            return jsonify({"status": "success", "hierarchy": "geography", "data": data})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/olap/drilldown", methods=["GET"])
def olap_drilldown():
    try:
        region = request.args.get("region", "South India")
        data = olap.drilldown_geography(region)
        return jsonify({"status": "success", "region": region, "count": len(data), "data": data})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/olap/slice", methods=["GET"])
def olap_slice():
    try:
        dim = request.args.get("dim", "accessibility")
        val = request.args.get("val", "Easy")
        data = olap.slice_dimension(dim, val)
        return jsonify({"status": "success", "dimension": dim, "value": val, "count": len(data), "data": data})
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/olap/dice", methods=["GET"])
def olap_dice():
    try:
        region = request.args.get("region")
        accessibility = request.args.get("accessibility")
        min_safety = request.args.get("min_safety")
        max_spend = request.args.get("max_spend")
        max_days = request.args.get("max_days")

        data = olap.dice_dimensions(
            region=region,
            accessibility=accessibility,
            min_safety=min_safety,
            max_spend=max_spend,
            max_days=max_days
        )
        return jsonify({"status": "success", "count": len(data), "data": data})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/olap/pivot", methods=["GET"])
def olap_pivot():
    try:
        row = request.args.get("row", "region")
        col = request.args.get("col", "accessibility")
        measure = request.args.get("measure", "mid_daily_avg")
        agg = request.args.get("agg", "AVG")

        data = olap.pivot_cube(row_dim=row, col_dim=col, measure=measure, agg_func=agg)
        return jsonify({"status": "success", "data": data})
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# --- Data Mining Endpoints ---
@app.route("/api/mining/clusters", methods=["GET"])
def get_clusters():
    try:
        # Load from persisted table or compute if needed
        clusters = db.fetch_all("SELECT * FROM mining_clusters ORDER BY cluster_id;")
        assignments = db.fetch_all("""
            SELECT 
                a.destination_key,
                d.destination_name,
                a.cluster_id,
                c.cluster_label,
                a.distance_to_centroid,
                f.mid_daily_avg,
                f.ideal_duration_days,
                f.popularity_score,
                f.safety_rating,
                f.altitude_m
            FROM mining_cluster_assignments a
            JOIN mining_clusters c ON a.cluster_id = c.cluster_id
            JOIN dim_destination d ON a.destination_key = d.destination_key
            JOIN fact_destination_metrics f ON a.destination_key = f.destination_key
            ORDER BY a.cluster_id, a.distance_to_centroid ASC;
        """)

        # If tables are empty, trigger mining run
        if not clusters:
            run_res = run_kmeans_clustering()
            clusters = db.fetch_all("SELECT * FROM mining_clusters ORDER BY cluster_id;")

        return jsonify({
            "status": "success",
            "total_clusters": len(clusters),
            "clusters": clusters,
            "assignments": assignments
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/mining/rules", methods=["GET"])
def get_rules():
    try:
        min_lift = float(request.args.get("min_lift", 1.1))
        min_conf = float(request.args.get("min_conf", 0.5))

        rules = db.fetch_all("""
            SELECT * FROM mining_rules 
            WHERE lift >= %s AND confidence >= %s
            ORDER BY lift DESC, confidence DESC;
        """, (min_lift, min_conf))

        if not rules:
            run_association_rules(min_support=0.08, min_confidence=min_conf, min_lift=min_lift)
            rules = db.fetch_all("SELECT * FROM mining_rules ORDER BY lift DESC, confidence DESC;")

        return jsonify({
            "status": "success",
            "count": len(rules),
            "rules": rules
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/mining/classification", methods=["GET"])
def get_classification():
    try:
        rows = db.fetch_all("SELECT * FROM mining_classification_metrics;")
        if not rows:
            run_classification_models()
            rows = db.fetch_all("SELECT * FROM mining_classification_metrics;")

        parsed_metrics = []
        for r in rows:
            parsed_metrics.append({
                "model_name": r["model_name"],
                "accuracy": float(r["accuracy"]),
                "precision": float(r["precision_score"]),
                "recall": float(r["recall_score"]),
                "f1_score": float(r["f1_score"]),
                "confusion_matrix": json.loads(r["confusion_matrix_json"]),
                "feature_importance": json.loads(r["feature_importance_json"])
            })

        return jsonify({
            "status": "success",
            "models": parsed_metrics,
            "target": "Mid-Range Daily Spend >= Median (₹4,725/day)",
            "leakage_prevention": "All monetary and component spend metrics strictly excluded from features."
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/mining/outliers", methods=["GET"])
def get_outliers():
    try:
        rows = db.fetch_all("SELECT * FROM mining_outliers ORDER BY anomaly_score DESC;")
        if not rows:
            run_outlier_detection()
            rows = db.fetch_all("SELECT * FROM mining_outliers ORDER BY anomaly_score DESC;")

        return jsonify({
            "status": "success",
            "count": len(rows),
            "outliers": rows
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/mining/trends", methods=["GET"])
def get_trends():
    try:
        trend_rows = db.fetch_all("SELECT * FROM mining_trends ORDER BY category_type, destination_count DESC;")
        if not trend_rows:
            run_trend_analysis()
            trend_rows = db.fetch_all("SELECT * FROM mining_trends ORDER BY category_type, destination_count DESC;")

        return jsonify({
            "status": "success",
            "trends": trend_rows
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/mining/recommend", methods=["POST"])
def post_recommend():
    try:
        payload = request.get_json() or {}
        budget = float(payload.get("budget_max", 6000))
        duration = float(payload.get("duration_days", 4))
        region = payload.get("region")
        trip_type = payload.get("trip_type")
        season = payload.get("season")

        rec_res = recommend_destinations(
            budget_max=budget,
            duration_days=duration,
            region=region,
            trip_type=trip_type,
            season=season,
            top_n=5
        )
        return jsonify({"status": "success", "result": rec_res})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# --- Warehouse Metadata & Previews ---
@app.route("/api/warehouse/tables", methods=["GET"])
def get_warehouse_tables():
    try:
        tables = [
            "dim_date", "dim_geography", "dim_destination", "dim_connectivity",
            "dim_seasonality", "dim_trip_type", "dim_activity", "dim_accommodation",
            "dim_season", "bridge_destination_trip_type", "bridge_destination_activity",
            "bridge_destination_accommodation", "bridge_destination_season",
            "fact_destination_metrics", "mining_clusters", "mining_cluster_assignments",
            "mining_rules", "mining_classification_metrics", "mining_outliers", "mining_trends"
        ]
        summaries = []
        for t in tables:
            cnt_res = db.fetch_one(f"SELECT COUNT(*) AS total FROM {t};")
            sample = db.fetch_all(f"SELECT * FROM {t} LIMIT 3;")
            summaries.append({
                "table_name": t,
                "row_count": cnt_res["total"] if cnt_res else 0,
                "columns": list(sample[0].keys()) if sample else [],
                "sample_rows": sample
            })
        return jsonify({"status": "success", "tables": summaries})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
    port = int(os.getenv("FLASK_PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "False").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug)
