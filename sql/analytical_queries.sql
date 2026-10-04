-- =====================================================================
-- Tourism Data Warehouse: Analytical & OLAP SQL Queries
-- Database: MySQL 8.0 / SQLite Dual-Engine Compatible
-- =====================================================================

-- ---------------------------------------------------------------------
-- 1. Executive Summary KPIs
-- ---------------------------------------------------------------------
SELECT 
    COUNT(DISTINCT f.destination_key) AS total_destinations,
    COUNT(DISTINCT g.state) AS total_states,
    COUNT(DISTINCT g.region) AS total_regions,
    ROUND(AVG(f.ideal_duration_days), 2) AS avg_trip_duration_days,
    ROUND(AVG(f.popularity_score), 2) AS avg_popularity_score,
    ROUND(AVG(f.safety_rating), 2) AS avg_safety_rating,
    ROUND(AVG(f.budget_daily_avg), 2) AS avg_budget_daily_spend_inr,
    ROUND(AVG(f.mid_daily_avg), 2) AS avg_mid_daily_spend_inr,
    ROUND(AVG(f.luxury_daily_avg), 2) AS avg_luxury_daily_spend_inr,
    ROUND(AVG(f.total_estimated_trip_cost_mid), 2) AS avg_total_trip_cost_mid_inr
FROM fact_destination_metrics f
JOIN dim_geography g ON f.geography_key = g.geography_key;

-- ---------------------------------------------------------------------
-- 2. OLAP Operation 1: Roll-up (Hierarchical Aggregation)
-- Aggregates metrics up the Geography hierarchy: Region -> Country
-- ---------------------------------------------------------------------
SELECT 
    COALESCE(g.region, 'All Regions (India Total)') AS region,
    COUNT(f.destination_key) AS destination_count,
    ROUND(AVG(f.ideal_duration_days), 2) AS avg_ideal_days,
    ROUND(AVG(f.popularity_score), 2) AS avg_popularity,
    ROUND(AVG(f.safety_rating), 2) AS avg_safety,
    ROUND(AVG(f.mid_daily_avg), 2) AS avg_daily_mid_spend,
    ROUND(MIN(f.budget_daily_min), 2) AS min_budget_spend,
    ROUND(MAX(f.luxury_daily_max), 2) AS max_luxury_spend
FROM fact_destination_metrics f
JOIN dim_geography g ON f.geography_key = g.geography_key
GROUP BY g.region WITH ROLLUP;

-- ---------------------------------------------------------------------
-- 3. OLAP Operation 2: Drill-down (Granular Sub-level Analysis)
-- Drills down into a selected Region to examine State and District metrics
-- Parameter: :region_name (e.g. 'South India')
-- ---------------------------------------------------------------------
SELECT 
    g.region,
    g.state,
    g.district,
    d.destination_name,
    c.accessibility,
    f.ideal_duration_days,
    f.mid_daily_avg,
    f.popularity_score,
    f.safety_rating
FROM fact_destination_metrics f
JOIN dim_geography g ON f.geography_key = g.geography_key
JOIN dim_destination d ON f.destination_key = d.destination_key
JOIN dim_connectivity c ON f.connectivity_key = c.connectivity_key
WHERE g.region = 'South India'
ORDER BY g.state, f.popularity_score DESC;

-- ---------------------------------------------------------------------
-- 4. OLAP Operation 3: Slice (Fixing One Dimension Value)
-- Slices on Accessibility = 'Easy'
-- ---------------------------------------------------------------------
SELECT 
    d.destination_name,
    g.region,
    g.state,
    c.accessibility,
    c.road_connectivity,
    f.mid_daily_avg,
    f.popularity_score,
    f.safety_rating
FROM fact_destination_metrics f
JOIN dim_destination d ON f.destination_key = d.destination_key
JOIN dim_geography g ON f.geography_key = g.geography_key
JOIN dim_connectivity c ON f.connectivity_key = c.connectivity_key
WHERE c.accessibility = 'Easy'
ORDER BY f.popularity_score DESC;

-- ---------------------------------------------------------------------
-- 5. OLAP Operation 4: Dice (Filtering on Multiple Dimensions Simultaneously)
-- Filters: Region IN ('North India', 'Northeast India')
--          AND Safety Rating >= 8
--          AND Mid-Range Daily Spend <= 5000
-- ---------------------------------------------------------------------
SELECT 
    d.destination_name,
    g.region,
    g.state,
    c.accessibility,
    f.safety_rating,
    f.popularity_score,
    f.mid_daily_avg,
    f.ideal_duration_days,
    f.total_estimated_trip_cost_mid
