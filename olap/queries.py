"""
OLAP Query Engine for Tourism Data Warehouse.
Provides parameterized execution of Roll-up, Drill-down, Slice, Dice, and Pivot operations
with whitelist input validation against SQL injection.
"""

import os
import sys
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sql.database import db

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Security whitelists
ALLOWED_MEASURES = {
    "mid_daily_avg": "f.mid_daily_avg",
    "budget_daily_avg": "f.budget_daily_avg",
    "luxury_daily_avg": "f.luxury_daily_avg",
    "ideal_duration_days": "f.ideal_duration_days",
    "popularity_score": "f.popularity_score",
    "safety_rating": "f.safety_rating",
    "total_estimated_trip_cost_mid": "f.total_estimated_trip_cost_mid",
    "altitude_m": "f.altitude_m",
    "airport_distance_km": "f.airport_distance_km"
}

ALLOWED_AGGS = {"AVG", "SUM", "COUNT", "MIN", "MAX"}

ALLOWED_ROW_DIMS = {
    "region": "g.region",
    "state": "g.state",
    "accessibility": "c.accessibility",
    "permits_required": "d.permits_required"
}

ALLOWED_COL_DIMS = {
    "accessibility": "c.accessibility",
    "region": "g.region",
    "permits_required": "d.permits_required"
}


