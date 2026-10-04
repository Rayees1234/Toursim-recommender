"""
Data Mining Module: Trend & Seasonality Analysis
Evaluates seasonal distribution, regional dynamics, accessibility trends,
and cross-tier spend growth rates across the warehouse.
"""

import os
import sys
import logging
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sql.database import db

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def run_trend_analysis():
    logger.info("Executing Trend and Seasonality Analysis...")

    # 1. National Baselines
    base_q = """
        SELECT 
            COUNT(*) AS total_count,
            ROUND(AVG(mid_daily_avg), 2) AS nat_avg_mid_spend,
            ROUND(AVG(budget_daily_avg), 2) AS nat_avg_budget_spend,
            ROUND(AVG(luxury_daily_avg), 2) AS nat_avg_luxury_spend,
            ROUND(AVG(ideal_duration_days), 2) AS nat_avg_days,
            ROUND(AVG(popularity_score), 2) AS nat_avg_popularity,
            ROUND(AVG(safety_rating), 2) AS nat_avg_safety
        FROM fact_destination_metrics;
    """
    nat_base = db.fetch_one(base_q)
    nat_mid_spend = float(nat_base["nat_avg_mid_spend"])
    nat_pop = float(nat_base["nat_avg_popularity"])

    # 2. Seasonality Dynamics (Best Seasons)
    seas_q = """
        SELECT 
            s.season_name,
            COUNT(DISTINCT b.destination_key) AS destination_count,
            ROUND(AVG(f.mid_daily_avg), 2) AS avg_mid_spend,
            ROUND(AVG(f.budget_daily_avg), 2) AS avg_budget_spend,
            ROUND(AVG(f.luxury_daily_avg), 2) AS avg_luxury_spend,
            ROUND(AVG(f.popularity_score), 2) AS avg_popularity,
            ROUND(AVG(f.safety_rating), 2) AS avg_safety,
            ROUND(AVG(f.ideal_duration_days), 2) AS avg_duration
        FROM bridge_destination_season b
        JOIN dim_season s ON b.season_key = s.season_key
        JOIN fact_destination_metrics f ON b.destination_key = f.destination_key
        WHERE b.season_type = 'best'
        GROUP BY s.season_name
        ORDER BY destination_count DESC
    """
    seas_rows = db.fetch_all(seas_q)
    for r in seas_rows:
        r_spend = float(r["avg_mid_spend"])
        r["spend_premium_pct"] = round(((r_spend - nat_mid_spend) / nat_mid_spend) * 100, 2)

    # 3. Regional Macro Trends
    reg_q = """
        SELECT 
            g.region,
            COUNT(f.destination_key) AS destination_count,
            ROUND(AVG(f.mid_daily_avg), 2) AS avg_mid_spend,
            ROUND(AVG(f.popularity_score), 2) AS avg_popularity,
            ROUND(AVG(f.safety_rating), 2) AS avg_safety,
            ROUND(AVG(f.ideal_duration_days), 2) AS avg_duration
        FROM fact_destination_metrics f
        JOIN dim_geography g ON f.geography_key = g.geography_key
        GROUP BY g.region
        ORDER BY destination_count DESC
    """
    reg_rows = db.fetch_all(reg_q)
    for r in reg_rows:
        r_spend = float(r["avg_mid_spend"])
        r["spend_growth_relative_to_national"] = round(((r_spend - nat_mid_spend) / nat_mid_spend) * 100, 2)

    # 4. Accessibility Tier Trends
    acc_q = """
        SELECT 
            c.accessibility,
            COUNT(f.destination_key) AS destination_count,
            ROUND(AVG(f.mid_daily_avg), 2) AS avg_mid_spend,
            ROUND(AVG(f.popularity_score), 2) AS avg_popularity,
            ROUND(AVG(f.safety_rating), 2) AS avg_safety,
            ROUND(AVG(f.ideal_duration_days), 2) AS avg_duration
        FROM fact_destination_metrics f
        JOIN dim_connectivity c ON f.connectivity_key = c.connectivity_key
        GROUP BY c.accessibility
        ORDER BY destination_count DESC
    """
    acc_rows = db.fetch_all(acc_q)

    # 5. Cross-Tier Spend Step-Up Rates
    nat_budget = float(nat_base["nat_avg_budget_spend"])
    nat_luxury = float(nat_base["nat_avg_luxury_spend"])
    budget_to_mid_stepup = round(((nat_mid_spend - nat_budget) / nat_budget) * 100, 2)
    mid_to_lux_stepup = round(((nat_luxury - nat_mid_spend) / nat_mid_spend) * 100, 2)

    tier_growth = {
        "budget_daily_avg": nat_budget,
        "mid_daily_avg": nat_mid_spend,
        "luxury_daily_avg": nat_luxury,
        "budget_to_mid_stepup_pct": budget_to_mid_stepup,
        "mid_to_luxury_stepup_pct": mid_to_lux_stepup
    }

    # 6. Persist to mining_trends Table
    db.execute("DELETE FROM mining_trends;")
    trend_rows = []
    t_id = 1
    for r in seas_rows[:10]:
        trend_rows.append((
            t_id, "Season", r["season_name"], float(r["avg_mid_spend"]),
            float(r["avg_popularity"]), float(r["avg_duration"]), float(r["avg_safety"]),
            int(r["destination_count"])
        ))
        t_id += 1

    for r in reg_rows:
        trend_rows.append((
            t_id, "Region", r["region"], float(r["avg_mid_spend"]),
            float(r["avg_popularity"]), float(r["avg_duration"]), float(r["avg_safety"]),
            int(r["destination_count"])
        ))
        t_id += 1

    for r in acc_rows:
        trend_rows.append((
            t_id, "Accessibility", r["accessibility"], float(r["avg_mid_spend"]),
            float(r["avg_popularity"]), float(r["avg_duration"]), float(r["avg_safety"]),
            int(r["destination_count"])
        ))
        t_id += 1

    db.executemany(
        """
        INSERT INTO mining_trends (
            trend_id, category_type, category_value, avg_mid_spend, avg_popularity,
            avg_duration, avg_safety, destination_count
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
        """,
        trend_rows
    )
    logger.info(f"Persisted {len(trend_rows)} trend metrics to database.")

    return {
        "national_baseline": nat_base,
        "seasonal_trends": seas_rows,
        "regional_trends": reg_rows,
        "accessibility_trends": acc_rows,
        "tier_stepup_rates": tier_growth
    }


if __name__ == "__main__":
    t_res = run_trend_analysis()
    print("Trend Analysis Complete.")
    print("Tier Step-up:", t_res["tier_stepup_rates"])
    print("Top Season Trends:", t_res["seasonal_trends"][:3])
