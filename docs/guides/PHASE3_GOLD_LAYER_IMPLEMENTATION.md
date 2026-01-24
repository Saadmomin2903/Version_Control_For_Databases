# Phase 3: Gold Layer Implementation Guide

This guide details the steps to create the **Gold Layer**, which consists of aggregated, business-ready tables optimized for analytics and reporting.

---

## 🎯 Objective

Create the following aggregated tables in the `nessie.ecommerce` namespace:
1.  **`daily_sales_summary`**: High-level daily metrics.
2.  **`brand_performance`**: Sales performance by brand.
3.  **`category_analytics`**: Funnel analysis by category.
4.  **`customer_segments`**: RFM (Recency, Frequency, Monetary) analysis.

---

## 🛠️ Step 1: Preparation

Ensure you have the `silver` data ready. We will create these tables directly on the `main` branch (or a `gold` feature branch if you prefer strict WAP, but for simplicity here we assume `main` or a feature branch that merges to `main`).

### 1.1 Start Spark Session
Use the standard configuration found in `docs/guides/HOW_TO_QUERY_DATA.md`.

```python
# Standard Spark Setup (if running in script/notebook)
# Ensure Nessie config is set to reference the correct branch (e.g. 'main')
```

---

## 📊 Step 2: Implement Aggregations

Create a new script `scripts/gold/create_gold_tables.py` or use a Jupyter notebook.

### 2.1 Daily Sales Summary

Aggregates sales data by day.

```sql
CREATE OR REPLACE TABLE nessie.ecommerce.daily_sales_summary USING iceberg AS
SELECT 
    CAST(event_time AS DATE) as date,
    ROUND(SUM(price), 2) as total_revenue,
    COUNT(CASE WHEN event_type = 'purchase' THEN 1 END) as total_orders,
    COUNT(DISTINCT user_id) as unique_customers,
    ROUND(AVG(CASE WHEN event_type = 'purchase' THEN price END), 2) as avg_order_value
FROM nessie.ecommerce.orders_silver
WHERE event_type = 'purchase'
GROUP BY 1
ORDER BY 1 DESC;
```

### 2.2 Brand Performance

Analyzes how different brands are performing.

```sql
CREATE OR REPLACE TABLE nessie.ecommerce.brand_performance USING iceberg AS
SELECT 
    brand,
    ROUND(SUM(CASE WHEN event_type = 'purchase' THEN price ELSE 0 END), 2) as total_revenue,
    COUNT(CASE WHEN event_type = 'purchase' THEN 1 END) as total_purchases,
    COUNT(CASE WHEN event_type = 'view' THEN 1 END) as total_views,
    COUNT(DISTINCT user_id) as unique_customers,
    ROUND(
        COUNT(CASE WHEN event_type = 'purchase' THEN 1 END) * 100.0 / 
        NULLIF(COUNT(CASE WHEN event_type = 'view' THEN 1 END), 0), 2
    ) as conversion_rate
FROM nessie.ecommerce.orders_silver
WHERE brand IS NOT NULL
GROUP BY 1
ORDER BY total_revenue DESC;
```

### 2.3 Customer Segments (RFM)

Classifies customers based on their purchasing behavior.

```sql
CREATE OR REPLACE TABLE nessie.ecommerce.customer_segments USING iceberg AS
WITH rfm_stats AS (
    SELECT 
        user_id,
        MAX(event_time) as last_purchase_date,
        COUNT(*) as total_purchases,
        SUM(price) as total_spend
    FROM nessie.ecommerce.orders_silver
    WHERE event_type = 'purchase'
    GROUP BY user_id
)
SELECT 
    user_id,
    total_purchases,
    ROUND(total_spend, 2) as total_spend,
    last_purchase_date,
    CASE 
        WHEN total_spend > 1000 AND total_purchases > 10 THEN 'VIP'
        WHEN total_spend > 500 THEN 'Gold'
        WHEN total_purchases > 5 THEN 'Regular'
        ELSE 'New/Low'
    END as customer_segment
FROM rfm_stats;
```

---

## ✅ Step 3: Verification

Run the following queries to verify the data:

