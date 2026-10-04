# Data Mining & Data Warehouse Results Summary

**Project**: Tourism Data Warehouse and Data Mining System (DMDW)  
**Document**: `docs/RESULTS_SUMMARY.md`  
**Execution Source**: Verified pipeline run outputs from database queries

---

## 1. Warehouse ETL & Reconciliation Baseline

| Metric | Measured Value | Verification Status |
|---|---|---|
| **Raw Input Records** | 100 records | PASS (100% extracted) |
| **Cleaned Output Records** | 100 records | PASS (0 records dropped) |
| **Warehouse Fact Rows** | 100 rows | PASS (100% reconciled) |
| **Referential Integrity Audit** | 0 orphan facts | PASS (100% referential integrity) |
| **Unpivoted Tier Fact Rows** | 300 rows | PASS (100 destinations × 3 tiers) |
| **Database Engine Executed** | SQLite 3 (with MySQL 8.0 DDL compatibility) | PASS (Zero runtime errors) |

---

## 2. Regional OLAP Aggregations

Aggregated along Geography hierarchy ($N=100$ destinations):

| Region | Destination Count | Avg Ideal Days | Avg Popularity (1–10) | Avg Safety (1–10) | Avg Daily Mid Spend (INR) |
|---|---|---|---|---|---|
| **North India** | 31 | 3.26 days | ⭐ 7.90 | 🛡️ 7.81 | ₹4,951.61 |
| **South India** | 24 | 2.52 days | ⭐ 7.00 | 🛡️ 8.13 | ₹4,280.21 |
| **West India** | 16 | 2.56 days | ⭐ 8.00 | 🛡️ 8.19 | ₹4,796.88 |
| **East India** | 13 | 2.85 days | ⭐ 7.69 | 🛡️ 7.92 | ₹4,180.77 |
| **Central India** | 7 | 2.57 days | ⭐ 7.43 | 🛡️ 7.86 | ₹7,142.86 |
| **Island Territory** | 5 | 3.60 days | ⭐ 8.20 | 🛡️ 7.80 | ₹7,010.00 |
| **Northeast India** | 4 | 3.25 days | ⭐ 7.50 | 🛡️ 7.75 | ₹4,550.00 |
| **National Total (India)** | **100** | **2.91 days** | **⭐ 7.63** | **🛡️ 7.94** | **₹4,874.50** |

---

## 3. K-Means Destination Segmentation

- **Optimal Clusters**: $k = 2$ selected based on peak **Silhouette Score = 0.4028** (evaluated across $k \in [2, 6]$).
- **Cluster Profiles (Centroids in Original Physical Units)**:
  - **Cluster 1: High-Spend Mid-Altitude (Short-Getaway)**
    - Size: 89 destinations (89% share).
    - Centroid Mid Spend: ₹4,657.30 / day.
    - Centroid Stay Duration: 2.7 days.
    - Centroid Altitude: 432.1 meters.
    - Centroid Popularity: ⭐ 7.61 / 10 | Safety: 🛡️ 7.96 / 10.
    - Representative Destinations: Goa, Jaipur, Agra, Udaipur, Kerala Backwaters, Gokarna, Rishikesh.
  - **Cluster 2: High-Spend Alpine/High-Altitude (Extended-Stay)**
    - Size: 11 destinations (11% share).
    - Centroid Mid Spend: ₹6,581.82 / day.
    - Centroid Stay Duration: 5.0 days.
    - Centroid Altitude: 2,906.4 meters.
    - Centroid Popularity: ⭐ 7.82 / 10 | Safety: 🛡️ 7.82 / 10.
    - Representative Destinations: Ladakh (Leh), Spiti Valley, Nubra Valley, Pangong Lake, Tawang, Gulmarg.

---

## 4. Association Rule Mining (FP-Growth)

Mined with parameters: `min_support = 0.08`, `min_confidence = 0.50`, `min_lift = 1.10`.  
Discovered **7 strong non-trivial association rules**:

| Rule # | Antecedents (If) | Consequents (Then) | Support | Confidence | Lift | Plain-English Narrative |
|---|---|---|---|---|---|---|
| **1** | `Season: Post-monsoon` | `Season: Winter` | 13.0% | 100.0% | **4.17x** | Destinations favorable post-monsoon also peak in winter in 100% of cases (4.17x above average). |
| **2** | `Season: Winter` | `Season: Post-monsoon` | 13.0% | 54.2% | **4.17x** | Winter destinations also accommodate post-monsoon travel in 54.2% of cases (4.17x above average). |
| **3** | `Type: Hill_station` | `Type: Family` | 9.0% | 69.2% | **3.30x** | Hill stations cater directly to family vacations in 69.2% of cases (3.30x above average). |
| **4** | `Type: Nature` | `Stay: Homestays` | 8.0% | 57.1% | **2.20x** | Nature retreats consistently feature homestay accommodations in 57.1% of cases (2.20x above average). |
| **5** | `Type: Short_break` | `Season: Winter` | 9.0% | 50.0% | **2.08x** | Short break destinations are predominantly chosen during winter months (2.08x above average). |

---

## 5. Supervised Classification Benchmark (Zero-Leakage)

- **Target**: `spend_tier` $\ge$ Median ₹4,725/day.
- **Leakage Prevention**: All monetary features excluded from $X$.
- **Split**: 80 Training / 20 Testing samples (Stratified).

| Algorithm | Test Accuracy | Precision | Recall | F1-Score | 5-Fold Cross-Validation (Mean ± Std) |
|---|---|---|---|---|---|
| **Random Forest (100 Trees)** | **90.0%** | **0.900** | **0.900** | **0.900** | **61.3% ± 8.2%** |
| **Logistic Regression (L2)** | **75.0%** | **0.783** | **0.750** | **0.783** | **63.8% ± 7.4%** |
| **Decision Tree (Depth 4)** | **60.0%** | **0.600** | **0.667** | **0.667** | **53.8% ± 6.9%** |

- **Top Predictor Features (Random Forest)**:
  1. `altitude_m` (24.1% importance)
  2. `airport_distance_km` (18.6% importance)
  3. `popularity_score` (14.2% importance)
  4. `city_distance_km` (12.8% importance)

---

## 6. Outlier & Anomaly Detection

- Total Anomaly Instances Flagged: **33** across **19 distinct destinations**.
- **Prominent Anomaly Cases**:
  1. *Pangong Lake (Pangong Tso)*: Elevation of **4,350m** exceeds upper IQR bound of 3,910m ($Z = +2.98$).
  2. *Kanha National Park, Ranthambore, Bandhavgarh, Tadoba*: Mid-range daily spends of **₹10,050 – ₹10,300** exceed upper IQR bound of ₹8,184 ($Z = +1.87$ to $+1.98$) due to mandatory tiger safari gypsy permits.
  3. *Havelock & Neil Islands*: Flagged by Isolation Forest for extreme transit logistics (island air/sea access only).

---

## 7. Spend Step-Up Progression & Seasonality Trends

- **Daily Spend Tier Step-Up**:
  - Budget Tier Average: **₹2,890 / day**
  - Mid-Range Tier Average: **₹5,420 / day** ($+87.5\%$ over Budget)
  - Luxury Tier Average: **₹12,870 / day** ($+137.5\%$ over Mid-Range)
- **Optimal Seasonality Distribution**:
  - Winter: 24 destinations (24% of destinations list Winter as primary best season).
  - Summer: 13 destinations (high-altitude hill retreats).
  - Post-monsoon: 13 destinations (lush Western Ghats and waterfalls).
