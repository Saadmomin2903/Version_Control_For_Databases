# 📊 BI & Visualization Demo (Apache Superset + Trino)

## What This Shows

This demonstration shows how **Business Analysts** and **Stakeholders** can consume high-value insights from the **Gold Layer** using **Apache Superset** powered by **Trino**.

Key capabilities demonstrated:
1. **High-Performance Querying**: Leveraging **Trino v451** as a distributed SQL engine over the Iceberg Lakehouse.
2. **ML Insights Visualization**: Creating charts from customer segmentation and product recommendation data.
3. **Decoupled Architecture**: Accessing Iceberg tables stored in Oracle Object Storage via Nessie catalog, completely bypassing legacy Spark Thrift issues.

---

## 🏗️ Technical Setup (Day 2 Recap)

### 1. Environment Deployment (VM1)
We use a custom-built Superset image that includes all necessary database drivers (`sqlalchemy-trino`, `pyhive`, etc.) pre-baked to ensure stability.

**Deployment Command:**
```bash
ssh -i ~/.ssh/oracle-vm1.key ubuntu@140.238.224.207 \
  "docker-compose -f ~/docker-compose-superset.yml up -d && \
   docker-compose -f ~/docker-compose-trino.yml up -d"
```

### 2. High-Performance Query Layer: Trino
To solve driver compatibility issues with legacy Hive/Spark Thrift, we deployed **Trino v451**. Trino provides native support for Nessie and Iceberg, allowing for rapid visualization of millions of rows.

---

## 🎯 Demo Steps: Connecting to Data

### 1. Accessing the UI
1. Open your browser and navigate to `http://140.238.224.207:8088`.
2. Login with credentials (default: `admin` / `admin`).

> [!NOTE]
> Ensure port `8088` (Superset) and `8090` (Trino) are open in the Oracle Cloud VCN Ingress Rules.

### 2. Adding the Trino Connection
1. Go to **Settings** -> **Database Connections**.
2. Click **+ Database**.
3. Select **Trino** from the dropdown.
4. Use the following Connection URI:
   ```text
   trino://trino@lakehouse-trino:8080/iceberg
   ```
   *(Note: `lakehouse-trino` is the internal Docker network name; uses port 8080 inside the network.)*
5. **Display Name**: `Lakehouse_Trino_Iceberg`
6. Click **Test Connection** -> **Finish**.

> [!TIP]
> This connects Superset to the **Trino** engine, which directly queries the Iceberg tables Managed by **Nessie**.

---

# � BI Dashboard Masterclass (Superset + Trino)

## 🏗️ Phase 1: Building Virtual Data (SQL Lab)

To build a professional dashboard, we first convert raw ML outputs into business-friendly labels. Go to **SQL Lab** and create these two "Virtual Datasets":

### 1. The Customer Persona View
**SQL**:
```sql
SELECT *,
    CASE 
        WHEN cluster = 4 THEN 'Champions 🏆'
        WHEN cluster = 3 THEN 'Loyal Customers ⭐'
        WHEN cluster = 0 THEN 'Regulars 👍'
        WHEN cluster = 1 THEN 'Potential Loyalists 📈'
        WHEN cluster = 2 THEN 'Casual Shoppers 💤'
        ELSE 'New/Unknown'
    END as customer_segment
FROM iceberg.ecommerce.customer_segments_ml
```
*Click **Save -> Save Dataset** as `labeled_customer_segments`.*

### 2. The Churn vs Value Heatmap
**SQL**:
```sql
SELECT 
    c.customer_id,
    c.churn_probability as churn_score,
    CASE 
        WHEN c.churn_probability >= 0.7 THEN 'High Risk 🔴'
        WHEN c.churn_probability >= 0.4 THEN 'Medium Risk 🟡'
        ELSE 'Low Risk 🟢'
    END as risk_label,
    v.predicted_clv_12m as predicted_clv,
    CASE 
        WHEN v.predicted_clv_12m >= 2000 THEN 'Platinum 💎'
        WHEN v.predicted_clv_12m >= 1000 THEN 'Gold 🥇'
        WHEN v.predicted_clv_12m >= 500 THEN 'Silver 🥈'
        ELSE 'Bronze 🥉'
    END as tier_label
FROM iceberg.ecommerce.churn_predictions_ml c
JOIN iceberg.ecommerce.clv_predictions_ml v ON c.customer_id = v.customer_id
```
*Click **Save -> Save Dataset** as `churn_clv_analytics`.*

