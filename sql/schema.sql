-- =====================================================================
-- Tourism Data Warehouse Star Schema (DDL)
-- Database: MySQL 8.0 (Compatible with SQLite3 fallback)
-- Author: Data Engineering & Data Science Team
-- Project: Tourism Data Warehouse and Data Mining System (DMDW)
-- =====================================================================

-- Drop existing tables in dependency order if recreating
DROP VIEW IF EXISTS vw_fact_destination_tier_spend;
DROP VIEW IF EXISTS vw_star_destination_full;
DROP TABLE IF EXISTS mining_trends;
DROP TABLE IF EXISTS mining_outliers;
DROP TABLE IF EXISTS mining_classification_metrics;
DROP TABLE IF EXISTS mining_rules;
DROP TABLE IF EXISTS mining_cluster_assignments;
DROP TABLE IF EXISTS mining_clusters;
DROP TABLE IF EXISTS bridge_destination_season;
DROP TABLE IF EXISTS bridge_destination_accommodation;
DROP TABLE IF EXISTS bridge_destination_activity;
DROP TABLE IF EXISTS bridge_destination_trip_type;
DROP TABLE IF EXISTS dim_season;
DROP TABLE IF EXISTS dim_accommodation;
DROP TABLE IF EXISTS dim_activity;
DROP TABLE IF EXISTS dim_trip_type;
DROP TABLE IF EXISTS fact_destination_metrics;
DROP TABLE IF EXISTS dim_seasonality;
DROP TABLE IF EXISTS dim_connectivity;
DROP TABLE IF EXISTS dim_geography;
DROP TABLE IF EXISTS dim_destination;
DROP TABLE IF EXISTS dim_date;

-- ---------------------------------------------------------------------
-- 1. Dimension: Date (Calendar Dimension)
-- Hierarchy: Year -> Quarter -> Month -> Day
-- ---------------------------------------------------------------------
CREATE TABLE dim_date (
    date_key INT PRIMARY KEY,                       -- Format: YYYYMMDD (e.g., 20260112)
    full_date DATE NOT NULL,
    year INT NOT NULL,
    quarter INT NOT NULL,
    month INT NOT NULL,
    month_name VARCHAR(20) NOT NULL,
    day INT NOT NULL,
    day_of_week VARCHAR(20) NOT NULL,
    is_weekend TINYINT(1) DEFAULT 0,
    season_name VARCHAR(50) NOT NULL
);

-- ---------------------------------------------------------------------
-- 2. Dimension: Geography
-- Hierarchy: Country -> Region -> State -> District
-- ---------------------------------------------------------------------
CREATE TABLE dim_geography (
    geography_key INT PRIMARY KEY,
    country VARCHAR(50) NOT NULL DEFAULT 'India',
    region VARCHAR(50) NOT NULL,
    state VARCHAR(100) NOT NULL,
    district VARCHAR(150) NOT NULL
);

CREATE INDEX idx_geography_hierarchy ON dim_geography(region, state, district);

-- ---------------------------------------------------------------------
-- 3. Dimension: Destination (Core Descriptive Entity)
-- ---------------------------------------------------------------------
CREATE TABLE dim_destination (
    destination_key INT PRIMARY KEY,
    natural_id INT NOT NULL,
    destination_name VARCHAR(150) NOT NULL,
    latitude DECIMAL(9,6) NOT NULL,
    longitude DECIMAL(9,6) NOT NULL,
    food_scene TEXT,
    local_culture TEXT,
    local_customs TEXT,
    festivals_events TEXT,
    unique_experiences TEXT,
    permits_required TINYINT(1) DEFAULT 0,
    permits_details VARCHAR(255)
);

CREATE INDEX idx_destination_name ON dim_destination(destination_name);

-- ---------------------------------------------------------------------
-- 4. Dimension: Connectivity & Infrastructure
-- ---------------------------------------------------------------------
CREATE TABLE dim_connectivity (
    connectivity_key INT PRIMARY KEY,
    accessibility VARCHAR(50) NOT NULL,             -- Easy, Moderate, Difficult
    road_connectivity VARCHAR(255),
    atm_availability VARCHAR(255),
    internet_connectivity VARCHAR(255),
    has_railway_access TINYINT(1) DEFAULT 1,
    nearest_airport_name VARCHAR(150),
    nearest_railway_name VARCHAR(150),
    nearest_city_name VARCHAR(150)
);

