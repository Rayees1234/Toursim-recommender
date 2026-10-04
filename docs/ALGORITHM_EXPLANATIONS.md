# Data Mining Algorithms & Methodologies

**Project**: Tourism Data Warehouse and Data Mining System (DMDW)  
**Target**: B.Tech CSE Academic Defense & Laboratory Evaluation  
**Document**: `docs/ALGORITHM_EXPLANATIONS.md`

---

## 1. Unsupervised Segmentation: K-Means Clustering

### 1.1 Objective & Domain Context
To discover organic clusters of tourist destinations based on multi-dimensional travel requirements, infrastructure, and expenditure patterns, enabling destination management organizations (DMOs) to tailor packages.

### 1.2 Feature Selection & Scaling
We select 6 standardized continuous features:
1. `mid_daily_avg`: Baseline daily expenditure in INR.
2. `ideal_duration_days`: Recommended stay duration.
3. `popularity_score`: Tourist preference index (1–10).
4. `safety_rating`: Perceived safety rating (1–10).
5. `altitude_m`: Physical elevation above sea level.
6. `airport_distance_km`: Logistics proximity indicator.

**Standardization**: K-Means relies on Euclidean distance:
$$d(x, c) = \sqrt{\sum_{i=1}^{p} (x_i - c_i)^2}$$
Because `altitude_m` ranges up to 4,350m while `ideal_duration_days` ranges between 0.5 and 7, unscaled features would allow altitude to dominate distance calculations by several orders of magnitude. We apply Z-Score standardization via `StandardScaler`:
$$z = \frac{x - \mu}{\sigma}$$
yielding zero mean and unit variance across all $p=6$ features.

### 1.3 Optimization: Elbow Method & Silhouette Analysis
We iterate over $k \in [2, 6]$ with fixed `random_state=42` and `n_init=10`:
1. **Inertia (Within-Cluster Sum of Squares - WCSS)**:
   $$\text{WCSS} = \sum_{k=1}^{K} \sum_{x \in C_k} \|x - \mu_k\|^2$$
2. **Silhouette Coefficient**:
   $$s(i) = \frac{b(i) - a(i)}{\max(a(i), b(i))}$$
   where $a(i)$ is the mean intra-cluster distance and $b(i)$ is the mean nearest-cluster distance.
   - For $k=2$, Silhouette Score reaches **0.4028** (optimal separation between high-altitude alpine extended stays vs mid/lowland getaways).

### 1.4 Programmatic Naming Algorithm
To strictly obey the non-negotiable rule against hardcoding, cluster centroids $\mu_k$ are inversely transformed to raw units and evaluated relative to global medians:
- If $\mu_{\text{spend}} > 1.1 \times \text{Median}$: `"High-Spend"`
- If $\mu_{\text{duration}} > \text{Median}$: `"Extended-Stay"`
- If $\mu_{\text{altitude}} > 1500\text{m}$: `"Alpine/High-Altitude"`
- Generated Name: `f"{spend_desc} {alt_desc} ({dur_desc})"`

---

## 2. Market Basket Analysis: Association Rule Mining (FP-Growth)

### 2.1 Problem Formulation
Each destination is treated as a transaction basket containing discrete travel attributes:
$$\text{Basket}_i = \{\text{Trip Types}\} \cup \{\text{Accommodations}\} \cup \{\text{Best Seasons}\} \cup \{\text{Top Activities}\}$$

### 2.2 Algorithm: FP-Growth vs. Apriori
We utilize **FP-Growth (Frequent Pattern Growth)** as the primary mining engine:
- Unlike Apriori, which generates exponential candidate itemsets via costly multi-pass database scans ($O(2^m)$), FP-Growth compresses the transactional database into an in-memory **FP-Tree** (Frequent Pattern Tree) and mines patterns through recursive conditional pattern bases without candidate generation.
- Default threshold: `min_support = 0.08` ($N=100$, minimum 8 destination occurrences).

### 2.3 Evaluation Metrics & Pruning
Given an association rule $X \longrightarrow Y$:
1. **Support**:
   $$\text{Support}(X \cup Y) = \frac{\text{Count}(X \cup Y)}{N}$$
