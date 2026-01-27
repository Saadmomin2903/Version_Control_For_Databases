# Jupyter Notebook - Spark Query Guide

## Access JupyterLab on VM1

**URL:** http://140.238.224.207:8888

**Token:** Check the token with:
```bash
ssh -i ~/.ssh/oracle-vm1.key ubuntu@140.238.224.207 \
  "docker logs lakehouse-spark 2>&1 | grep 'token=' | tail -1"
```

---

## Query Bronze Table in Jupyter Notebook

### Step 1: Create New Notebook
1. Open JupyterLab at http://140.238.224.207:8888
2. Click "Python 3" under "Notebook"

### Step 2: Initialize Spark Session

Copy and paste this code into the first cell:

```python
import os
import sys
from pyspark.sql import SparkSession
from pyspark.sql import functions as F

# Add utils to path
sys.path.append('/home/jovyan/scripts')

# Import Spark session helper
from utils.spark_utils import get_spark_session

# Create Spark session
spark = get_spark_session("JupyterQuery")

print("✅ Spark Session Created!")
print(f"Spark Version: {spark.version}")
```

### Step 3: Query Bronze Table

```python
# Read Bronze table
bronze_df = spark.table("nessie.ecommerce.orders_bronze")

# Show record count
print(f"Total Records: {bronze_df.count():,}")

# Show schema
print("\nSchema:")
bronze_df.printSchema()

# Show sample data (first 20 rows)
print("\nSample Data:")
bronze_df.show(20, truncate=False)
```

### Step 4: Analyze Data by Month

```python
# Records by month
monthly_stats = bronze_df.groupBy(
    F.year("event_time").alias("year"),
    F.month("event_time").alias("month")
).agg(
    F.count("*").alias("record_count"),
    F.countDistinct("user_id").alias("unique_users"),
    F.countDistinct("product_id").alias("unique_products")
).orderBy("year", "month")

monthly_stats.show()
```

### Step 5: Sample Queries

**Top 10 Products:**
```python
top_products = bronze_df.groupBy("product_id").agg(
    F.count("*").alias("event_count")
).orderBy(F.desc("event_count")).limit(10)

top_products.show()
```

**Event Type Distribution:**
```python
event_types = bronze_df.groupBy("event_type").count().orderBy(F.desc("count"))
event_types.show()
```

**Data by Category:**
```python
category_stats = bronze_df.groupBy("category_code").agg(
    F.count("*").alias("events"),
    F.sum("price").alias("total_revenue")
).orderBy(F.desc("events")).limit(20)

category_stats.show(truncate=False)
```

---

## Access Spark UI

While queries are running:

**Spark UI URL:** http://140.238.224.207:4040

This shows:
- Active/completed jobs
- Stage details
- SQL queries
- Executors
- Storage

---

## Quick Data Quality Check

```python
# Data Quality Overview
print("=" * 70)
print("DATA QUALITY CHECK - BRONZE LAYER")
print("=" * 70)

# Total records
total = bronze_df.count()
print(f"\nTotal Records: {total:,}")

# Null checks
print("\nNull Counts:")
for col in bronze_df.columns:
    null_count = bronze_df.filter(F.col(col).isNull()).count()
    null_pct = (null_count / total) * 100
    print(f"  {col:20s}: {null_count:,} ({null_pct:.2f}%)")

# Date range
date_range = bronze_df.agg(
    F.min("event_time").alias("min_date"),
    F.max("event_time").alias("max_date")
).collect()[0]

print(f"\nDate Range:")
print(f"  Start: {date_range['min_date']}")
print(f"  End:   {date_range['max_date']}")

# Duplicates check
print(f"\nDuplicate Check:")
distinct_count = bronze_df.distinct().count()
duplicate_count = total - distinct_count
print(f"  Distinct: {distinct_count:,}")
print(f"  Duplicates: {duplicate_count:,} ({(duplicate_count/total)*100:.2f}%)")

print("=" * 70)
```

---

## Create Visualizations (Pandas)

