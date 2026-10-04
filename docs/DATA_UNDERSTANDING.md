# Tourism Data Understanding & Profiling Report

**Project**: Tourism Data Warehouse and Data Mining System (DMDW)  
**Academic Target**: B.Tech CSE Submission & Interactive Live Demo  
**Date**: October 2026  
**Status**: Completed (Phase 1 Baseline)

---

## 1. Executive Summary & File Inventory

The workspace contains four primary files defining the tourism analytics domain for Indian destinations:

| File Name | Format | Size | Records / Dimensions | Primary Description |
|---|---|---|---|---|
| `india_tourism_dataset.json` | JSON (Array of Objects) | ~572.6 KB | 100 rows × 54 columns | Complete tourism profiles for 100 Indian destinations, including geography, connectivity, cost tiers, seasonal patterns, activities, and ratings. |
| `dataset_schema.json` | JSON Schema (Draft-07) | ~22.7 KB | 917 lines | Structural specification defining validation rules, mandatory fields (53 required), types, and nested constraints. |
| `destination_names.txt` | Plain Text | ~3.0 KB | 100 lines (numbered 1 to 100) | Master list of destination names corresponding 1:1 to the 100 entries in `india_tourism_dataset.json`. |
| `skills-lock.json` | JSON | ~0.8 KB | 13 lines | Lockfile for environment agent skills. |

Original raw files are stored immutably in `data/raw/`. All transformations, cleanings, and derived outputs are written to `data/processed/` and the database warehouse.

---

## 2. File-by-File Technical Inspection

### 2.1 `india_tourism_dataset.json`
- **Format**: JSON array containing 100 destination objects.
- **Dimensions**: 100 records × 54 attributes per record.
- **Primary Key**: `id` (integer, ranges strictly from 1 to 100 with zero duplicates).
- **Destination Name (`destination_name`)**: 93 unique names across 100 rows.
  - **7 Duplicate Names Detected**:
    1. *Varanasi (Kashi)*: IDs 4 and 39 (both Uttar Pradesh, North India).
    2. *Coorg (Kodagu)*: IDs 8 and 53 (both Karnataka, South India).
    3. *Tawang*: IDs 14 and 73 (both Arunachal Pradesh).
    4. *Spiti Valley*: IDs 16 and 74 (both Himachal Pradesh).
    5. *Gokarna*: IDs 25 and 71 (both Karnataka).
    6. *Havelock Island (Swaraj Dweep)*: IDs 31 and 61 (Andaman & Nicobar).
    7. *Neil Island (Shaheed Dweep)*: IDs 32 and 62 (Andaman & Nicobar).
  - *Finding*: While `destination_name` has duplicates reflecting regional circuit mentions, each record has a unique `id` and distinct nested attributes. In our warehouse, surrogate integer keys (`destination_key`) ensure primary key uniqueness.

- **Missing Values**:
  - `nearest_railway_station.distance_km`: Missing (None/null) in **8 records** (8.0%).
    - These 8 records correspond strictly to island locations: Havelock Island (IDs 31, 61), Neil Island (IDs 32, 62), Lakshadweep / Agatti (ID 49), Kalpeni Island (ID 50), Port Blair (ID 63), Bangaram & Kadmat (ID 88).
    - Station name is explicitly recorded as `"None"` or `"None (island; access via ferry...)"`.
    - Handling: In the warehouse, this is imputed to `-1` or mapped with a boolean indicator `has_railway_access = 0` to preserve the real domain fact that islands have no rail network.
  - `average_temperature.monsoon`: Contains string `'data_not_available'` for cold desert high-altitude destination Ladakh (ID 2).
  - All other 52 fields have **0 missing values (100% complete)**.

