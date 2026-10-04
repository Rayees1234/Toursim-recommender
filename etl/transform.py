"""
ETL Module: Transform
Transforms cleaned data into Star Schema entities, surrogate keys, bridge tables,
and reconciled fact rows with referential integrity.
"""

from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def transform_to_star_schema(cleaned_records):
    logger.info(f"Transforming {len(cleaned_records)} cleaned records into Star Schema...")

    # 1. Dimension: Date
    # Parse last_updated dates and pre-populate Unknown member
    date_lookup = {}
    dim_date_rows = [
        {
            "date_key": 0,
            "full_date": "1900-01-01",
            "year": 1900,
            "quarter": 0,
            "month": 0,
            "month_name": "Unknown",
            "day": 0,
            "day_of_week": "Unknown",
            "is_weekend": 0,
            "season_name": "Unknown"
        }
    ]
    
    unique_dates = sorted(list(set(r.get("last_updated", "2026-01-12") for r in cleaned_records)))
    for d_str in unique_dates:
        dt = datetime.strptime(d_str, "%Y-%m-%d")
        d_key = int(dt.strftime("%Y%m%d"))
        q = (dt.month - 1) // 3 + 1
        # Season based on Northern Hemisphere month
        if dt.month in (12, 1, 2):
            seas = "Winter"
        elif dt.month in (3, 4, 5):
            seas = "Summer"
        elif dt.month in (6, 7, 8, 9):
            seas = "Monsoon"
        else:
            seas = "Post-Monsoon"

        date_lookup[d_str] = d_key
        dim_date_rows.append({
            "date_key": d_key,
            "full_date": d_str,
            "year": dt.year,
            "quarter": q,
            "month": dt.month,
            "month_name": dt.strftime("%B"),
            "day": dt.day,
            "day_of_week": dt.strftime("%A"),
            "is_weekend": 1 if dt.weekday() >= 5 else 0,
            "season_name": seas
        })

    # 2. Dimension: Geography
    geography_lookup = {}
    dim_geography_rows = [
        {
            "geography_key": 0,
            "country": "India",
            "region": "Unknown",
            "state": "Unknown",
            "district": "Unknown"
        }
    ]
    geo_counter = 1

    # 3. Dimension: Connectivity
    connectivity_lookup = {}
    dim_connectivity_rows = [
        {
            "connectivity_key": 0,
            "accessibility": "Unknown",
            "road_connectivity": "Unknown",
            "atm_availability": "Unknown",
            "internet_connectivity": "Unknown",
            "has_railway_access": 0,
            "nearest_airport_name": "Unknown",
            "nearest_railway_name": "Unknown",
            "nearest_city_name": "Unknown"
        }
    ]
    conn_counter = 1

    # 4. Dimension: Seasonality
    seasonality_lookup = {}
    dim_seasonality_rows = [
        {
            "seasonality_key": 0,
            "peak_tourist_season": "Unknown",
            "off_season": "Unknown",
            "rainfall_pattern": "Unknown",
            "winter_temp_desc": "Unknown",
            "summer_temp_desc": "Unknown",
            "monsoon_temp_desc": "Unknown"
        }
    ]
    season_counter = 1

    # 5. Multi-Valued Attributes Collectors
    trip_type_set = set()
    activity_set = set()
    accom_set = set()
    season_set = set()

    # Pre-scan for multi-valued dimensions
    for r in cleaned_records:
        for t in r.get("trip_types", []):
            if t:
                trip_type_set.add(t)
        for a in r.get("activities_available", []):
            if a:
                activity_set.add(a)
        for acc in r.get("accommodation_types", []):
            if acc:
                accom_set.add(acc)
        for s in r.get("best_seasons", []):
            if s:
                season_set.add(s)
        for s in r.get("avoid_seasons", []):
            if s:
                season_set.add(s)

    # Build Bridge Master Dimensions
    trip_type_lookup = {name: idx + 1 for idx, name in enumerate(sorted(list(trip_type_set)))}
    dim_trip_type_rows = [{"trip_type_key": k, "trip_type_name": v} for v, k in trip_type_lookup.items()]

    activity_lookup = {name: idx + 1 for idx, name in enumerate(sorted(list(activity_set)))}
    dim_activity_rows = [{"activity_key": k, "activity_name": v} for v, k in activity_lookup.items()]

    accom_lookup = {name: idx + 1 for idx, name in enumerate(sorted(list(accom_set)))}
    dim_accom_rows = [{"accommodation_key": k, "accommodation_name": v} for v, k in accom_lookup.items()]

    season_lookup = {name: idx + 1 for idx, name in enumerate(sorted(list(season_set)))}
    dim_season_rows = [{"season_key": k, "season_name": v} for v, k in season_lookup.items()]

    # 6. Build Destination Dimension, Fact Rows, and Bridge Rows
    dim_destination_rows = [
        {
            "destination_key": 0,
            "natural_id": 0,
            "destination_name": "Unknown Destination",
            "latitude": 0.0,
            "longitude": 0.0,
            "food_scene": "",
            "local_culture": "",
            "local_customs": "",
            "festivals_events": "",
            "unique_experiences": "",
            "permits_required": 0,
            "permits_details": "None"
        }
    ]

    fact_destination_rows = []
    bridge_trip_rows = []
    bridge_act_rows = []
    bridge_accom_rows = []
    bridge_season_rows = []

    for r in cleaned_records:
        dest_key = r["id"]  # 1 to 100
        
        # Dim Destination
        dim_destination_rows.append({
            "destination_key": dest_key,
            "natural_id": r["id"],
            "destination_name": r["destination_name"],
            "latitude": r["latitude"],
            "longitude": r["longitude"],
            "food_scene": r["food_scene"],
            "local_culture": r["local_culture"],
            "local_customs": r["local_customs"],
            "festivals_events": r["festivals_events"],
            "unique_experiences": r["unique_experiences"],
            "permits_required": r["permits_required"],
            "permits_details": r["permits_details"]
        })

        # Dim Geography
        geo_tuple = (r["region"], r["state"], r["district"])
        if geo_tuple not in geography_lookup:
            geography_lookup[geo_tuple] = geo_counter
            dim_geography_rows.append({
                "geography_key": geo_counter,
                "country": "India",
                "region": r["region"],
                "state": r["state"],
                "district": r["district"]
            })
            geo_counter += 1
        geog_key = geography_lookup[geo_tuple]

        # Dim Connectivity
        conn_tuple = (
            r["accessibility"],
            r["road_connectivity"],
            r["atm_availability"],
            r["internet_connectivity"],
            r["has_railway_access"],
            r["nearest_airport_name"],
            r["nearest_railway_name"],
            r["nearest_city_name"]
        )
        if conn_tuple not in connectivity_lookup:
            connectivity_lookup[conn_tuple] = conn_counter
            dim_connectivity_rows.append({
                "connectivity_key": conn_counter,
                "accessibility": r["accessibility"],
                "road_connectivity": r["road_connectivity"],
                "atm_availability": r["atm_availability"],
                "internet_connectivity": r["internet_connectivity"],
                "has_railway_access": r["has_railway_access"],
                "nearest_airport_name": r["nearest_airport_name"],
                "nearest_railway_name": r["nearest_railway_name"],
                "nearest_city_name": r["nearest_city_name"]
            })
            conn_counter += 1
        conn_key = connectivity_lookup[conn_tuple]

        # Dim Seasonality
        seas_tuple = (
            r["peak_tourist_season"],
            r["off_season"],
            r["rainfall_pattern"],
            r["winter_temp_desc"],
            r["summer_temp_desc"],
            r["monsoon_temp_desc"]
        )
        if seas_tuple not in seasonality_lookup:
            seasonality_lookup[seas_tuple] = season_counter
            dim_seasonality_rows.append({
                "seasonality_key": season_counter,
                "peak_tourist_season": r["peak_tourist_season"],
                "off_season": r["off_season"],
                "rainfall_pattern": r["rainfall_pattern"],
                "winter_temp_desc": r["winter_temp_desc"],
                "summer_temp_desc": r["summer_temp_desc"],
                "monsoon_temp_desc": r["monsoon_temp_desc"]
            })
            season_counter += 1
        seas_key = seasonality_lookup[seas_tuple]

        # Fact Row
        fact_destination_rows.append({
            "fact_id": dest_key,
            "date_key": date_lookup.get(r.get("last_updated", "2026-01-12"), 20260112),
            "destination_key": dest_key,
            "geography_key": geog_key,
            "connectivity_key": conn_key,
            "seasonality_key": seas_key,
            "min_duration_days": r["minimum_days"],
            "ideal_duration_days": r["ideal_days"],
            "max_duration_days": r["maximum_days"],
            "altitude_m": r["altitude_m"],
            "popularity_score": r["popularity_score"],
            "safety_rating": r["safety_rating"],
            "airport_distance_km": r["airport_distance_km"],
            "railway_distance_km": r["railway_distance_km"],
            "city_distance_km": r["city_distance_km"],
            "budget_accom_min": r["budget_accom_min"],
            "budget_accom_max": r["budget_accom_max"],
            "budget_accom_avg": r["budget_accom_avg"],
            "budget_food_min": r["budget_food_min"],
            "budget_food_max": r["budget_food_max"],
            "budget_food_avg": r["budget_food_avg"],
            "budget_act_min": r["budget_act_min"],
            "budget_act_max": r["budget_act_max"],
            "budget_act_avg": r["budget_act_avg"],
            "budget_trans_min": r["budget_trans_min"],
            "budget_trans_max": r["budget_trans_max"],
            "budget_trans_avg": r["budget_trans_avg"],
            "budget_daily_min": r["budget_daily_min"],
            "budget_daily_max": r["budget_daily_max"],
            "budget_daily_avg": r["budget_daily_avg"],
            "mid_accom_min": r["mid_accom_min"],
            "mid_accom_max": r["mid_accom_max"],
            "mid_accom_avg": r["mid_accom_avg"],
            "mid_food_min": r["mid_food_min"],
            "mid_food_max": r["mid_food_max"],
            "mid_food_avg": r["mid_food_avg"],
            "mid_act_min": r["mid_act_min"],
            "mid_act_max": r["mid_act_max"],
            "mid_act_avg": r["mid_act_avg"],
            "mid_trans_min": r["mid_trans_min"],
            "mid_trans_max": r["mid_trans_max"],
            "mid_trans_avg": r["mid_trans_avg"],
            "mid_daily_min": r["mid_daily_min"],
            "mid_daily_max": r["mid_daily_max"],
            "mid_daily_avg": r["mid_daily_avg"],
            "luxury_accom_min": r["luxury_accom_min"],
            "luxury_accom_max": r["luxury_accom_max"],
            "luxury_accom_avg": r["luxury_accom_avg"],
            "luxury_food_min": r["luxury_food_min"],
            "luxury_food_max": r["luxury_food_max"],
            "luxury_food_avg": r["luxury_food_avg"],
            "luxury_act_min": r["luxury_act_min"],
            "luxury_act_max": r["luxury_act_max"],
            "luxury_act_avg": r["luxury_act_avg"],
            "luxury_trans_min": r["luxury_trans_min"],
            "luxury_trans_max": r["luxury_trans_max"],
            "luxury_trans_avg": r["luxury_trans_avg"],
            "luxury_daily_min": r["luxury_daily_min"],
            "luxury_daily_max": r["luxury_daily_max"],
            "luxury_daily_avg": r["luxury_daily_avg"],
            "total_estimated_trip_cost_mid": r["total_estimated_trip_cost_mid"]
        })

        # Bridges
        for t in r.get("trip_types", []):
            if t in trip_type_lookup:
                bridge_trip_rows.append({"destination_key": dest_key, "trip_type_key": trip_type_lookup[t]})

        for a in r.get("activities_available", []):
            if a in activity_lookup:
                bridge_act_rows.append({"destination_key": dest_key, "activity_key": activity_lookup[a]})

        for acc in r.get("accommodation_types", []):
            if acc in accom_lookup:
                bridge_accom_rows.append({"destination_key": dest_key, "accommodation_key": accom_lookup[acc]})

        for s in r.get("best_seasons", []):
            if s in season_lookup:
                bridge_season_rows.append({"destination_key": dest_key, "season_key": season_lookup[s], "season_type": "best"})

        for s in r.get("avoid_seasons", []):
            if s in season_lookup:
                bridge_season_rows.append({"destination_key": dest_key, "season_key": season_lookup[s], "season_type": "avoid"})

    transformed_data = {
        "dim_date": dim_date_rows,
        "dim_geography": dim_geography_rows,
        "dim_destination": dim_destination_rows,
        "dim_connectivity": dim_connectivity_rows,
        "dim_seasonality": dim_seasonality_rows,
        "dim_trip_type": dim_trip_type_rows,
        "bridge_destination_trip_type": bridge_trip_rows,
        "dim_activity": dim_activity_rows,
        "bridge_destination_activity": bridge_act_rows,
        "dim_accommodation": dim_accom_rows,
        "bridge_destination_accommodation": bridge_accom_rows,
        "dim_season": dim_season_rows,
        "bridge_destination_season": bridge_season_rows,
        "fact_destination_metrics": fact_destination_rows
    }

    logger.info(
        f"Transformation Complete: Fact rows={len(fact_destination_rows)}, "
        f"Destinations={len(dim_destination_rows)-1}, Geographies={len(dim_geography_rows)-1}, "
        f"Trip Bridges={len(bridge_trip_rows)}, Activity Bridges={len(bridge_act_rows)}."
    )
    return transformed_data


if __name__ == "__main__":
    from extract import extract_raw_data
    from clean import clean_destination_records
    raw = extract_raw_data()
    clean, _ = clean_destination_records(raw)
    td = transform_to_star_schema(clean)
    print("Transform test successful.")
