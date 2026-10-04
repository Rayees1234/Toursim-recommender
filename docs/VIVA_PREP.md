# DMDW Comprehensive Viva Preparation Guide

**Project**: Tourism Data Warehouse and Data Mining System (DMDW)  
**Target**: B.Tech CSE Viva Voce & Laboratory Examination  
**Document**: `docs/VIVA_PREP.md`

---

### Q1: What is a Data Warehouse, and how does it differ from an Operational Database (OLTP)?
**Answer**: An operational database (OLTP) is optimized for high-concurrency, fast ACID transactions (inserts, updates, deletes) on normalized schemas (3NF). A Data Warehouse (OLAP) is a subject-oriented, integrated, time-variant, non-volatile repository designed for complex analytical queries and aggregations across historical data, typically modeled in dimensional star or snowflake schemas.

### Q2: Why did you choose a Star Schema over a Snowflake Schema for this project?
**Answer**: Star schema has completely denormalized dimension tables directly connected to a central fact table. This minimizes the number of expensive multi-table `JOIN` operations, maximizing analytical query throughput. Snowflake normalizes dimensions into sub-dimensions (saving minimal disk space), but significantly slows down OLAP queries. In tourism analytics, query performance and simplicity vastly outweigh storage concerns.

### Q3: What is the declared Grain of your Fact Table?
**Answer**: Our declared fact grain is *"One row per tourist destination observation snapshot, representing its verified geographic location, infrastructure metrics, duration requirements, and multi-tier daily expenditure profile."* Defining the grain up front ensures every measure (spend, duration, ratings) has an unambiguous physical meaning and prevents accidental double-counting.

### Q4: What is the difference between an Additive, Semi-Additive, and Non-Additive measure? Give examples from your project.
**Answer**:
- **Additive**: Can be summed across all dimensions (e.g., total trip expenditure, count of destinations).
- **Semi-Additive**: Can be summed across some dimensions but not others (e.g., daily spend cannot be summed across days, but can be averaged across regions).
- **Non-Additive**: Cannot be meaningfully added across any dimension (e.g., `popularity_score`, `safety_rating`, ratios, and percentages).

### Q5: Why do you use Surrogate Integer Keys instead of Natural Keys?
**Answer**: Natural keys (like `destination_name` or alphanumeric codes) can change over time, contain duplicates (e.g., Varanasi appearing in multiple circuit records), or have high byte storage overhead. Integer surrogate keys (`destination_key = 1, 2, ...`) provide fast single-column indexing, decouple warehouse data from source system changes, and standardize referential integrity across all dimension tables.

### Q6: How does your warehouse handle missing values without generating orphan facts?
**Answer**: Every dimension table contains an "Unknown" member row (surrogate key = `0` or `-1`). If an incoming record has a missing or unresolvable foreign key, it links to key `0` rather than storing a `NULL`. This guarantees 100% referential integrity with zero orphan fact records.

### Q7: How did you specifically handle missing railway distances for island destinations?
**Answer**: Exactly 8 destination records had null railway distances. Rather than blindly dropping the destinations (which would lose major hubs like Havelock Island) or imputing `0` (which would falsely imply a station at the beach), we imputed `distance = -1`, assigned station name `"No Railway Network (Island Territory)"`, and added a boolean flag `has_railway_access = 0` to `dim_connectivity`.

### Q8: What are the 5 core OLAP operations implemented in your project?
**Answer**:
1. **Roll-up**: Aggregates metrics along a dimension hierarchy (e.g., Destination $\rightarrow$ State $\rightarrow$ Region $\rightarrow$ Country).
2. **Drill-down**: Disaggregates higher-level summaries into detailed records (e.g., Region $\rightarrow$ individual State & District destinations).
3. **Slice**: Fixes one dimension to a single value (e.g., `accessibility = 'Easy'`).
4. **Dice**: Filters across two or more dimensions simultaneously (e.g., `region = 'North India'` AND `safety_rating >= 8` AND `spend <= ₹5,000`).
5. **Pivot**: Rotates the multi-dimensional cube to generate cross-tabulated matrices (e.g., Region as Rows, Accessibility as Columns, Average Spend as Measure).

### Q9: How is SQL `GROUP BY ... WITH ROLLUP` utilized in OLAP?
**Answer**: `WITH ROLLUP` computes hierarchical subtotals and grand totals in a single database pass, eliminating the need to write multiple separate `UNION ALL` aggregation queries.