- **Value Ranges & Distributions**:
  - `altitude_m`: 0 m (Goa, Kanyakumari, Islands) to 4,350 m (Pangong Lake).
  - `popularity_score`: Integer from 4 to 10 (mean = 7.72, median = 8).
  - `safety_rating`: Integer from 6 to 9 (mean = 7.86, median = 8).
  - `ideal_days`: 0.5 to 7.0 days (mean = 3.65 days).
  - `minimum_days`: 0.5 to 6.0 days (mean = 2.45 days).
  - `maximum_days`: 1 to 14 days (mean = 5.68 days).
  - Geographic Coordinates:
    - Latitude: 8.0883° N (Kanyakumari) to 34.6700° N (Nubra Valley).
    - Longitude: 69.6700° E (Kutch) to 94.2000° E (Ziro Valley).
  - Nearest Transport Distances:
    - `nearest_airport.distance_km`: 0 km to 520 km (mean = 112.5 km).
    - `nearest_railway_station.distance_km`: 0 km to 450 km (for non-islands, mean = 74.2 km).
    - `nearest_major_city.distance_km`: 0 km to 490 km (mean = 145.8 km).

- **Cost & Expenditure Tiers (Currency: INR ₹)**:
  Every record contains 3 detailed budget tiers (`budget_category`, `mid_range_category`, `luxury_category`), each breaking down into 4 itemized components plus total daily range `[min, max]`:
  - **Budget Tier**:
    - Accommodation: ₹250 – ₹1,800 / day
    - Food: ₹200 – ₹700 / day
    - Activities: ₹0 – ₹800 / day
    - Local Transport: ₹50 – ₹300 / day
    - Total Daily Spend: ₹500 – ₹3,400 / day (Median avg: ₹1,950 / day)
  - **Mid-Range Tier**:
    - Accommodation: ₹1,500 – ₹6,000 / day
    - Food: ₹500 – ₹1,800 / day
    - Activities: ₹300 – ₹2,500 / day
    - Local Transport: ₹200 – ₹800 / day
    - Total Daily Spend: ₹2,500 – ₹9,500 / day (Median avg: ₹4,800 / day)
  - **Luxury Tier**:
    - Accommodation: ₹5,000 – ₹35,000 / day
    - Food: ₹1,200 – ₹5,000 / day
    - Activities: ₹800 – ₹8,000 / day
    - Local Transport: ₹300 – ₹1,500 / day
    - Total Daily Spend: ₹6,900 – ₹45,000 / day (Median avg: ₹17,500 / day)
  - **Integrity Validation**: Min ≤ Max holds for 100% of records. Budget ≤ Mid-Range ≤ Luxury holds for 100% of records. No negative or impossible expenditures exist.

- **Categorical & List Field Counts**:
  - `region`: 9 raw string values (`North India`, `South India`, `West India`, `East India`, `Central India`, `North East India`, `Northeast India`, `Island Territory`, `Multi-state`). Standardised to 7 geographic zones (`North`, `South`, `West`, `East`, `Central`, `Northeast`, `Islands`).
  - `state`: 30 distinct values (covers 28 states and union territories).
  - `trip_types`: 103 distinct unique trip types (e.g., `Beach`, `Heritage`, `Spiritual`, `Adventure`, `Wildlife`, `Hill_station`, `Trekking`, `Monsoon`, `Nature`).
  - `accommodation_types`: 11 distinct categories (`Hotels`, `Resorts`, `Homestays`, `Guesthouses`, `Hostels`, `Camps / Tents`, `Houseboats`, `Ashrams`, `Monasteries`, `Heritage Stays`, `Cottages`).
  - `activities_available`: 350+ unique activities across destinations.
  - `accessibility`: 3 distinct levels (`Easy`, `Moderate`, `Difficult`).
  - `permits_required`: Boolean (`True`: 14 destinations, `False`: 86 destinations).

---

## 3. Data Dictionary

