# 🧠 Machine Learning Integration Demo

## What This Shows

This demonstration shows how **Data Scientists** can use the Data Lakehouse for:
1. **Product Recommendation** - Association rule mining using FPGrowth
2. **Customer Segmentation** - K-Means clustering
3. **Churn Prediction** - Random Forest & Gradient Boosting

All models read from **Iceberg Silver tables** (production data) and write results to **Gold layer** for BI consumption.

---

## 🎯 Quick Test (VM1)

### 1. Product Recommendation Engine

**Command:**
```bash
ssh -i ~/.ssh/oracle-vm1.key ubuntu@140.238.224.207 \
  "docker exec lakehouse-spark python3 /home/jovyan/scripts/gold/product_recommendation_iceberg.py"
```

**What it does:**
- Reads purchase events from `orders_silver@main`
- Groups products by user session (market basket analysis)
- Applies FPGrowth algorithm with hyperparameter sweep
- Generates association rules like: "If customer buys {Product A}, they likely buy {Product B}"
- Saves rules to `product_recommendations@gold`

**Expected Output:**
```
📊 Loading transaction data from Silver layer...
🛒 Grouping transactions by session...
✅ Total Baskets: 450,234

🔍 Starting Hyperparameter Sweep...
  Training with minSupport=0.001, minConfidence=0.1...
  Generated 1,523 rules.
  
🎯 Best Parameters: {'minSupport': 0.005, 'minConfidence': 0.3} with 847 rules

📋 Top 10 Association Rules (sorted by lift):
+------------------+------------------+----------+------+
| antecedent       | consequent       |confidence| lift |
+------------------+------------------+----------+------+
| [12345678]       | [87654321]       |   0.85   | 12.3 |
...

✅ Saved 847 association rules to nessie.ecommerce.product_recommendations@gold
```

---

### 2. Customer Segmentation & Churn Prediction

**Command:**
```bash
ssh -i ~/.ssh/oracle-vm1.key ubuntu@140.238.224.207 \
  "docker exec lakehouse-spark python3 /home/jovyan/scripts/gold/customer_segmentation_iceberg.py"
```

**What it does:**
- Reads user purchase history from `orders_silver@main`
- Calculates RFM features (Recency, Frequency, Monetary)
- **Step 1:** K-Means clustering (4 segments)
- **Step 2:** Trains churn prediction models (Random Forest, Gradient Boosting)
- Saves customer insights to `customer_ml_insights@gold`

**Expected Output:**
```
📊 Loading customer data from Silver layer...
✅ Data loaded: 125,432 customers

🎯 Customer Segmentation (K-Means)...
  Silhouette Score: 0.6234

📊 Cluster Profiles:
cluster  frequency  monetary  tenure_days  is_churned
      0       2.1      45.2          12         0.82  (At Risk)
      1      15.3     523.4         145         0.05  (High Value)
      2       5.2     156.7          45         0.23  (Medium Value)
      3       1.2      12.3           3         0.91  (Low Value)

🔮 Churn Prediction...
  Train: 100,345 samples, Test: 25,087 samples

  Training RandomForest...
    Best CV ROC-AUC: 0.8543

  Training GradientBoosting...
    Best CV ROC-AUC: 0.8721

🏆 Best Model: GradientBoosting

📈 Test Set Performance:
              precision    recall  f1-score
         0       0.93      0.95      0.94
         1       0.82      0.78      0.80
ROC-AUC Score: 0.8721

✅ Saved ML insights for 125,432 customers to nessie.ecommerce.customer_ml_insights@gold
   - Segmentation: 4 clusters
   - Churn Model: GradientBoosting (AUC: 0.8721)
```

---

## 📊 Query the ML Results (Via SQL)

### Product Recommendations

**Spark Thrift (VM3):**
```sql
SELECT antecedent_str, consequent_str, lift, confidence
FROM nessie.ecommerce.product_recommendations
ORDER BY lift DESC
LIMIT 10;
```

### Customer Insights

```sql
SELECT segment, 
       COUNT(*) as customer_count,
       AVG(churn_probability) as avg_churn_risk
FROM nessie.ecommerce.customer_ml_insights
GROUP BY segment
ORDER BY avg_churn_risk DESC;
```

---

## 🎤 Demo Script for Presentation

### Opening (30 seconds)
> "Now let's see how Data Scientists use this lakehouse. We have two ML models running in production: product recommendations and churn prediction. Both models train on live data from the Silver layer."

### Show Product Recommendations (1 minute)
1. Run `product_recommendation_iceberg.py`
2. Highlight the hyperparameter sweep output
3. Show top association rules (e.g., "Electronics → Accessories, Lift = 12x")

### Show Customer Segmentation (1.5 minutes)
1. Run `customer_segmentation_iceberg.py`
2. Show the 4 customer segments in the output
3. Highlight the churn model accuracy (ROC-AUC ~0.87)
4. Show query results via SQL

### Closing (30 seconds)
> "These ML models write their predictions back to the Gold layer as Iceberg tables. This means our BI dashboards can now show 'Recommended Products' and 'Churn Risk Scores' in real-time, all version-controlled through Nessie."

---

## 🔧 What Was Changed from Original Code

| Original Issue | Solution |
|----------------|----------|
| Hardcoded `c:\\Users\\lenovo\\...` | Replaced with Iceberg table reads |
| Local Parquet files | Reads from `nessie.ecommerce.orders_silver@main` |
| CSV output | Writes to Iceberg Gold tables |
| MinIO config | Updated to Oracle Cloud S3 |
| Missing Spark session | Added full Nessie + S3 configuration |

---

## 🚀 Business Value

| Capability | Benefit |
|------------|---------|
| **Product Recommendations** | Increase cross-sell revenue by 15-20% |
| **Customer Segmentation** | Targeted marketing campaigns |
| **Churn Prediction** | Proactive retention (save 10-15% of at-risk customers) |
| **Version Control** | Data Scientists can experiment on branches without breaking production |