1.  **Check Row Counts**:
    ```sql
    SELECT 'daily_sales' as table, COUNT(*) FROM nessie.ecommerce.daily_sales_summary
    UNION ALL
    SELECT 'brand_perf', COUNT(*) FROM nessie.ecommerce.brand_performance
    UNION ALL
    SELECT 'cust_seg', COUNT(*) FROM nessie.ecommerce.customer_segments;
    ```

2.  **Sample Data**:
    ```sql
    SELECT * FROM nessie.ecommerce.daily_sales_summary LIMIT 5;
    ```

---

## 📝 Script Implementation

Create the file `scripts/gold/create_gold_tables.py` with the following executable code:

```python
from pyspark.sql import SparkSession
import sys

def create_spark_session():
    return SparkSession.builder \
        .appName("Gold_Layer_Creation") \
        .config("spark.jars.packages", "org.apache.iceberg:iceberg-spark-runtime-3.3_2.12:1.3.1,org.projectnessie.nessie-integrations:nessie-spark-extensions-3.3_2.12:0.67.0,software.amazon.awssdk:bundle:2.17.178") \
        .config("spark.sql.extensions", "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions,org.projectnessie.spark.extensions.NessieSparkSessionExtensions") \
        .config("spark.sql.catalog.nessie", "org.apache.iceberg.spark.SparkCatalog") \
        .config("spark.sql.catalog.nessie.uri", "http://nessie:19120/api/v1") \
        .config("spark.sql.catalog.nessie.ref", "main") \
        .config("spark.sql.catalog.nessie.authentication.type", "NONE") \
        .config("spark.sql.catalog.nessie.catalog-impl", "org.apache.iceberg.nessie.NessieCatalog") \
        .config("spark.sql.catalog.nessie.warehouse", "s3a://lakehouse/warehouse") \
        .config("spark.sql.catalog.nessie.io-impl", "org.apache.iceberg.aws.s3.S3FileIO") \
        .config("spark.sql.catalog.nessie.s3.endpoint", "http://minio:9000") \
        .config("spark.hadoop.fs.s3a.access.key", "admin") \
        .config("spark.hadoop.fs.s3a.secret.key", "password123") \
        .config("spark.hadoop.fs.s3a.endpoint", "http://minio:9000") \
        .config("spark.hadoop.fs.s3a.path.style.access", "true") \
        .config("spark.hadoop.fs.s3a.connection.ssl.enabled", "false") \
        .getOrCreate()

def create_gold_tables(spark):
    print("Creating daily_sales_summary...")
    spark.sql("""
        CREATE OR REPLACE TABLE nessie.ecommerce.daily_sales_summary USING iceberg AS
        SELECT 
            CAST(event_time AS DATE) as date,
            ROUND(SUM(price), 2) as total_revenue,
            COUNT(CASE WHEN event_type = 'purchase' THEN 1 END) as total_orders,
            COUNT(DISTINCT user_id) as unique_customers,
            ROUND(AVG(CASE WHEN event_type = 'purchase' THEN price END), 2) as avg_order_value
        FROM nessie.ecommerce.orders_silver
        WHERE event_type = 'purchase'
        GROUP BY 1
        ORDER BY 1 DESC
    """)
    print("daily_sales_summary created.")

    print("Creating brand_performance...")
    spark.sql("""
        CREATE OR REPLACE TABLE nessie.ecommerce.brand_performance USING iceberg AS
        SELECT 
            brand,
            ROUND(SUM(CASE WHEN event_type = 'purchase' THEN price ELSE 0 END), 2) as total_revenue,
            COUNT(CASE WHEN event_type = 'purchase' THEN 1 END) as total_purchases,
            COUNT(CASE WHEN event_type = 'view' THEN 1 END) as total_views,
            COUNT(DISTINCT user_id) as unique_customers
        FROM nessie.ecommerce.orders_silver
        WHERE brand IS NOT NULL
        GROUP BY 1
        ORDER BY total_revenue DESC
    """)
    print("brand_performance created.")

if __name__ == "__main__":
    spark = create_spark_session()
    create_gold_tables(spark)
    spark.stop()
```