| Column Name | Raw Data Type | Target Warehouse Type | Classification | Description & Value Domain |
|---|---|---|---|---|
| `id` | Integer | INT | Key / Identifier | Unique destination ID (1 to 100). |
| `destination_name` | String | VARCHAR(150) | Dimension | Destination display name. |
| `state` | String | VARCHAR(100) | Dimension | State or Union Territory name. |
| `region` | String | VARCHAR(50) | Dimension | Geographic macro-region (North, South, etc.). |
| `district` | String | VARCHAR(150) | Dimension | District name(s). |
| `latitude` | Float | DECIMAL(9,6) | Dimension / Spatial | Decimal latitude (8.0883 to 34.6700). |
| `longitude` | Float | DECIMAL(9,6) | Dimension / Spatial | Decimal longitude (69.6700 to 94.2000). |
| `altitude_m` | Integer | INT | Measure | Elevation above sea level in meters (0 to 4,350 m). |
| `accessibility` | String | VARCHAR(50) | Dimension | Accessibility difficulty rating (Easy, Moderate, Difficult). |
| `road_connectivity` | String | VARCHAR(255) | Dimension | Quality and nature of road access. |
| `airport_name` | String | VARCHAR(150) | Dimension | Nearest commercial airport. |
| `airport_distance_km` | Integer | INT | Measure | Road distance to nearest airport in km (0 to 520 km). |
| `railway_name` | String | VARCHAR(150) | Dimension | Nearest railway station name (or 'None' for islands). |
| `railway_distance_km` | Integer (nullable) | INT | Measure | Road distance to nearest rail station (-1 if island/none). |
| `city_name` | String | VARCHAR(150) | Dimension | Nearest major urban center. |
| `city_distance_km` | Integer | INT | Measure | Distance to nearest major city in km (0 to 490 km). |
| `minimum_days` | Float / Int | DECIMAL(4,1) | Measure | Minimum recommended stay duration (0.5 to 6.0 days). |
| `ideal_days` | Float / Int | DECIMAL(4,1) | Measure | Ideal recommended stay duration (0.5 to 7.0 days). |
| `maximum_days` | Integer | INT | Measure | Maximum recommended stay duration (1 to 14 days). |
| `popularity_score` | Integer | INT | Measure | Destination popularity index (scale 1–10). |
| `safety_rating` | Integer | INT | Measure | Destination safety index (scale 1–10). |
| `permits_required` | Boolean | TINYINT(1) | Dimension | Flag indicating special permit requirement (0 = No, 1 = Yes). |
| `budget_daily_min` | Integer | DECIMAL(10,2) | Measure | Minimum daily expenditure in Budget tier (INR ₹). |
| `budget_daily_max` | Integer | DECIMAL(10,2) | Measure | Maximum daily expenditure in Budget tier (INR ₹). |
| `budget_daily_avg` | Float | DECIMAL(10,2) | Measure | Midpoint daily expenditure in Budget tier (INR ₹). |
| `mid_daily_min` | Integer | DECIMAL(10,2) | Measure | Minimum daily expenditure in Mid-Range tier (INR ₹). |
| `mid_daily_max` | Integer | DECIMAL(10,2) | Measure | Maximum daily expenditure in Mid-Range tier (INR ₹). |
| `mid_daily_avg` | Float | DECIMAL(10,2) | Measure | Midpoint daily expenditure in Mid-Range tier (INR ₹). |
| `luxury_daily_min` | Integer | DECIMAL(10,2) | Measure | Minimum daily expenditure in Luxury tier (INR ₹). |
| `luxury_daily_max` | Integer | DECIMAL(10,2) | Measure | Maximum daily expenditure in Luxury tier (INR ₹). |
| `luxury_daily_avg` | Float | DECIMAL(10,2) | Measure | Midpoint daily expenditure in Luxury tier (INR ₹). |
| `trip_cost_mid_est` | Float | DECIMAL(12,2) | Measure | Estimated total trip spend (`ideal_days` × `mid_daily_avg`). |
| `peak_season` | String | VARCHAR(255) | Dimension | Text description of peak visitor months. |
| `off_season` | String | VARCHAR(255) | Dimension | Text description of low season / off-peak months. |
| `best_seasons` | Array of Strings | Bridge / Dim | Dimension | Structured list of optimal travel seasons (Winter, Monsoon, etc.). |
| `trip_types` | Array of Strings | Bridge / Dim | Dimension | Structured list of tourism categories. |
| `accommodation_types`| Array of Strings | Bridge / Dim | Dimension | Available lodging types. |
| `activities_available`| Array of Strings | Bridge / Dim | Dimension | Available recreational and cultural activities. |
| `last_updated` | String (Date) | DATE | Dimension / Time | Dataset snapshot update date (`2026-01-12`). |