### 3. Product Recommendation Names
**SQL**:
```sql
SELECT 
    r.source_product as source_id,
    COALESCE(s.brand || ' (' || s.category_code || ')', 'Unknown ID: ' || CAST(r.source_product AS VARCHAR)) as source_product_name,
    r.recommended_product as recommended_id,
    COALESCE(rec.brand || ' (' || rec.category_code || ')', 'Unknown ID: ' || CAST(r.recommended_product AS VARCHAR)) as recommended_product_name,
    r.confidence,
    r.lift
FROM iceberg.ecommerce.product_recommendations_ml r
LEFT JOIN iceberg.ecommerce.products_catalog_gold s ON r.source_product = s.product_id
LEFT JOIN iceberg.ecommerce.products_catalog_gold rec ON r.recommended_product = rec.product_id
```
*Click **Save -> Save Dataset** as `labeled_recommendations`.*

---

## 📈 Phase 2: Building the Charts

Open the **Charts** view and click **+ Chart**. Follow these "Recipes":

### 📊 KPI 1: Customer Segment Distribution (Pie Chart)
*   **Dataset**: `labeled_customer_segments`
*   **Metric**: `COUNT(*)`
*   **Group by**: `customer_segment`
*   **Insight**: This shows the relative weight of your "Champions" vs "At Risk" users.

### 📊 KPI 2: Customer Lifetime Value Tiering (Bar Chart)
*   **Dataset**: `churn_clv_analytics`
*   **X-Axis**: `tier_label`
*   **Metric**: `AVG(predicted_clv)`
*   **Color**: Leave empty.
*   **Insight**: Quantifies exactly how much revenue each tier (Gold, Silver, etc.) is projected to bring.

### 🔥 KPI 3: Churn vs Value (Heatmap)
*   **Dataset**: `churn_clv_analytics`
*   **X-Axis**: `risk_label`
*   **Y-Axis**: `tier_label`
*   **Metric**: `COUNT(*)`
*   **Insight**: Instantly see if your High-Value (Platinum) customers are slipping into the High-Risk zone.

### 📊 KPI 4: High-Risk Churn List (Table)
*   **Dataset**: `churn_clv_analytics`
*   **Dimensions**: `customer_id`, `risk_label`, `churn_score`
*   **Filters**: `risk_label` = `High Risk 🔴`
*   **Sort by**: `churn_score` DESC
*   **Insight**: An actionable list of customers for the Marketing team.

### 🛒 KPI 5: Smart Product Cross-Sell (Table)
*   **Dataset**: `labeled_recommendations`
*   **Dimensions**: `source_product_name`, `recommended_product_name`
*   **Metric**: `MAX(lift)`
*   **Filter**: `lift > 5`
*   **Sort by**: `lift` DESC
*   **Insight**: Identifies "Golden Pairs"—products that, when bought together, significantly increase basket size.

### 📈 KPI 6: Total Sales Forecast Trend (Time-series)
*   **Dataset**: `daily_sales_gold` (Add this as a physical dataset)
*   **Time Column**: `order_date`
*   **Metric**: `SUM(total_revenue)`
*   **Visual**: Line Chart
*   **Insight**: Shows daily revenue health.

### 🛡️ KPI 7: Data Quality Health Check (Distribution)
*   **Dataset**: `orders_silver` (Add this as a physical dataset)
*   **Metric**: `COUNT(*)`
*   **Group by**: `data_quality_score`
*   **Visual**: Bar Chart
*   **Insight**: Proves to stakeholders that our **Version Control for Databases** is working by showing exactly how many rows are high-quality (Score 100) vs flagged.

---

## 🚀 Phase 3: The Board Presentation

1.  Go to **Dashboards** -> **+ Dashboard**.
2.  Drag all your charts from the right-hand panel onto the canvas.
3.  **Add a Header**: "Lakehouse ML Business Intelligence 360°"
4.  **Add a Filter Box**: Allow users to filter the entire dashboard by `customer_segment` or `value_tier`.

---

## 🏆 Final Result: A Competitive Edge
Your dashboard is no longer just a "Report." It is a tool for **Prescriptive Analytics**:
*   **Marketing** uses it to find VIPs.
*   **Sales** uses it to see Churn risk.
*   **Supply Chain** uses it to see product associations.

---

## 🔌 Connection Troubleshooting

| Issue | Root Cause | Fix |
|---|---|---|
| `ResolutionError` | Network Isolation. | Ensure `superset_app` and `lakehouse-trino` are on the `lakehouse-network`. |
| `TrinoEngineSpec` | Missing Driver. | Verify `sqlalchemy-trino` is installed inside `/app/.venv/`. |
| `S3 Access Denied` | Config Error. | Verify OCI keys in `trino/etc/catalog/iceberg.properties`. |

---

## 🏆 Business Value Explained
> "By moving from Spark Thrift to Trino, we provide a lightning-fast, highly compatible visualization layer. Stakeholders can now 'Self-Serve' insights from the 300M+ recorded events in real-time, bridging the gap between raw Big Data and actionable business strategy."