CREATE INDEX idx_connectivity_access ON dim_connectivity(accessibility);

-- ---------------------------------------------------------------------
-- 5. Dimension: Seasonality Profile
-- ---------------------------------------------------------------------
CREATE TABLE dim_seasonality (
    seasonality_key INT PRIMARY KEY,
    peak_tourist_season VARCHAR(255),
    off_season VARCHAR(255),
    rainfall_pattern VARCHAR(255),
    winter_temp_desc VARCHAR(100),
    summer_temp_desc VARCHAR(100),
    monsoon_temp_desc VARCHAR(100)
);

-- ---------------------------------------------------------------------
-- 6. Fact Table: Destination Metrics (Primary Warehouse Grain)
-- Grain: One row per destination observation snapshot
-- ---------------------------------------------------------------------
CREATE TABLE fact_destination_metrics (
    fact_id INT PRIMARY KEY,
    date_key INT NOT NULL,
    destination_key INT NOT NULL,
    geography_key INT NOT NULL,
    connectivity_key INT NOT NULL,
    seasonality_key INT NOT NULL,
    
    -- Duration Measures (Days)
    min_duration_days DECIMAL(4,1) NOT NULL,
    ideal_duration_days DECIMAL(4,1) NOT NULL,
    max_duration_days INT NOT NULL,
    
    -- Physical & Evaluative Measures
    altitude_m INT NOT NULL,
    popularity_score INT NOT NULL,                  -- Scale: 1 - 10
    safety_rating INT NOT NULL,                     -- Scale: 1 - 10
    
    -- Infrastructure Proximity Measures (km)
    airport_distance_km INT NOT NULL,
    railway_distance_km INT NOT NULL,               -- -1 if island / no railway
    city_distance_km INT NOT NULL,
    
    -- Budget Tier Daily Spend Breakdown (INR)
    budget_accom_min DECIMAL(10,2) NOT NULL,
    budget_accom_max DECIMAL(10,2) NOT NULL,
    budget_accom_avg DECIMAL(10,2) NOT NULL,
    budget_food_min DECIMAL(10,2) NOT NULL,
    budget_food_max DECIMAL(10,2) NOT NULL,
    budget_food_avg DECIMAL(10,2) NOT NULL,
    budget_act_min DECIMAL(10,2) NOT NULL,
    budget_act_max DECIMAL(10,2) NOT NULL,
    budget_act_avg DECIMAL(10,2) NOT NULL,
    budget_trans_min DECIMAL(10,2) NOT NULL,
    budget_trans_max DECIMAL(10,2) NOT NULL,
    budget_trans_avg DECIMAL(10,2) NOT NULL,
    budget_daily_min DECIMAL(10,2) NOT NULL,
    budget_daily_max DECIMAL(10,2) NOT NULL,
    budget_daily_avg DECIMAL(10,2) NOT NULL,
    
    -- Mid-Range Tier Daily Spend Breakdown (INR)
    mid_accom_min DECIMAL(10,2) NOT NULL,
    mid_accom_max DECIMAL(10,2) NOT NULL,
    mid_accom_avg DECIMAL(10,2) NOT NULL,
    mid_food_min DECIMAL(10,2) NOT NULL,
    mid_food_max DECIMAL(10,2) NOT NULL,
    mid_food_avg DECIMAL(10,2) NOT NULL,
    mid_act_min DECIMAL(10,2) NOT NULL,
    mid_act_max DECIMAL(10,2) NOT NULL,
    mid_act_avg DECIMAL(10,2) NOT NULL,
    mid_trans_min DECIMAL(10,2) NOT NULL,
    mid_trans_max DECIMAL(10,2) NOT NULL,
    mid_trans_avg DECIMAL(10,2) NOT NULL,
    mid_daily_min DECIMAL(10,2) NOT NULL,
    mid_daily_max DECIMAL(10,2) NOT NULL,
    mid_daily_avg DECIMAL(10,2) NOT NULL,
    
    -- Luxury Tier Daily Spend Breakdown (INR)
    luxury_accom_min DECIMAL(10,2) NOT NULL,
    luxury_accom_max DECIMAL(10,2) NOT NULL,
    luxury_accom_avg DECIMAL(10,2) NOT NULL,
    luxury_food_min DECIMAL(10,2) NOT NULL,
    luxury_food_max DECIMAL(10,2) NOT NULL,
    luxury_food_avg DECIMAL(10,2) NOT NULL,
    luxury_act_min DECIMAL(10,2) NOT NULL,
    luxury_act_max DECIMAL(10,2) NOT NULL,
    luxury_act_avg DECIMAL(10,2) NOT NULL,
    luxury_trans_min DECIMAL(10,2) NOT NULL,
    luxury_trans_max DECIMAL(10,2) NOT NULL,
    luxury_trans_avg DECIMAL(10,2) NOT NULL,
    luxury_daily_min DECIMAL(10,2) NOT NULL,
    luxury_daily_max DECIMAL(10,2) NOT NULL,
    luxury_daily_avg DECIMAL(10,2) NOT NULL,
    
    -- Derived Legitimate Total Trip Spend Measure (INR)
    total_estimated_trip_cost_mid DECIMAL(12,2) NOT NULL,
    
    CONSTRAINT fk_fact_date FOREIGN KEY (date_key) REFERENCES dim_date(date_key),
    CONSTRAINT fk_fact_dest FOREIGN KEY (destination_key) REFERENCES dim_destination(destination_key),
    CONSTRAINT fk_fact_geog FOREIGN KEY (geography_key) REFERENCES dim_geography(geography_key),
    CONSTRAINT fk_fact_conn FOREIGN KEY (connectivity_key) REFERENCES dim_connectivity(connectivity_key),
    CONSTRAINT fk_fact_seas FOREIGN KEY (seasonality_key) REFERENCES dim_seasonality(seasonality_key)
);

