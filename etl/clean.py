"""
ETL Module: Clean
Applies data quality transformations, text sanitization, category standardization,
imputation, and integrity constraints without dropping valid records.
"""

import json
import re
import os
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Regular expressions for cleaning
CITATION_REGEX = re.compile(r"\[web:\d+\]", re.IGNORECASE)
TEMP_EXTRACT_REGEX = re.compile(r"(-?\d+)\s*(?:to|-|–|—)\s*(-?\d+)", re.UNICODE)


def sanitize_text(text):
    if not isinstance(text, str):
        return text
    # Remove citation tags like [web:123]
    cleaned = CITATION_REGEX.sub("", text)
    # Replace non-breaking / non-ascii dashes and spaces
    cleaned = cleaned.replace("\u2011", "-").replace("\u2013", "-").replace("\u2014", "-")
    cleaned = cleaned.replace("\u00a0", " ")
    cleaned = cleaned.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")
    # Collapse multiple spaces and strip
    cleaned = re.sub(r"[ \t]+", " ", cleaned).strip()
    return cleaned


def standardize_region(region_raw):
    region_clean = sanitize_text(region_raw)
    mapping = {
        "North East India": "Northeast India",
        "Northeast India": "Northeast India",
        "North India": "North India",
        "South India": "South India",
        "West India": "West India",
        "East India": "East India",
        "Central India": "Central India",
        "Island Territory": "Island Territory",
        "Multi-state": "Multi-state",
    }
    return mapping.get(region_clean, region_clean)


def parse_temperature_range(temp_str):
    if not temp_str or "data_not_available" in str(temp_str).lower():
        return {"raw_desc": "Data Not Available", "min_c": None, "max_c": None, "avg_c": None}
    
    clean_str = sanitize_text(str(temp_str))
    match = TEMP_EXTRACT_REGEX.search(clean_str)
    if match:
        t_min = float(match.group(1))
        t_max = float(match.group(2))
        return {
            "raw_desc": clean_str,
            "min_c": min(t_min, t_max),
            "max_c": max(t_min, t_max),
            "avg_c": round((t_min + t_max) / 2.0, 1)
        }
    return {"raw_desc": clean_str, "min_c": None, "max_c": None, "avg_c": None}