---

## 4. Data Quality & Profiling Report

1. **Station Distance Nulls**: 8 records have null railway distance. Investigation revealed these are all offshore island territories (Andaman & Nicobar, Lakshadweep) where no train tracks exist. In ETL, we assign `railway_distance_km = -1` and set a flag `has_rail = FALSE` with station name `"No Railway Connection (Island)"`.
2. **Citation Artifacts & Unicode Characters**: Several text fields contain web scraper citation markers like `[web:269]`, non-breaking hyphens (`\u2011`), en-dashes (`–`), and non-standard whitespace. The cleaning pipeline scrubs citation tags, replaces non-breaking characters with standard ASCII dashes/spaces, and trims whitespace.
3. **Region Categorisation Inconsistencies**: The dataset contains both `'North East India'` and `'Northeast India'`. The cleaning pipeline maps both to a single canonical `'Northeast India'` category.
4. **Multi-State Demarcations**: Special circuits such as `'Madhya Pradesh / Chhattisgarh border'` and `'Kerala & Karnataka (bordering regions)'` are standardized into clean primary state assignments with cross-border flags.
5. **Temperature String Variation**: Temperature is provided as textual ranges (`"10-25°C"`, `"-15 to -5°C"`, `"data_not_available"`). A numerical parsing function extracts min, max, and mean temperatures per season for analytical modeling.
6. **Zero Orphan Facts Guarantee**: Source records map 100% to dimension surrogate keys. All foreign keys are strictly validated.

---

## 5. Fact vs. Dimension Classification & Grain Declaration

### 5.1 Classification
- **Fact-like Attributes (Numeric, Additive & Semi-Additive Measures)**:
  - Daily expenditures across 3 tiers (Budget, Mid-range, Luxury) and 4 categories (Accommodation, Food, Activities, Transport).
  - Estimated total trip expenditure (`ideal_days` × `daily_avg`).
  - Stay durations (`minimum_days`, `ideal_days`, `maximum_days`).
  - Physical metrics: `altitude_m`, `airport_distance_km`, `railway_distance_km`, `city_distance_km`.
  - Evaluative metrics: `popularity_score`, `safety_rating`.
- **Dimension-like Attributes (Descriptive, Contextual & Hierarchical)**:
  - `dim_destination`: Name, district, coordinates, description, food scene, culture, permits.
  - `dim_geography`: Country (`India`) → Region (`North`, `South`, `West`, `East`, etc.) → State → District.
  - `dim_connectivity`: Accessibility level (`Easy`, `Moderate`, `Difficult`), road connectivity, ATM availability, internet connectivity.
  - `dim_date`: Full calendar hierarchy (Date, Day, Month, Month Name, Quarter, Year) based on snapshot date `2026-01-12`.
  - Bridge Dimensions for Multi-Valued Attributes: `dim_trip_type`, `dim_activity`, `dim_accommodation`, `dim_season`.

### 5.2 Declared Fact-Table Grain
> **Primary Fact Table Grain**:  
> **"One row per tourist destination observation snapshot, representing its verified geographic location, infrastructure metrics, duration requirements, and multi-tier daily expenditure profile."**