CREATE INDEX idx_fact_dest ON fact_destination_metrics(destination_key);
CREATE INDEX idx_fact_geog ON fact_destination_metrics(geography_key);
CREATE INDEX idx_fact_date ON fact_destination_metrics(date_key);

-- ---------------------------------------------------------------------
-- 7. Bridge & Outrigger Dimensions (Multi-Valued Attributes)
-- ---------------------------------------------------------------------
CREATE TABLE dim_trip_type (
    trip_type_key INT PRIMARY KEY,
    trip_type_name VARCHAR(100) UNIQUE NOT NULL
);

CREATE TABLE bridge_destination_trip_type (
    destination_key INT NOT NULL,
    trip_type_key INT NOT NULL,
    PRIMARY KEY (destination_key, trip_type_key),
    CONSTRAINT fk_bridge_trip_dest FOREIGN KEY (destination_key) REFERENCES dim_destination(destination_key),
    CONSTRAINT fk_bridge_trip_type FOREIGN KEY (trip_type_key) REFERENCES dim_trip_type(trip_type_key)
);

CREATE TABLE dim_activity (
    activity_key INT PRIMARY KEY,
    activity_name VARCHAR(150) UNIQUE NOT NULL
);

CREATE TABLE bridge_destination_activity (
    destination_key INT NOT NULL,
    activity_key INT NOT NULL,
    PRIMARY KEY (destination_key, activity_key),
    CONSTRAINT fk_bridge_act_dest FOREIGN KEY (destination_key) REFERENCES dim_destination(destination_key),
    CONSTRAINT fk_bridge_act_name FOREIGN KEY (activity_key) REFERENCES dim_activity(activity_key)
);

CREATE TABLE dim_accommodation (
    accommodation_key INT PRIMARY KEY,
    accommodation_name VARCHAR(100) UNIQUE NOT NULL
);

CREATE TABLE bridge_destination_accommodation (
    destination_key INT NOT NULL,
    accommodation_key INT NOT NULL,
    PRIMARY KEY (destination_key, accommodation_key),
    CONSTRAINT fk_bridge_acc_dest FOREIGN KEY (destination_key) REFERENCES dim_destination(destination_key),
    CONSTRAINT fk_bridge_acc_name FOREIGN KEY (accommodation_key) REFERENCES dim_accommodation(accommodation_key)
);

CREATE TABLE dim_season (
    season_key INT PRIMARY KEY,
    season_name VARCHAR(50) UNIQUE NOT NULL
);