def clean_destination_records(raw_records):
    logger.info(f"Beginning data cleaning for {len(raw_records)} records...")
    cleaned_records = []
    
    stats = {
        "total_input": len(raw_records),
        "citations_removed": 0,
        "islands_imputed": 0,
        "regions_standardized": 0,
        "valid_records_retained": 0,
        "dropped_records": 0
    }

    for record in raw_records:
        rec = {}
        # 1. Primary Identifiers
        rec["id"] = int(record["id"])
        rec["destination_name"] = sanitize_text(record["destination_name"])
        
        # 2. Geography
        raw_reg = record.get("region", "")
        std_reg = standardize_region(raw_reg)
        if std_reg != raw_reg:
            stats["regions_standardized"] += 1
        rec["region"] = std_reg
        rec["state"] = sanitize_text(record.get("state", "Unknown"))
        rec["district"] = sanitize_text(record.get("district", "Unknown"))
        
        # Coordinates
        coords = record.get("coordinates", {})
        rec["latitude"] = float(coords.get("latitude", 0.0))
        rec["longitude"] = float(coords.get("longitude", 0.0))
        rec["altitude_m"] = int(record.get("altitude_m", 0))

        # 3. Connectivity & Transport
        rec["accessibility"] = sanitize_text(record.get("accessibility", "Moderate"))
        rec["road_connectivity"] = sanitize_text(record.get("road_connectivity", "Good"))
        rec["atm_availability"] = sanitize_text(record.get("atm_availability", "Standard"))
        rec["internet_connectivity"] = sanitize_text(record.get("internet_connectivity", "Standard"))
        
        airport = record.get("nearest_airport", {})
        rec["nearest_airport_name"] = sanitize_text(airport.get("name", "Unknown"))
        rec["airport_distance_km"] = int(airport.get("distance_km", 0))

        railway = record.get("nearest_railway_station", {})
        raw_rail_dist = railway.get("distance_km")
        if raw_rail_dist is None or str(railway.get("name", "")).lower().startswith("none"):
            rec["has_railway_access"] = 0
            rec["railway_distance_km"] = -1
            rec["nearest_railway_name"] = "No Railway Network (Island Territory)"
            stats["islands_imputed"] += 1
        else:
            rec["has_railway_access"] = 1
            rec["railway_distance_km"] = int(raw_rail_dist)
            rec["nearest_railway_name"] = sanitize_text(railway.get("name", "Unknown"))

        city = record.get("nearest_major_city", {})
        rec["nearest_city_name"] = sanitize_text(city.get("name", "Unknown"))
        rec["city_distance_km"] = int(city.get("distance_km", 0))

        # 4. Durations
        rec["minimum_days"] = float(record.get("minimum_days", 1.0))
        rec["ideal_days"] = float(record.get("ideal_days", 2.0))
        rec["maximum_days"] = int(record.get("maximum_days", 3))

        # 5. Ratings & Scores
        rec["popularity_score"] = int(record.get("popularity_score", 5))
        rec["safety_rating"] = int(record.get("safety_rating", 5))
        rec["permits_required"] = 1 if record.get("permits_required") else 0
        rec["permits_details"] = sanitize_text(record.get("permits_details", "Not required"))

        # 6. Budget Tiers & Category Breakdowns
        tiers = [
            ("budget_category", "budget"),
            ("mid_range_category", "mid"),
            ("luxury_category", "luxury")
        ]
        
        for raw_tier_key, prefix in tiers:
            tier_dict = record.get(raw_tier_key, {})
            # Accommodation
            accom = tier_dict.get("accommodation_range", [0, 0])
            rec[f"{prefix}_accom_min"] = float(accom[0])
            rec[f"{prefix}_accom_max"] = float(accom[1])
            rec[f"{prefix}_accom_avg"] = round((accom[0] + accom[1]) / 2.0, 2)
            
            # Food
            food = tier_dict.get("food_range", [0, 0])
            rec[f"{prefix}_food_min"] = float(food[0])
            rec[f"{prefix}_food_max"] = float(food[1])
            rec[f"{prefix}_food_avg"] = round((food[0] + food[1]) / 2.0, 2)
            
            # Activities
            act = tier_dict.get("activities_range", [0, 0])
            rec[f"{prefix}_act_min"] = float(act[0])
            rec[f"{prefix}_act_max"] = float(act[1])
            rec[f"{prefix}_act_avg"] = round((act[0] + act[1]) / 2.0, 2)
            
            # Local Transport
            trans = tier_dict.get("local_transport_range", [0, 0])
            rec[f"{prefix}_trans_min"] = float(trans[0])
            rec[f"{prefix}_trans_max"] = float(trans[1])
            rec[f"{prefix}_trans_avg"] = round((trans[0] + trans[1]) / 2.0, 2)
            
            # Total Daily Spend
            daily = tier_dict.get("total_daily_range", [0, 0])
            rec[f"{prefix}_daily_min"] = float(daily[0])
            rec[f"{prefix}_daily_max"] = float(daily[1])
            rec[f"{prefix}_daily_avg"] = round((daily[0] + daily[1]) / 2.0, 2)

        # Derived Total Trip Spend (Mid-Range)
        rec["total_estimated_trip_cost_mid"] = round(rec["ideal_days"] * rec["mid_daily_avg"], 2)

        # 7. Seasonality & Temperatures
        rec["peak_tourist_season"] = sanitize_text(record.get("peak_tourist_season", ""))
        rec["off_season"] = sanitize_text(record.get("off_season", ""))
        rec["rainfall_pattern"] = sanitize_text(record.get("rainfall_pattern", ""))

        temp_dict = record.get("average_temperature", {})
        rec["winter_temp_parsed"] = parse_temperature_range(temp_dict.get("winter"))
        rec["summer_temp_parsed"] = parse_temperature_range(temp_dict.get("summer"))
        rec["monsoon_temp_parsed"] = parse_temperature_range(temp_dict.get("monsoon"))
        
        rec["winter_temp_desc"] = rec["winter_temp_parsed"]["raw_desc"]
        rec["summer_temp_desc"] = rec["summer_temp_parsed"]["raw_desc"]
        rec["monsoon_temp_desc"] = rec["monsoon_temp_parsed"]["raw_desc"]

        # 8. Descriptive Context
        rec["food_scene"] = sanitize_text(record.get("food_scene", ""))
        rec["local_culture"] = sanitize_text(record.get("local_culture", ""))
        rec["local_customs"] = sanitize_text(record.get("local_customs", ""))
        rec["festivals_events"] = sanitize_text(record.get("festivals_events", ""))
        rec["unique_experiences"] = sanitize_text(record.get("unique_experiences", ""))

        # 9. Multi-Valued Attributes (Arrays cleaned)
        rec["trip_types"] = [sanitize_text(t) for t in record.get("trip_types", []) if t]
        rec["activities_available"] = [sanitize_text(a) for a in record.get("activities_available", []) if a]
        rec["accommodation_types"] = [sanitize_text(acc) for acc in record.get("accommodation_types", []) if acc]
        rec["best_seasons"] = [sanitize_text(s) for s in record.get("best_seasons", []) if s]
        rec["avoid_seasons"] = [sanitize_text(s) for s in record.get("avoid_seasons", []) if s]
        rec["ideal_for"] = [sanitize_text(i) for i in record.get("ideal_for", []) if i]

        # 10. Snapshot Date
        rec["last_updated"] = record.get("last_updated", "2026-01-12")

        cleaned_records.append(rec)
        stats["valid_records_retained"] += 1

    logger.info(
        f"Cleaning Complete: {stats['valid_records_retained']}/{stats['total_input']} retained. "
        f"{stats['islands_imputed']} islands handled, {stats['regions_standardized']} regions canonicalized."
    )
    
    # Save cleaned JSON
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_dir = os.path.join(base_dir, "data", "processed")
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, "cleaned_tourism_data.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(cleaned_records, f, indent=2, ensure_ascii=False)
    logger.info(f"Cleaned data persisted to: {output_file}")

    return cleaned_records, stats


if __name__ == "__main__":
    from extract import extract_raw_data
    raw = extract_raw_data()
    clean, st = clean_destination_records(raw)
    print(f"Cleaned {len(clean)} records successfully. Stats: {st}")