FROM fact_destination_metrics f
JOIN dim_destination d ON f.destination_key = d.destination_key
JOIN dim_geography g ON f.geography_key = g.geography_key
JOIN dim_connectivity c ON f.connectivity_key = c.connectivity_key
WHERE g.region IN ('North India', 'Northeast India')
  AND f.safety_rating >= 8
  AND f.mid_daily_avg <= 5000.00
ORDER BY f.safety_rating DESC, f.mid_daily_avg ASC;

-- ---------------------------------------------------------------------
-- 6. OLAP Operation 5: Pivot (Multi-Dimensional Cross-Tabulation)
-- Rows: Region, Columns: Accessibility Levels, Measure: AVG(Mid Daily Spend)
-- ---------------------------------------------------------------------
SELECT 
    g.region,
    COUNT(f.destination_key) AS total_destinations,
    ROUND(AVG(CASE WHEN c.accessibility = 'Easy' THEN f.mid_daily_avg ELSE NULL END), 2) AS avg_spend_easy,
    ROUND(AVG(CASE WHEN c.accessibility = 'Moderate' THEN f.mid_daily_avg ELSE NULL END), 2) AS avg_spend_moderate,
    ROUND(AVG(CASE WHEN c.accessibility = 'Difficult' THEN f.mid_daily_avg ELSE NULL END), 2) AS avg_spend_difficult,
    ROUND(AVG(f.mid_daily_avg), 2) AS overall_avg_spend
FROM fact_destination_metrics f
JOIN dim_geography g ON f.geography_key = g.geography_key
JOIN dim_connectivity c ON f.connectivity_key = c.connectivity_key
GROUP BY g.region
ORDER BY total_destinations DESC;

-- ---------------------------------------------------------------------
-- 7. Spend Breakdown by Category (Accommodation, Food, Activities, Transport)
-- Across Tiers
-- ---------------------------------------------------------------------
SELECT 
    'Budget Tier' AS tier_name,
    ROUND(AVG(budget_accom_avg), 2) AS avg_accommodation,
    ROUND(AVG(budget_food_avg), 2) AS avg_food,
    ROUND(AVG(budget_act_avg), 2) AS avg_activities,
    ROUND(AVG(budget_trans_avg), 2) AS avg_transport,
    ROUND(AVG(budget_daily_avg), 2) AS avg_daily_total
FROM fact_destination_metrics

UNION ALL

SELECT 
    'Mid-Range Tier' AS tier_name,
    ROUND(AVG(mid_accom_avg), 2) AS avg_accommodation,
    ROUND(AVG(mid_food_avg), 2) AS avg_food,
    ROUND(AVG(mid_act_avg), 2) AS avg_activities,
    ROUND(AVG(mid_trans_avg), 2) AS avg_transport,
    ROUND(AVG(mid_daily_avg), 2) AS avg_daily_total
FROM fact_destination_metrics

UNION ALL

SELECT 
    'Luxury Tier' AS tier_name,
    ROUND(AVG(luxury_accom_avg), 2) AS avg_accommodation,
    ROUND(AVG(luxury_food_avg), 2) AS avg_food,
    ROUND(AVG(luxury_act_avg), 2) AS avg_activities,
    ROUND(AVG(luxury_trans_avg), 2) AS avg_transport,
    ROUND(AVG(luxury_daily_avg), 2) AS avg_daily_total
FROM fact_destination_metrics;

-- ---------------------------------------------------------------------
-- 8. Top 10 Most Popular Destinations with Complete Profile
-- ---------------------------------------------------------------------
SELECT 
    d.destination_name,
    g.state,
    g.region,
    c.accessibility,
    f.popularity_score,
    f.safety_rating,
    f.ideal_duration_days,
    f.mid_daily_avg AS daily_spend_inr,
    f.total_estimated_trip_cost_mid AS estimated_trip_cost_inr
FROM fact_destination_metrics f
JOIN dim_destination d ON f.destination_key = d.destination_key
JOIN dim_geography g ON f.geography_key = g.geography_key
JOIN dim_connectivity c ON f.connectivity_key = c.connectivity_key
ORDER BY f.popularity_score DESC, f.safety_rating DESC, f.mid_daily_avg ASC
LIMIT 10;