CREATE TABLE bridge_destination_season (
    destination_key INT NOT NULL,
    season_key INT NOT NULL,
    season_type VARCHAR(20) NOT NULL,              -- 'best' or 'avoid'
    PRIMARY KEY (destination_key, season_key, season_type),
    CONSTRAINT fk_bridge_seas_dest FOREIGN KEY (destination_key) REFERENCES dim_destination(destination_key),
    CONSTRAINT fk_bridge_seas_name FOREIGN KEY (season_key) REFERENCES dim_season(season_key)
);

-- ---------------------------------------------------------------------
-- 8. Mining Storage Tables (Phase 5 Persistence for Instant Dashboards)
-- ---------------------------------------------------------------------
CREATE TABLE mining_clusters (
    cluster_id INT PRIMARY KEY,
    cluster_label VARCHAR(100) NOT NULL,
    centroid_mid_spend DECIMAL(10,2) NOT NULL,
    centroid_duration DECIMAL(4,1) NOT NULL,
    centroid_popularity DECIMAL(4,2) NOT NULL,
    centroid_safety DECIMAL(4,2) NOT NULL,
    centroid_altitude DECIMAL(8,1) NOT NULL,
    destination_count INT NOT NULL,
    summary_explanation TEXT NOT NULL
);

CREATE TABLE mining_cluster_assignments (
    destination_key INT PRIMARY KEY,
    cluster_id INT NOT NULL,
    distance_to_centroid DECIMAL(8,4) NOT NULL,
    CONSTRAINT fk_assign_dest FOREIGN KEY (destination_key) REFERENCES dim_destination(destination_key),
    CONSTRAINT fk_assign_cluster FOREIGN KEY (cluster_id) REFERENCES mining_clusters(cluster_id)
);

CREATE TABLE mining_rules (
    rule_id INT PRIMARY KEY,
    antecedents VARCHAR(255) NOT NULL,
    consequents VARCHAR(255) NOT NULL,
    support DECIMAL(6,4) NOT NULL,
    confidence DECIMAL(6,4) NOT NULL,
    lift DECIMAL(6,4) NOT NULL,
    plain_english_rule TEXT NOT NULL
);

CREATE TABLE mining_classification_metrics (
    model_name VARCHAR(100) PRIMARY KEY,
    accuracy DECIMAL(6,4) NOT NULL,
    precision_score DECIMAL(6,4) NOT NULL,
    recall_score DECIMAL(6,4) NOT NULL,
    f1_score DECIMAL(6,4) NOT NULL,
    confusion_matrix_json TEXT NOT NULL,
    feature_importance_json TEXT NOT NULL
);

CREATE TABLE mining_outliers (
    outlier_id INT PRIMARY KEY,
    destination_key INT NOT NULL,
    destination_name VARCHAR(150) NOT NULL,
    method VARCHAR(50) NOT NULL,                   -- 'Isolation Forest' or 'IQR / Z-Score'
    feature_name VARCHAR(100) NOT NULL,
    feature_value DECIMAL(10,2) NOT NULL,
    threshold_value DECIMAL(10,2) NOT NULL,
    anomaly_score DECIMAL(6,4) NOT NULL,
    reason TEXT NOT NULL,
    CONSTRAINT fk_outlier_dest FOREIGN KEY (destination_key) REFERENCES dim_destination(destination_key)
);

CREATE TABLE mining_trends (
    trend_id INT PRIMARY KEY,
    category_type VARCHAR(50) NOT NULL,            -- 'Season', 'Region', 'Accessibility'
    category_value VARCHAR(100) NOT NULL,
    avg_mid_spend DECIMAL(10,2) NOT NULL,
    avg_popularity DECIMAL(4,2) NOT NULL,
    avg_duration DECIMAL(4,2) NOT NULL,
    avg_safety DECIMAL(4,2) NOT NULL,
    destination_count INT NOT NULL
);

