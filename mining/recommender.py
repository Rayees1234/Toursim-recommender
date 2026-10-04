"""
Data Mining Module: Personalized Destination Recommender
Content-based and popularity-weighted recommendation engine filtering on budget,
duration, seasonality, and trip type preferences.
"""

import os
import sys
import logging
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sql.database import db

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def recommend_destinations(budget_max=6000, duration_days=4, region=None, trip_type=None, season=None, top_n=5):
    logger.info(f"Generating recommendations (budget={budget_max}, duration={duration_days}, region={region}, type={trip_type})...")

    # 1. Base Query with Joined Dimensions
    query = """
        SELECT 
            f.destination_key,
            d.destination_name,
            g.region,
            g.state,
            c.accessibility,
            f.mid_daily_avg,
            f.budget_daily_avg,
            f.ideal_duration_days,
            f.min_duration_days,
            f.max_duration_days,
            f.popularity_score,
            f.safety_rating,
            d.unique_experiences,
            d.food_scene
        FROM fact_destination_metrics f
        JOIN dim_destination d ON f.destination_key = d.destination_key
        JOIN dim_geography g ON f.geography_key = g.geography_key
        JOIN dim_connectivity c ON f.connectivity_key = c.connectivity_key
        WHERE f.mid_daily_avg <= %s
    """
    params = [float(budget_max)]
    
    if region and region != "All":
        query += " AND g.region = %s"
        params.append(region)

    rows = db.fetch_all(query, tuple(params))
    if not rows:
        # Fallback to nearest budget if no strict match
        return {
            "query": {"budget": budget_max, "duration": duration_days, "region": region, "type": trip_type},
            "recommendations": [],
            "message": f"No destinations found within daily budget of ₹{budget_max:,.0f}. Try increasing budget limit."
        }

    # 2. Fetch Trip Types and Best Seasons for candidate destinations
    dest_keys = [r["destination_key"] for r in rows]
    key_placeholders = ", ".join(["%s"] * len(dest_keys))
    
    trip_q = f"""
        SELECT b.destination_key, t.trip_type_name
        FROM bridge_destination_trip_type b
        JOIN dim_trip_type t ON b.trip_type_key = t.trip_type_key
        WHERE b.destination_key IN ({key_placeholders})
    """
    trip_rows = db.fetch_all(trip_q, tuple(dest_keys))
    dest_trips = {}
    for tr in trip_rows:
        dk = tr["destination_key"]
        dest_trips.setdefault(dk, set()).add(tr["trip_type_name"].lower())

    seas_q = f"""
        SELECT b.destination_key, s.season_name
        FROM bridge_destination_season b
        JOIN dim_season s ON b.season_key = s.season_key
        WHERE b.season_type = 'best' AND b.destination_key IN ({key_placeholders})
    """
    seas_rows = db.fetch_all(seas_q, tuple(dest_keys))
    dest_seasons = {}
    for sr in seas_rows:
        dk = sr["destination_key"]
        dest_seasons.setdefault(dk, set()).add(sr["season_name"].lower())

    # 3. Scoring Matrix
    scored_candidates = []
    for r in rows:
        dk = r["destination_key"]
        score = 0.0
        match_reasons = []

        # Duration match (Gaussian proximity penalty)
        ideal_d = float(r["ideal_duration_days"])
        dur_diff = abs(ideal_d - float(duration_days))
        dur_score = max(0, 30.0 - (dur_diff * 6.0))
        score += dur_score
        if dur_diff <= 1.0:
            match_reasons.append(f"Ideal duration ({ideal_d:.0f} days) aligns with your {duration_days}-day itinerary.")

        # Budget match (more value if below budget)
        mid_spend = float(r["mid_daily_avg"])
        budget_ratio = (float(budget_max) - mid_spend) / float(budget_max)
        score += max(0, budget_ratio * 20.0)
        match_reasons.append(f"Comfortably within budget at ₹{mid_spend:,.0f}/day.")

        # Trip type match
        if trip_type and trip_type.lower() != "any":
            user_type = trip_type.lower()
            if dk in dest_trips and any(user_type in t for t in dest_trips[dk]):
                score += 35.0
                match_reasons.append(f"Features your requested '{trip_type}' travel experience.")

        # Season match
        if season and season.lower() != "any":
            user_seas = season.lower()
            if dk in dest_seasons and any(user_seas in s for s in dest_seasons[dk]):
                score += 25.0
                match_reasons.append(f"Optimal visiting season is {season}.")

        # Popularity and safety weighting
        score += float(r["popularity_score"]) * 2.0
        score += float(r["safety_rating"]) * 2.0

        r_dict = dict(r)
        r_dict["match_score"] = round(min(100.0, score), 1)
        r_dict["match_reasons"] = match_reasons
        scored_candidates.append(r_dict)

    scored_candidates.sort(key=lambda x: x["match_score"], reverse=True)
    top_matches = scored_candidates[:top_n]

    return {
        "query": {
            "budget_max": budget_max,
            "duration_days": duration_days,
            "region": region or "All",
            "trip_type": trip_type or "Any",
            "season": season or "Any"
        },
        "total_matches_found": len(scored_candidates),
        "recommendations": top_matches
    }


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    rec = recommend_destinations(budget_max=5000, duration_days=3, trip_type="Beach", season="Winter")
    print(f"Found {len(rec['recommendations'])} recommendations.")
    for d in rec["recommendations"]:
        print(f"-> {d['destination_name']} ({d['region']}) - Score: {d['match_score']}% | Spend: INR {d['mid_daily_avg']:,.0f}/day")
        print(f"   Reasons: {d['match_reasons']}")
