# 5–7 Minute Live Demonstration Script

**Project**: Tourism Data Warehouse and Data Mining System (DMDW)  
**Target**: B.Tech CSE Viva Voce & Laboratory Presentation  
**Document**: `docs/DEMO_SCRIPT.md`

---

## Presentation Breakdown

### ⏱️ Minute 1: Introduction & Pipeline Architecture
- **Speaker Action**: Open the Executive Dashboard (`http://localhost:5000`).
- **Script**:
  > *"Good morning respected evaluators. Today I am presenting our Tourism Data Warehouse and Data Mining System. We have engineered an end-to-end pipeline covering raw data ingestion, automated cleaning, star-schema warehouse modeling, full OLAP operations, and multiple machine learning modules exposed through a Flask API and an interactive glassmorphism dashboard."*
- **Key Visuals to Show**:
  - Point to the live database engine indicator in the bottom-left sidebar: `Engine: SQLITE / MYSQL`.
  - Highlight the 5 core KPI cards: Total Destinations (100), Average Mid Spend (₹4,875/day), Recommended Duration (2.9 days), and Safety Index (7.9/10).

---

### ⏱️ Minute 2: Warehouse Modeling & Row Reconciliation
- **Speaker Action**: Click on the **"Data Warehouse"** tab.
- **Script**:
  > *"Our dimensional model strictly implements a Star Schema with a declared grain of: 'One row per destination observation snapshot'. We have 1 primary fact table (`fact_destination_metrics`), 5 master dimensions, and 4 bridge tables to handle multi-valued attributes like activities and seasons in First Normal Form."*
- **Live Demo Action**:
  - Show the **Warehouse Table Catalog** table showing live row counts: 100 fact rows, 101 destinations, 79 geographies.
  - Click **"Preview"** on `fact_destination_metrics` to display live database rows.
  - State: *"We enforce 100% row reconciliation: 100 source records produce exactly 100 cleaned records and 100 fact rows with zero orphan facts."*

---

### ⏱️ Minute 3: Real OLAP Operations in Action
- **Speaker Action**: Click on the **"OLAP Operations"** tab.
- **Script**:
  > *"Rather than hardcoded summaries, our backend executes parameterized SQL queries covering all 5 canonical OLAP operations."*
- **Live Demo Actions**:
  1. Click **"1. Roll-up (Geography)"**: Show aggregation up from Destination to Region with subtotals and grand totals.
  2. Click **"2. Drill-down (South India)"**: Show granular breakdown into Karnataka, Kerala, Tamil Nadu, and individual destinations.
  3. Click **"3. Slice (Easy Access)"**: Show filtered sub-cube isolating destinations with easy accessibility.
  4. Click **"4. Dice (North + Safe + Budget)"**: Show multi-dimensional filtering simultaneously constraining Region, Safety, and Spend.
  5. Click **"5. Pivot (Region x Access)"**: Show the dynamic cross-tabulation matrix calculating Average Spend across Regions and Accessibility tiers.

---

### ⏱️ Minute 4: Data Mining — K-Means & Association Rules
- **Speaker Action**: Click on the **"K-Means Segmentation"** tab.
- **Script**:
  > *"Our data mining models read directly from warehouse joined views. For K-Means, we evaluated continuous scaled features using both the Elbow Method and Silhouette Analysis, discovering optimal separation at k=2 with a silhouette score of 0.4028. Notice that cluster titles like 'High-Spend Alpine/High-Altitude' are generated programmatically by evaluating centroid coordinates relative to dataset medians—zero hardcoded strings."*
- **Speaker Action**: Click on the **"Association Rules"** tab.
- **Script**:
  > *"Next, we used FP-Growth on warehouse bridge tables to perform Market Basket Analysis. For instance, Rule #3 shows that destinations tagged as 'Hill Station' also feature 'Family' travel in 69.2% of cases, with a Lift of 3.30x over random baseline."*

---

### ⏱️ Minute 5: Supervised Classification (Zero-Leakage) & Outliers
- **Speaker Action**: Click on the **"Spend Classification"** tab.
- **Script**:
  > *"For supervised classification, we predict whether a destination falls into the High-Spend tier using an 80/20 stratified split. We strictly enforced a zero-leakage policy: all monetary cost variables are 100% excluded from features. We benchmarked Random Forest, Logistic Regression, and Decision Trees. Random Forest achieved 90.0% test accuracy and an F1-score of 0.900, with altitude and airport proximity as top predictors."*
- **Speaker Action**: Click on the **"Outlier Detection"** tab.
- **Script**:
  > *"We combined univariate IQR bounds with multivariate Isolation Forest. Pangong Lake is flagged for extreme elevation (4,350m), while Kanha and Ranthambore are flagged for safari permit expenditure spikes."*

---

### ⏱️ Minute 6: Personalized Recommender Demo
- **Speaker Action**: Click on the **"Trip Recommender"** tab.
- **Script**:
  > *"Finally, we built an interactive content-based trip recommender. Let us enter a daily budget of ₹5,000, 3 days duration, preferred style 'Beach', and season 'Winter'."*
- **Live Demo Action**: Click **"Find Recommended Destinations"**.
- **Script**:
  > *"The engine computes multi-dimensional match scores in real time, recommending top destinations (such as Goa, Gokarna, Varkala) with calculated match percentages and personalized rationales."*

---

### ⏱️ Minute 7: Conclusion & Summary
- **Script**:
  > *"To summarize: the system is completely idempotent via `python run_pipeline.py`, maintains complete referential integrity, contains zero hardcoded numbers, and includes automated test coverage with 32 passing tests. Thank you, and I am now ready for your viva questions."*