-- ---------------------------------------------------------------------
-- 9. Analytical Warehouse Views
-- ---------------------------------------------------------------------
CREATE VIEW vw_star_destination_full AS
SELECT 
    f.fact_id,
    dt.date_key,
    dt.full_date,
    dt.year,
    dt.quarter,
    dt.month_name,
    d.destination_key,
    d.destination_name,
    d.latitude,
    d.longitude,
    d.permits_required,
    g.geography_key,
    g.country,
    g.region,
    g.state,
    g.district,
    c.connectivity_key,
    c.accessibility,
    c.road_connectivity,
    c.has_railway_access,
    c.nearest_airport_name,
    c.nearest_railway_name,
    c.nearest_city_name,
    s.seasonality_key,
    s.peak_tourist_season,
    s.off_season,
    s.winter_temp_desc,
    s.summer_temp_desc,
    f.min_duration_days,
    f.ideal_duration_days,
    f.max_duration_days,
    f.altitude_m,
    f.popularity_score,
    f.safety_rating,
    f.airport_distance_km,
    f.railway_distance_km,
    f.city_distance_km,
    f.budget_daily_avg,
    f.mid_daily_avg,
    f.luxury_daily_avg,
    f.total_estimated_trip_cost_mid
FROM fact_destination_metrics f
JOIN dim_date dt ON f.date_key = dt.date_key
JOIN dim_destination d ON f.destination_key = d.destination_key
JOIN dim_geography g ON f.geography_key = g.geography_key
JOIN dim_connectivity c ON f.connectivity_key = c.connectivity_key
JOIN dim_seasonality s ON f.seasonality_key = s.seasonality_key;

-- Unpivoted Tier-Level Grain View (100 destinations x 3 tiers = 300 rows)
CREATE VIEW vw_fact_destination_tier_spend AS
SELECT 
    f.fact_id * 10 + 1 AS tier_fact_id,
    f.destination_key,
    d.destination_name,
    g.region,
    g.state,
    c.accessibility,
    'Budget' AS budget_tier,
    f.budget_accom_avg AS daily_accommodation,
    f.budget_food_avg AS daily_food,
    f.budget_act_avg AS daily_activities,
    f.budget_trans_avg AS daily_transport,
    f.budget_daily_avg AS total_daily_spend,
    f.ideal_duration_days,
    f.budget_daily_avg * f.ideal_duration_days AS total_trip_spend,
    f.popularity_score,
    f.safety_rating
FROM fact_destination_metrics f
JOIN dim_destination d ON f.destination_key = d.destination_key
JOIN dim_geography g ON f.geography_key = g.geography_key
JOIN dim_connectivity c ON f.connectivity_key = c.connectivity_key

UNION ALL

SELECT 
    f.fact_id * 10 + 2 AS tier_fact_id,
    f.destination_key,
    d.destination_name,
    g.region,
    g.state,
    c.accessibility,
    'Mid-Range' AS budget_tier,
    f.mid_accom_avg AS daily_accommodation,
    f.mid_food_avg AS daily_food,
    f.mid_act_avg AS daily_activities,
    f.mid_trans_avg AS daily_transport,
    f.mid_daily_avg AS total_daily_spend,
    f.ideal_duration_days,
    f.mid_daily_avg * f.ideal_duration_days AS total_trip_spend,
    f.popularity_score,
    f.safety_rating
FROM fact_destination_metrics f
JOIN dim_destination d ON f.destination_key = d.destination_key
JOIN dim_geography g ON f.geography_key = g.geography_key
JOIN dim_connectivity c ON f.connectivity_key = c.connectivity_key

UNION ALL

SELECT 
    f.fact_id * 10 + 3 AS tier_fact_id,
    f.destination_key,
    d.destination_name,
    g.region,
    g.state,
    c.accessibility,
    'Luxury' AS budget_tier,
    f.luxury_accom_avg AS daily_accommodation,
    f.luxury_food_avg AS daily_food,
    f.luxury_act_avg AS daily_activities,
    f.luxury_trans_avg AS daily_transport,
    f.luxury_daily_avg AS total_daily_spend,
    f.ideal_duration_days,
    f.luxury_daily_avg * f.ideal_duration_days AS total_trip_spend,
    f.popularity_score,
    f.safety_rating
FROM fact_destination_metrics f
JOIN dim_destination d ON f.destination_key = d.destination_key
JOIN dim_geography g ON f.geography_key = g.geography_key
JOIN dim_connectivity c ON f.connectivity_key = c.connectivity_key;