This grain guarantees that:
- Every record in `fact_destination_metrics` corresponds directly to a unique destination entity (100 rows).
- Multi-tier spend analysis is directly accessible via measures (`budget_*`, `mid_*`, `luxury_*`) or through the unpivoted analytical view `vw_fact_destination_tier_spend` (Grain: 1 row per destination × budget tier = 300 rows).
- Roll-up, Drill-down, Slice, Dice, and Pivot operate cleanly without double-counting.

---

## 6. Analytical Feasibility Matrix

| Analysis Module | Feasibility Status | Justifying Columns & Data Capabilities | Notes & Implementation Strategy |
|---|---|---|---|
| **OLAP (Roll-up, Drill-down, Slice, Dice, Pivot)** | **Feasible** | `region`, `state`, `district`, `accessibility`, `permits_required`, `popularity_score`, `budget_daily_avg`, `mid_daily_avg`, `luxury_daily_avg`, `ideal_days` | Complete multi-level geographical hierarchy (Country → Region → State → District → Destination) and connectivity hierarchy allow full 5 OLAP operations using SQL GROUP BY WITH ROLLUP and parameterized queries. |
| **K-Means Clustering** | **Feasible** | `mid_daily_avg`, `ideal_days`, `popularity_score`, `safety_rating`, `altitude_m`, `airport_distance_km` | High-quality continuous variables. Scaled with StandardScaler. Optimal $k$ determined programmatically via combined Elbow (Inertia) and Silhouette score analysis. Cluster names generated dynamically from centroid rankings. |
| **Association Rule Mining (Apriori / FP-Growth)** | **Feasible** | `trip_types`, `activities_available`, `accommodation_types`, `best_seasons` | Each destination acts as a basket/transaction of characteristics. Apriori / FP-growth identifies frequent itemsets and high-lift associations (e.g., Beach + Water sports + Resorts). |
| **Supervised Classification** | **Feasible** | Predictor features: `ideal_days`, `altitude_m`, `popularity_score`, `safety_rating`, `airport_distance_km`, `region`, `accessibility`. Target: `spend_category` (Median split: High Spender vs. Budget/Moderate Spender) or `popularity_tier`. | Evaluates 3 algorithms (Random Forest, Logistic Regression, Decision Tree) using stratified train/test splits and 5-fold cross-validation. Zero data leakage: spend category target is derived solely from total spend, and component spend columns are excluded from features. |
| **Outlier Detection** | **Feasible** | `altitude_m` (e.g. Pangong Lake > 4,000m), `luxury_daily_max` (super-luxury resorts), `airport_distance_km` (remote valleys) | Implemented via IQR method, Z-score, and multivariate Isolation Forest. Reports flagged records with exact anomaly scores and business justifications. |
| **Trend & Seasonality Analysis** | **Feasible (Seasonal)** | `best_seasons`, `avoid_seasons`, `peak_tourist_season`, `off_season`, `average_temperature` | While the dataset is a point-in-time snapshot (`last_updated = 2026-01-12`) without multi-year transactional logs, seasonality distribution across seasons (Winter, Summer, Monsoon, Spring/Autumn) and temperature trends across seasons are fully analyzed. |
| **Recommendation Engine** | **Feasible** | `trip_types`, `budget_category`, `ideal_days`, `best_seasons`, `region`, `popularity_score` | Content-based filtering matching user criteria (budget limit, trip duration, preferred season, preferred region, activity interest) against destination feature profiles with cosine similarity ranking. |

---

## 7. Currency and Units of Measurement

- **Currency**: All monetary values are exclusively in **Indian National Rupees (INR, ₹)**.
- **Elevation / Altitude**: Measured in **meters (m)** above sea level.
- **Distances**: Measured in **kilometers (km)** via shortest road/ferry transit route.
- **Trip Duration**: Measured in **days** (`ideal_days`, `minimum_days`, `maximum_days`).
- **Temperatures**: Expressed in **degrees Celsius (°C)**.
- **Rating Scales**: `popularity_score` (1 to 10 scale), `safety_rating` (1 to 10 scale).
