# Tourism Data Warehouse Star Schema Architecture

**Project**: Tourism Data Warehouse and Data Mining System (DMDW)  
**Schema Model**: Star Schema with Normalized Multi-Valued Bridge Outriggers  
**Target RDBMS**: MySQL 8.0 / SQLite Dual-Engine

---

## 1. Dimensional Architecture Overview

```mermaid
erDiagram
    dim_date ||--o{ fact_destination_metrics : "records date"
    dim_destination ||--o{ fact_destination_metrics : "measures destination"
    dim_geography ||--o{ fact_destination_metrics : "locates destination"
    dim_connectivity ||--o{ fact_destination_metrics : "measures access"
    dim_seasonality ||--o{ fact_destination_metrics : "defines climate"

    dim_destination ||--o{ bridge_destination_trip_type : "has"
    dim_trip_type ||--o{ bridge_destination_trip_type : "classified by"

    dim_destination ||--o{ bridge_destination_activity : "offers"
    dim_activity ||--o{ bridge_destination_activity : "experienced as"

    dim_destination ||--o{ bridge_destination_accommodation : "provides"
    dim_accommodation ||--o{ bridge_destination_accommodation : "lodging type"

    dim_destination ||--o{ bridge_destination_season : "suitable for"
    dim_season ||--o{ bridge_destination_season : "seasonal cycle"

    fact_destination_metrics {
        int fact_id PK
        int date_key FK
        int destination_key FK
        int geography_key FK
        int connectivity_key FK
        int seasonality_key FK
        decimal min_duration_days
        decimal ideal_duration_days
        int max_duration_days
        int altitude_m
        int popularity_score
        int safety_rating
        int airport_distance_km
        int railway_distance_km
        int city_distance_km
        decimal budget_daily_avg
        decimal mid_daily_avg
        decimal luxury_daily_avg
        decimal total_estimated_trip_cost_mid
    }

    dim_date {
        int date_key PK
        date full_date
        int year
        int quarter
        int month
        string month_name
        int day
        string day_of_week
        string season_name
    }

    dim_geography {
        int geography_key PK
        string country
        string region
        string state
        string district
    }

    dim_destination {
        int destination_key PK
        int natural_id
        string destination_name
        decimal latitude
        decimal longitude
        int permits_required
        string permits_details
    }

    dim_connectivity {
        int connectivity_key PK
        string accessibility
        string road_connectivity
        string atm_availability
        string internet_connectivity
        int has_railway_access
        string nearest_airport_name
        string nearest_railway_name
        string nearest_city_name
    }

    dim_seasonality {
        int seasonality_key PK
        string peak_tourist_season
        string off_season
        string rainfall_pattern
        string winter_temp_desc
        string summer_temp_desc
    }
```

---

## 2. Dimension Hierarchies

1. **Geography Hierarchy**:
   `Country (India)` $\longrightarrow$ `Region (7 Zones)` $\longrightarrow$ `State (30 States/UTs)` $\longrightarrow$ `District` $\longrightarrow$ `Destination`

2. **Temporal Calendar Hierarchy**:
   `Year (2026)` $\longrightarrow$ `Quarter (Q1)` $\longrightarrow$ `Month (January)` $\longrightarrow$ `Day (12)`

3. **Accessibility & Infrastructure Hierarchy**:
   `Accessibility Level (Easy / Moderate / Difficult)` $\longrightarrow$ `Railway Access (Direct Rail / Island Route)` $\longrightarrow$ `Destination`

4. **Expenditure Tier Breakdown Hierarchy**:
   `Budget Tier (Budget / Mid-Range / Luxury)` $\longrightarrow$ `Expense Category (Accommodation / Food / Activities / Transport)` $\longrightarrow$ `Daily Amount (INR ₹)`

---

## 3. Grain & Integrity Specification

- **Primary Fact Grain**: Exactly one row per verified destination entity snapshot (100 rows).
- **Referential Integrity**: Every fact row links to valid non-null dimension records. Missing attributes map to `Unknown` dimension members with surrogate key `0`.
- **Zero Orphan Guarantee**: Foreign keys are enforced with relational constraints (`REFERENCES`).
- **Idempotency**: Schema DDL and loading scripts can be executed repeatedly without generating duplicate surrogate keys or fact records.