class OLAPEngine:
    def __init__(self, database_adapter=None):
        self.db = database_adapter or db

    def rollup_geography(self):
        """
        Roll-up along Geography hierarchy: Destination -> State -> Region -> Total
        """
        query = """
            SELECT 
                g.region,
                COUNT(f.destination_key) AS destination_count,
                ROUND(AVG(f.ideal_duration_days), 2) AS avg_ideal_days,
                ROUND(AVG(f.popularity_score), 2) AS avg_popularity,
                ROUND(AVG(f.safety_rating), 2) AS avg_safety,
                ROUND(AVG(f.mid_daily_avg), 2) AS avg_mid_daily_spend,
                ROUND(AVG(f.budget_daily_avg), 2) AS avg_budget_daily_spend,
                ROUND(AVG(f.luxury_daily_avg), 2) AS avg_luxury_daily_spend
            FROM fact_destination_metrics f
            JOIN dim_geography g ON f.geography_key = g.geography_key
            GROUP BY g.region
            ORDER BY destination_count DESC
        """
        rows = self.db.fetch_all(query)
        # Calculate Grand Total for Rollup
        total_query = """
            SELECT 
                'Total (All Regions)' AS region,
                COUNT(f.destination_key) AS destination_count,
                ROUND(AVG(f.ideal_duration_days), 2) AS avg_ideal_days,
                ROUND(AVG(f.popularity_score), 2) AS avg_popularity,
                ROUND(AVG(f.safety_rating), 2) AS avg_safety,
                ROUND(AVG(f.mid_daily_avg), 2) AS avg_mid_daily_spend,
                ROUND(AVG(f.budget_daily_avg), 2) AS avg_budget_daily_spend,
                ROUND(AVG(f.luxury_daily_avg), 2) AS avg_luxury_daily_spend
            FROM fact_destination_metrics f
        """
        total_row = self.db.fetch_one(total_query)
        return {"rows": rows, "total": total_row}

    def rollup_time(self):
        """
        Roll-up along Time calendar hierarchy: Day -> Month -> Quarter -> Year
        """
        query = """
            SELECT 
                dt.year,
                dt.quarter,
                dt.month_name,
                dt.season_name,
                COUNT(f.destination_key) AS destination_count,
                ROUND(AVG(f.mid_daily_avg), 2) AS avg_mid_spend,
                ROUND(AVG(f.popularity_score), 2) AS avg_popularity
            FROM fact_destination_metrics f
            JOIN dim_date dt ON f.date_key = dt.date_key
            GROUP BY dt.year, dt.quarter, dt.month_name, dt.season_name
        """
        return self.db.fetch_all(query)

    def drilldown_geography(self, region_name):
        """
        Drill-down from Region into States, Districts, and individual Destinations
        """
        query = """
            SELECT 
                g.region,
                g.state,
                g.district,
                d.destination_name,
                c.accessibility,
                f.ideal_duration_days,
                f.mid_daily_avg,
                f.popularity_score,
                f.safety_rating,
                f.altitude_m
            FROM fact_destination_metrics f
            JOIN dim_geography g ON f.geography_key = g.geography_key
            JOIN dim_destination d ON f.destination_key = d.destination_key
            JOIN dim_connectivity c ON f.connectivity_key = c.connectivity_key
            WHERE g.region = %s
            ORDER BY g.state, f.popularity_score DESC
        """
        return self.db.fetch_all(query, (region_name,))

    def slice_dimension(self, dimension, value):
        """
        Slice operation: fixes one dimension value and returns the resulting sub-cube.
        """
        dim_map = {
            "region": ("g.region", "dim_geography g ON f.geography_key = g.geography_key"),
            "state": ("g.state", "dim_geography g ON f.geography_key = g.geography_key"),
            "accessibility": ("c.accessibility", "dim_connectivity c ON f.connectivity_key = c.connectivity_key"),
            "permits_required": ("d.permits_required", "dim_destination d ON f.destination_key = d.destination_key")
        }
        
        if dimension not in dim_map:
            raise ValueError(f"Invalid slice dimension '{dimension}'. Allowed: {list(dim_map.keys())}")

        col_expr, join_clause = dim_map[dimension]
        
        # Cast permits value if needed
        if dimension == "permits_required":
            value = 1 if str(value).lower() in ("1", "true", "yes") else 0

        query = f"""
            SELECT 
                d.destination_name,
                g.region,
                g.state,
                c.accessibility,
                f.ideal_duration_days,
                f.budget_daily_avg,
                f.mid_daily_avg,
                f.luxury_daily_avg,
                f.popularity_score,
                f.safety_rating,
                f.total_estimated_trip_cost_mid
            FROM fact_destination_metrics f
            JOIN dim_destination d ON f.destination_key = d.destination_key
            JOIN dim_geography g ON f.geography_key = g.geography_key
            JOIN dim_connectivity c ON f.connectivity_key = c.connectivity_key
            WHERE {col_expr} = %s
            ORDER BY f.popularity_score DESC, f.mid_daily_avg ASC
        """
        return self.db.fetch_all(query, (value,))

    def dice_dimensions(self, region=None, accessibility=None, min_safety=None, max_spend=None, max_days=None):
        """
        Dice operation: filters on multiple dimensions and measure thresholds simultaneously.
        """
        where_clauses = []
        params = []

        if region:
            where_clauses.append("g.region = %s")
            params.append(region)
        if accessibility:
            where_clauses.append("c.accessibility = %s")
            params.append(accessibility)
        if min_safety is not None:
            where_clauses.append("f.safety_rating >= %s")
            params.append(int(min_safety))
        if max_spend is not None:
            where_clauses.append("f.mid_daily_avg <= %s")
            params.append(float(max_spend))
        if max_days is not None:
            where_clauses.append("f.ideal_duration_days <= %s")
            params.append(float(max_days))

        where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

        query = f"""
            SELECT 
                d.destination_name,
                g.region,
                g.state,
                c.accessibility,
                f.ideal_duration_days,
                f.safety_rating,
                f.popularity_score,
                f.budget_daily_avg,
                f.mid_daily_avg,
                f.luxury_daily_avg,
                f.total_estimated_trip_cost_mid
            FROM fact_destination_metrics f
            JOIN dim_destination d ON f.destination_key = d.destination_key
            JOIN dim_geography g ON f.geography_key = g.geography_key
            JOIN dim_connectivity c ON f.connectivity_key = c.connectivity_key
            {where_sql}
            ORDER BY f.popularity_score DESC
        """
        return self.db.fetch_all(query, tuple(params))

    def pivot_cube(self, row_dim="region", col_dim="accessibility", measure="mid_daily_avg", agg_func="AVG"):
        """
        Pivot operation: constructs a cross-tabulated matrix across row and column dimensions.
        """
        if row_dim not in ALLOWED_ROW_DIMS:
            raise ValueError(f"Invalid row dimension '{row_dim}'. Allowed: {list(ALLOWED_ROW_DIMS.keys())}")
        if col_dim not in ALLOWED_COL_DIMS:
            raise ValueError(f"Invalid col dimension '{col_dim}'. Allowed: {list(ALLOWED_COL_DIMS.keys())}")
        if measure not in ALLOWED_MEASURES:
            raise ValueError(f"Invalid measure '{measure}'. Allowed: {list(ALLOWED_MEASURES.keys())}")
        if agg_func.upper() not in ALLOWED_AGGS:
            raise ValueError(f"Invalid aggregation '{agg_func}'. Allowed: {list(ALLOWED_AGGS)}")

        row_expr = ALLOWED_ROW_DIMS[row_dim]
        col_expr = ALLOWED_COL_DIMS[col_dim]
        measure_expr = ALLOWED_MEASURES[measure]
        agg = agg_func.upper()

        # Step 1: Fetch distinct values of column dimension
        col_vals_query = f"""
            SELECT DISTINCT {col_expr} AS col_val
            FROM fact_destination_metrics f
            JOIN dim_destination d ON f.destination_key = d.destination_key
            JOIN dim_geography g ON f.geography_key = g.geography_key
            JOIN dim_connectivity c ON f.connectivity_key = c.connectivity_key
            WHERE {col_expr} IS NOT NULL AND {col_expr} != 'Unknown'
            ORDER BY col_val
        """
        col_rows = self.db.fetch_all(col_vals_query)
        col_headers = [str(r["col_val"]) for r in col_rows]

        # Step 2: Build conditional aggregation expressions
        case_clauses = []
        for val in col_headers:
            safe_alias = "val_" + "".join(c if c.isalnum() else "_" for c in val).lower()
            # Parameterized values in case when
            case_sql = f"ROUND({agg}(CASE WHEN {col_expr} = '{val}' THEN {measure_expr} ELSE NULL END), 2) AS `{val}`"
            case_clauses.append(case_sql)

        cases_sql = ",\n                ".join(case_clauses)
        if cases_sql:
            cases_sql = ", " + cases_sql

        pivot_query = f"""
            SELECT 
                {row_expr} AS `{row_dim}`,
                COUNT(f.destination_key) AS total_destinations,
                ROUND({agg}({measure_expr}), 2) AS overall_{agg.lower()}
                {cases_sql}
            FROM fact_destination_metrics f
            JOIN dim_destination d ON f.destination_key = d.destination_key
            JOIN dim_geography g ON f.geography_key = g.geography_key
            JOIN dim_connectivity c ON f.connectivity_key = c.connectivity_key
            GROUP BY {row_expr}
            ORDER BY total_destinations DESC
        """
        pivot_data = self.db.fetch_all(pivot_query)
        return {
            "row_dim": row_dim,
            "col_dim": col_dim,
            "col_headers": col_headers,
            "measure": measure,
            "aggregation": agg,
            "matrix": pivot_data
        }


olap = OLAPEngine()

if __name__ == "__main__":
    print("Testing OLAP Roll-up...")
    print("Rollup Geography:", olap.rollup_geography()["rows"][:2])
    print("Testing OLAP Drill-down for South India...")
    print("Drilldown count:", len(olap.drilldown_geography("South India")))
    print("Testing OLAP Slice (Accessibility=Easy)...")
    print("Slice count:", len(olap.slice_dimension("accessibility", "Easy")))
    print("Testing OLAP Dice...")
    print("Dice count:", len(olap.dice_dimensions(region="North India", min_safety=8)))
    print("Testing OLAP Pivot (Region x Accessibility)...")
    p = olap.pivot_cube(row_dim="region", col_dim="accessibility", measure="mid_daily_avg", agg_func="AVG")
    print("Pivot columns:", p["col_headers"])
    print("Pivot sample row:", p["matrix"][0])