```python
import pandas as pd
import matplotlib.pyplot as plt

# Convert small aggregates to Pandas for plotting
monthly_pd = monthly_stats.toPandas()

# Create month label
monthly_pd['month_label'] = monthly_pd['year'].astype(str) + '-' + monthly_pd['month'].astype(str).str.zfill(2)

# Plot
plt.figure(figsize=(12, 6))
plt.bar(monthly_pd['month_label'], monthly_pd['record_count'])
plt.title('Records by Month', fontsize=16)
plt.xlabel('Month', fontsize=12)
plt.ylabel('Record Count', fontsize=12)
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()

print(f"Total Records: {monthly_pd['record_count'].sum():,}")
```

---

## Stop Spark Session

When done:
```python
spark.stop()
print("✅ Spark session stopped")
```

---

## Troubleshooting

**If Spark session fails:**
```python
# Use direct configuration
from pyspark.sql import SparkSession
import pyspark

NESSIE_URI = "http://172.18.0.2:19120/api/v1"
WAREHOUSE = "s3a://lakehouse-prod/warehouse"
AWS_ACCESS_KEY = "962c9f862226831e4edea90cfcfafb8a8dffcd51"
AWS_SECRET_KEY = "sd2rGU918DTmn35E4xJ8EV7BX2XUt7DkqC8v6WDNDUw="
AWS_S3_ENDPOINT = "https://bmcfe6z38foz.compat.objectstorage.ap-mumbai-1.oraclecloud.com"
AWS_REGION = "ap-mumbai-1"

conf = (
    pyspark.SparkConf()
        .setAppName('jupyter-query')
        .set('spark.jars.packages', 
             'org.apache.iceberg:iceberg-spark-runtime-3.3_2.12:1.3.1,'
             'org.projectnessie.nessie-integrations:nessie-spark-extensions-3.3_2.12:0.67.0,'
             'software.amazon.awssdk:bundle:2.17.178,'
             'software.amazon.awssdk:url-connection-client:2.17.178,'
             'org.apache.hadoop:hadoop-aws:3.3.1')
        .set('spark.sql.extensions', 
             'org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions,'
             'org.projectnessie.spark.extensions.NessieSparkSessionExtensions')
        .set('spark.sql.catalog.nessie', 'org.apache.iceberg.spark.SparkCatalog')
        .set('spark.sql.catalog.nessie.uri', NESSIE_URI)
        .set('spark.sql.catalog.nessie.ref', 'main')
        .set('spark.sql.catalog.nessie.authentication.type', 'NONE')
        .set('spark.sql.catalog.nessie.catalog-impl', 'org.apache.iceberg.nessie.NessieCatalog')
        .set('spark.sql.catalog.nessie.warehouse', WAREHOUSE)
        .set('spark.sql.catalog.nessie.io-impl', 'org.apache.iceberg.aws.s3.S3FileIO')
        .set('spark.sql.catalog.nessie.s3.endpoint', AWS_S3_ENDPOINT)
        .set('spark.hadoop.fs.s3a.access.key', AWS_ACCESS_KEY)
        .set('spark.hadoop.fs.s3a.secret.key', AWS_SECRET_KEY)
        .set('spark.hadoop.fs.s3a.endpoint', AWS_S3_ENDPOINT)
        .set('spark.hadoop.fs.s3a.path.style.access', 'true')
        .set('spark.hadoop.fs.s3a.connection.ssl.enabled', 'true')
        .set('spark.hadoop.fs.s3a.impl', 'org.apache.hadoop.fs.s3a.S3AFileSystem')
        .set('spark.sql.catalog.nessie.s3.region', AWS_REGION)
        .set('spark.sql.catalog.nessie.client.region', AWS_REGION)
        .set('spark.hadoop.fs.s3a.endpoint.region', AWS_REGION)
)

spark = SparkSession.builder.config(conf=conf).getOrCreate()
```

---

## Performance Tips

1. **Use `.limit()` for quick checks:**
   ```python
   bronze_df.limit(1000).show()
   ```

2. **Use `.explain()` to see query plan:**
   ```python
   bronze_df.groupBy("event_type").count().explain()
   ```

3. **Cache frequently accessed data:**
   ```python
   bronze_df.cache()
   bronze_df.count()  # Trigger caching
   ```

4. **Write results to temp tables:**
   ```python
   monthly_stats.createOrReplaceTempView("monthly_temp")
   spark.sql("SELECT * FROM monthly_temp WHERE record_count > 50000000").show()
   ```