### Q10: What is Data Leakage in Machine Learning, and how did you prevent it?
**Answer**: Data leakage occurs when information from the target variable is inadvertently included in the feature set $X$. In our project, the target is `spend_tier` (High vs Moderate/Budget). Predicting high spend using total spend, accommodation cost, or food cost would be severe data leakage. We strictly excluded all financial cost columns from $X$, forcing the algorithms to predict spend solely from infrastructure, geography, altitude, stay duration, and ratings.

### Q11: Why is feature standardization mandatory before running K-Means Clustering?
**Answer**: K-Means uses Euclidean distance. If features have vastly different scales (e.g., `altitude_m` ranges up to 4,350m, whereas `ideal_duration_days` ranges between 0.5 and 7), the feature with the largest numerical range will dominate the distance calculations by a factor of 1,000×. Z-Score standardization (`StandardScaler`) scales all features to mean 0 and variance 1.

### Q12: How did you determine the optimal number of clusters ($k$)?
**Answer**: We combined the **Elbow Method** (tracking the drop in Within-Cluster Sum of Squares / Inertia) with **Silhouette Analysis** (measuring how tightly grouped points are within clusters compared to neighboring clusters) over $k \in [2, 6]$. The silhouette score peaked at **0.4028** for $k=2$.

### Q13: How were cluster names generated without hardcoding?
**Answer**: The centroids were inversely transformed back into original physical units. A programmatic heuristic compared the centroid's spend, duration, and altitude against the dataset's global medians. If centroid spend exceeded $1.1 \times$ median, it was labeled `"High-Spend"`; if altitude exceeded 1,500m, it was labeled `"Alpine/High-Altitude"`. The label was composed dynamically: `f"{spend_desc} {alt_desc} ({dur_desc})"`.

### Q14: What is the difference between the Apriori and FP-Growth algorithms?
**Answer**: Apriori uses a candidate-generation-and-test approach ($L_k \rightarrow C_{k+1}$) requiring multiple sequential scans of the entire transactional dataset, which is computationally expensive ($O(2^m)$). FP-Growth compresses the dataset into an in-memory **FP-Tree** (Frequent Pattern Tree) and mines frequent itemsets using divide-and-conquer conditional pattern bases without candidate generation, making it dramatically faster.

### Q15: What do Support, Confidence, and Lift represent in Association Rule Mining?
**Answer**:
- **Support**: Probability that itemsets $X$ and $Y$ occur together: $P(X \cap Y)$.
- **Confidence**: Conditional probability that $Y$ occurs given that $X$ has occurred: $P(Y | X)$.
- **Lift**: Measure of dependence: $\frac{P(X \cap Y)}{P(X) \cdot P(Y)}$.
  - Lift = 1: $X$ and $Y$ are independent.
  - Lift > 1: Positive association ($X$ and $Y$ occur together more frequently than expected by chance).
  - Lift < 1: Negative association (substitutes).

### Q16: How does Isolation Forest detect outliers compared to traditional IQR?
**Answer**: IQR is a univariate method that flags values exceeding $Q_3 + 1.5 \times \text{IQR}$ along a single dimension. Isolation Forest is a multivariate ensemble method: it isolates observations by randomly selecting features and split values. Anomalous observations require fewer random partitions to isolate, appearing closer to the root of the isolation trees (shorter average path lengths).

### Q17: Why did Random Forest outperform Decision Tree and Logistic Regression?
**Answer**: A single Decision Tree has high variance and easily overfits small datasets. Random Forest builds an ensemble of 100 decorrelated decision trees using bootstrap aggregating (bagging) and random feature subspace selection, significantly reducing variance while capturing non-linear feature interactions (such as altitude combined with airport distance).

### Q18: What is Idempotency in an ETL pipeline, and why is it essential?
**Answer**: An idempotent operation produces the exact same result whether executed once or multiple times ($f(f(x)) = f(x)$). In our pipeline, re-running `python run_pipeline.py` cleanly replaces or updates the tables without producing duplicate rows, primary key collisions, or broken surrogate links.

### Q19: What is the purpose of Bridge Tables in this Data Warehouse?
**Answer**: Destinations have multi-valued attributes (e.g., a destination can offer 5 different trip types and 10 different activities). Storing multiple values in a single column violates First Normal Form (1NF). Creating bridge tables (`bridge_destination_trip_type`, `bridge_destination_activity`) normalizes many-to-many relationships while enabling rapid index-driven filtering and market basket mining.

### Q20: What is the Dual-Engine Database Architecture implemented in this project?
**Answer**: The project includes a database adapter (`sql/database.py`) that prioritizes MySQL 8.0 when configured in `.env`. If the MySQL service is stopped or permissions are restricted, it seamlessly falls back to a local SQLite warehouse with identical Star Schema DDL, constraints, views, and queries, guaranteeing zero crashes during live demonstrations.
