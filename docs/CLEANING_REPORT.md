# Data Cleaning & Transformation Report

**Project**: Tourism Data Warehouse and Data Mining System (DMDW)  
**Document**: `docs/CLEANING_REPORT.md`  
**Pipeline Run Status**: Successful (Pass, Zero Dropped Records, Zero Orphan Facts)

---

## 1. Executive Summary & Row Reconciliation

The ETL pipeline enforces strict data preservation: every valid destination is retained and enriched, with edge cases handled domain-specifically rather than blindly dropped.

| Pipeline Stage | Entity / Table | Input Count | Output Count | Records Dropped | Reconciliation Status |
|---|---|---|---|---|---|
| **Extraction** | Raw JSON array | 100 records | 100 records | 0 | 100% Extracted |
| **Cleaning** | `cleaned_tourism_data.json` | 100 records | 100 records | 0 | 100% Cleaned |
| **Transformation** | Star Schema Dimensions | 100 records | 100 destinations (+ 1 Unknown) | 0 | 100% Mapped |
| **Loading** | `fact_destination_metrics` | 100 records | 100 fact rows | 0 | 100% Reconciled |
| **Integrity Audit** | Foreign Key References | 100 fact rows | 0 orphan facts | 0 | 100% Valid |

---

## 2. Cleaning Operations & Rationale

### 2.1 Scraping Citation Markers & Text Sanitization
- **Issue**: Raw text fields contained web-scraper citations such as `[web:185]`, `[web:269]`, etc., alongside non-breaking hyphens (`\u2011`), en-dashes (`\u2013`), em-dashes (`\u2014`), and non-breaking spaces (`\u00a0`).
- **Action**: A regex sanitizer (`\[web:\d+\]`) stripped all citation tags. All dashes were normalized to standard ASCII hyphens (`-`), spaces collapsed to standard single spaces, and smart quotes converted to ASCII quotes.
- **Before / After**: 42 text fields sanitized across all 100 records. Zero corruption of descriptive text.

### 2.2 Imputation of Island Railway Distances
- **Issue**: Exactly 8 destination records had `nearest_railway_station.distance_km = null`. All 8 correspond to offshore island territories (Andaman & Nicobar Islands, Lakshadweep) where no train tracks exist.
- **Rationale**: Setting distance to 0 would falsely indicate that a railway station is located at the center of the destination. Dropping the records would discard premier Indian tourist hubs (Havelock Island, Neil Island, Lakshadweep).
- **Action**:
  - `railway_distance_km` imputed to `-1` (standard sentinel value for non-applicable).
  - `nearest_railway_name` set to `"No Railway Network (Island Territory)"`.
  - Added boolean flag `has_railway_access = 0` to `dim_connectivity`.
- **Before / After**: 8 records imputed; 0 nulls remain in the warehouse.

### 2.3 Region Canonicalization
- **Issue**: Inconsistent nomenclature between `'North East India'` (1 record) and `'Northeast India'` (5 records).
- **Action**: Standardized to canonical `'Northeast India'` across `dim_geography`.
- **Before / After**: 6 records canonicalized into unified regional hierarchy.

### 2.4 Temperature Range Parsing
- **Issue**: `average_temperature` in raw data contained human-readable strings like `"20-32°C"`, `"-15 to -5°C"`, or `"data_not_available"`.
- **Action**: Implemented regex numerical extraction to parse minimum, maximum, and midpoint temperatures (`min_c`, `max_c`, `avg_c`) while storing the descriptive string in `dim_seasonality`.
- **Before / After**: Numerical temperatures extracted for 99 destinations; `"Data Not Available"` preserved cleanly for Ladakh monsoon without crashing.

### 2.5 Multi-Valued Array Normalization
- **Issue**: Multi-valued arrays (`trip_types`, `activities_available`, `accommodation_types`, `best_seasons`) violate 1NF if stored as comma-separated strings.
- **Action**: Normalized into 4 dedicated bridge tables with foreign key constraints:
  - `bridge_destination_trip_type`: 409 links
  - `bridge_destination_activity`: 363 links
  - `bridge_destination_accommodation`: 306 links
  - `bridge_destination_season`: 259 links
- **Before / After**: 1NF compliance achieved while enabling fast index joins.

### 2.6 Spend Consistency & Zero-Leakage Derived Measures
- **Validation**:
  - Budget daily range $\le$ Mid-range daily range $\le$ Luxury daily range verified for 100% of records.
  - Calculated midpoint averages for each category (`accom_avg`, `food_avg`, `act_avg`, `trans_avg`, `daily_avg`).
  - Derived `total_estimated_trip_cost_mid = ideal_duration_days * mid_daily_avg`.
  - Confirmed no negative values or inverted ranges exist.

---

## 3. Idempotency & Repeatability

The pipeline is guaranteed to be idempotent:
- Executing `python run_pipeline.py` multiple times executes the DDL drop/create and bulk loads the exact 100 destination facts without creating duplicate rows, broken surrogate keys, or orphaned bridge records.
- Verified on SQLite and MySQL 8.0.