2. **Confidence**:
   $$\text{Confidence}(X \longrightarrow Y) = \frac{\text{Support}(X \cup Y)}{\text{Support}(X)}$$
3. **Lift**:
   $$\text{Lift}(X \longrightarrow Y) = \frac{\text{Confidence}(X \longrightarrow Y)}{\text{Support}(Y)} = \frac{P(X \cap Y)}{P(X) \cdot P(Y)}$$
   - $\text{Lift} > 1.0$: Positive dependence ($X$ and $Y$ occur together significantly more often than random chance).
   - $\text{Lift} \le 1.0$: Independent or negatively associated (pruned out as trivial).

---

## 3. Supervised Classification & Zero-Leakage Policy

### 3.1 Target Definition & Leakage Prevention
- **Target**: `spend_tier` $\in \{0, 1\}$ (0 = Moderate/Budget, 1 = High Spend) derived from median split of mid-range daily spend (median = ₹4,725/day).
- **Leakage Prevention**:
  > **Crucial Rule**: Predicting spend using total spend, accommodation spend, or food spend is a fatal methodological error (data leakage).  
  To prevent leakage, all monetary features (`budget_*`, `mid_*`, `luxury_*`, `cost_*`) are 100% eliminated from the predictor matrix $X$.
- **Predictors ($X$)**: Stay duration (`min_days`, `ideal_days`, `max_days`), physical geography (`altitude_m`, `region`), logistics (`airport_dist_km`, `city_dist_km`, `has_railway_access`), governance (`permits_required`), and consumer scores (`popularity_score`, `safety_rating`).

### 3.2 Model Comparison & Validation Strategy
1. **Strict Train/Test Partitioning**:
   - Stratified 80/20 train/test split executed **before** any preprocessing.
   - `StandardScaler` and `OneHotEncoder` fitted exclusively on the 80 training samples.
2. **Algorithms Benchmarked**:
   - **Random Forest**: Ensemble of 100 decorrelated decision trees reducing variance.
   - **Logistic Regression**: Linear log-odds estimator with L2 regularization.
   - **Decision Tree (CART)**: Interpretable tree with Gini impurity splitting.
3. **Validation**: 5-Fold Stratified Cross-Validation on training data + Out-of-sample Test Set evaluation (Accuracy, Precision, Recall, F1, Confusion Matrix).

---

## 4. Anomaly & Outlier Detection

### 4.1 Univariate Detection: Interquartile Range (IQR) & Z-Score
1. **IQR Method**:
   $$\text{IQR} = Q_3 - Q_1$$
   $$\text{Lower Bound} = Q_1 - 1.5 \cdot \text{IQR}, \quad \text{Upper Bound} = Q_3 + 1.5 \cdot \text{IQR}$$
2. **Z-Score Method**:
   $$Z_i = \frac{x_i - \bar{x}}{s}, \quad \text{Flagged if } |Z_i| > 2.5$$

### 4.2 Multivariate Detection: Isolation Forest
- An unsupervised ensemble method that isolates anomalies by randomly selecting a feature and randomly selecting a split value between the minimum and maximum values of that feature.
- Because anomalies have distinct attribute distributions, they are isolated closer to the root of the trees (shorter average path length $h(x)$).
- Anomaly score:
  $$s(x, n) = 2^{-\frac{E(h(x))}{c(n)}}$$
  where $c(n)$ is the average path length of unsuccessful searches in a Binary Search Tree.

---

## 5. Content-Based Tourism Recommender

### 5.1 Distance & Match Formulation
Given user constraints $\{B_{\text{max}}, D_{\text{req}}, R_{\text{pref}}, T_{\text{pref}}, S_{\text{pref}}\}$:
1. **Budget Feasibility**: Strict constraint $\text{Daily Spend} \le B_{\text{max}}$.
2. **Duration Penalty**: Proximity score based on absolute deviation $|D_{\text{ideal}} - D_{\text{req}}|$.
3. **Categorical Affinity**:
   - $+35$ points if destination trip types contain $T_{\text{pref}}$.
   - $+25$ points if destination optimal season contains $S_{\text{pref}}$.
4. **Quality Weighting**: Additive terms for `popularity_score` and `safety_rating`.
5. Destinations ranked descending on composite match score $\in [0, 100\%]$.
