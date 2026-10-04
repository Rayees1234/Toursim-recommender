# Architecture & Project Assumptions Log

**Project**: Tourism Data Warehouse and Data Mining System (DMDW)  
**Document**: `docs/ASSUMPTIONS.md`  
**Compliance**: Adheres strictly to Non-Negotiable Rules 2, 5, and 6.

---

## 1. Dataset & Scope Assumptions

### 1.1 Temporal Nature of the Dataset
- **Observation**: The raw dataset `india_tourism_dataset.json` contains a single snapshot date (`last_updated = "2026-01-12"`) for each destination rather than a 10-year longitudinal transactional log of daily tourist footfalls.
- **Assumption / Adaptation**:
  - The Date Dimension (`dim_date`) is modeled as a standardized calendar dimension populated with the snapshot date and associated calendar hierarchies (Year, Quarter, Month, Day, Month Name, Day of Week).
  - Trend Analysis is modeled around **seasonal dynamics** (Winter, Summer, Monsoon, Post-Monsoon) and comparative growth across budget tiers and regional sectors, rather than synthetic time-series forecasting. No fake historical dates are fabricated.

### 1.2 Multi-Valued Attributes & Bridge Modeling
- **Observation**: Fields such as `trip_types`, `activities_available`, `accommodation_types`, and `best_seasons` are arrays containing multiple strings per destination.
- **Assumption / Adaptation**:
  - In our dimensional model, these are stored in dedicated bridge/dimension tables (`dim_trip_type`, `bridge_destination_trip_type`, `dim_activity`, `bridge_destination_activity`, `dim_accommodation`, `bridge_destination_accommodation`, `dim_season`, `bridge_destination_season`).
  - This preserves first normal form (1NF) in the relational schema while enabling flexible slicing, dicing, and market basket association mining.

### 1.3 Handling Missing Railway Distances (Islands)
- **Observation**: Exactly 8 destination records have `nearest_railway_station.distance_km = null`. All 8 are offshore island locations (Andaman & Nicobar Islands, Lakshadweep).
- **Assumption / Adaptation**:
  - Distance is imputed to `-1` (indicating non-applicable), the station name is standardized to `"No Railway Network (Island Territory)"`, and a boolean indicator `has_railway_access = 0` is provided. This reflects real-world physical geography without introducing misleading numerical zeroes or dropped records.

### 1.4 Region & State Standardization
- **Observation**: Region labels in raw data contain minor variants (`'North East India'` vs `'Northeast India'`).
- **Assumption / Adaptation**:
  - Cleaned into canonical 7 geographical zones: `North India`, `South India`, `West India`, `East India`, `Central India`, `Northeast India`, and `Island Territory`.
  - Border circuits (e.g. `'Kerala & Karnataka (bordering regions)'`) retain their raw state descriptor in `dim_destination` while mapping to the dominant state (`Kerala`) for hierarchy integrity in `dim_geography`.

---

## 2. Warehouse & OLAP Assumptions

### 2.1 Fact Table Grain
- **Declared Primary Grain**:  
  *"One row per tourist destination observation snapshot, representing its verified geographic location, infrastructure metrics, stay duration requirements, and multi-tier daily expenditure profile."*
- **Justification**: The atomic unit of observation provided by the dataset is the individual destination. Multi-tier expenditures (Budget, Mid-range, Luxury) and categories (Accommodation, Food, Activities, Transport) are stored as additive measures.
- **Auxiliary View Grain**:
  An unpivoted analytical view `vw_fact_destination_tier_spend` provides a granular grain of *"One row per destination per budget tier"* (100 destinations × 3 tiers = 300 rows) for drill-down and multi-dimensional pivoting.

### 2.2 Database Compatibility & Dual-Engine Fallback
- **Observation**: The target warehouse is specified as a MySQL star-schema warehouse. In some student environments or local development machines, the MySQL daemon (`MYSQL80`) may be stopped or require administrative rights to launch.
- **Assumption / Adaptation**:
  - The project implements a robust **Database Adapter** pattern (`sql/database.py`).
  - It prioritizes **MySQL 8.0** using connection credentials loaded from `.env`.
  - If MySQL is unavailable or connection fails, the pipeline seamlessly initializes and queries an identical **SQLite warehouse** (`data/processed/tourism_dw.db`) containing the identical star schema tables, indexes, views, and data rows.
  - This guarantees 100% testability, zero crashes, and complete academic reproducibility while preserving pure MySQL DDL in `sql/schema.sql`.

---

## 3. Data Mining Assumptions

### 3.1 Unsupervised Clustering (K-Means)
- Features chosen: `mid_daily_avg`, `ideal_days`, `popularity_score`, `safety_rating`, `altitude_m`, `airport_dist_km`.
- Features are strictly standardized using `StandardScaler` (zero mean, unit variance).
- Optimal $k$ is determined automatically via combined **Elbow Method (SSE/Inertia)** and **Silhouette Score** optimization over $k \in [2, 6]$.
- **Programmatic Cluster Naming**: Centroids are evaluated along normalized spending and duration dimensions to generate dynamic labels (e.g. `Tier 1: High-Spend / Long-Duration Destinations`, `Tier 2: Budget / Mountain Getaways`). No hardcoded persona names are used.

### 3.2 Association Rule Mining (Apriori / FP-Growth)
- Each destination's combined attributes (`trip_types` + `accommodation_types` + `best_seasons` + `accessibility`) serve as a transaction basket.
- Minimum support threshold is tuned adaptively to dataset size ($N=100$, default `min_support = 0.08` to ensure robust rules).
- Rules with $\text{Lift} \le 1.0$ (independent or negative associations) are automatically filtered out.
- Natural-language explanations are generated dynamically using templated sentences based on calculated Support, Confidence, and Lift.

### 3.3 Classification & Zero-Leakage Policy
- Target: `spend_class` (`High` vs `Moderate/Budget`) determined by a median split of `mid_daily_avg` (median = ₹4,800).
- **Leakage Prevention**: To strictly eliminate target leakage, all expense metrics (`budget_*`, `mid_*`, `luxury_*`, `accommodation_*`, `food_*`, `activities_*`, `transport_*`) are **excluded** from the feature matrix.
- Predictors used: `ideal_days`, `minimum_days`, `maximum_days`, `altitude_m`, `popularity_score`, `safety_rating`, `airport_dist_km`, `railway_dist_km`, `region`, `accessibility`, `permits_required`.
- Model comparison evaluates Random Forest, Logistic Regression, and Decision Tree with 5-fold cross-validation, stratified train/test split (80/20), and reports Accuracy, Precision, Recall, F1-Score, and Confusion Matrix.

### 3.4 Outlier Detection
- Evaluated via IQR, Z-Score ($|Z| > 2.5$), and Isolation Forest (`contamination = 0.05`).
- Flagged records report the exact numerical deviation and contextual explanation (e.g., extreme altitude > 4,000m for Ladakh and Spiti; ultra-luxury resorts in Udaipur).

---

## 4. UI & Dashboard Assumptions
- Every KPI, chart series, table row, cluster label, and metric displayed in the frontend dashboard is fetched dynamically via the Flask REST API from database queries or pipeline calculations.
- Global filters (Region, State, Accessibility, Permits, Min Rating) trigger parameterized backend queries dynamically.
