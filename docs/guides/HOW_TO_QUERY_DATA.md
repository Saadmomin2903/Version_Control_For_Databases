# How to Query Your Data - Interactive Guide

## 🎯 Multiple Ways to Query Your Lakehouse

You have several options to run SQL/Spark commands and see table outputs:

1. **Jupyter Notebook** (Best for exploration) ✅
2. **PySpark Shell** (Quick terminal queries)
3. **Spark SQL Shell** (Pure SQL)
4. **Custom Python Scripts**

---

## 🚀 Option 1: Jupyter Notebook (Recommended!)

### Step 1: Access Jupyter

Your Spark container already has Jupyter running!

```bash
# Get the Jupyter token
docker exec lakehouse-spark jupyter server list
```

**Output will show**:
```
http://0.0.0.0:8888/?token=abc123xyz...
```

### Step 2: Open in Browser

1. Copy the full URL with token
2. Replace `0.0.0.0` with `localhost`
3. Open: `http://localhost:8888/?token=abc123xyz...`

OR simply go to: **http://localhost:8888**

---

## 📓 Create Your First Notebook

### Step 1: Create New Notebook

In Jupyter:
1. Click **"New"** → **"Python 3"**
2. Rename to: `Query_Lakehouse.ipynb`

### Step 2: Setup Spark Session (Run this first!)

```python
# Cell 1: Import and configure Spark
import pyspark
from pyspark.sql import SparkSession
from pyspark.sql import functions as F

# Spark configuration with Nessie
conf = (
    pyspark.SparkConf()
        .setAppName('interactive-queries')
        .set('spark.jars.packages', 
             'org.apache.iceberg:iceberg-spark-runtime-3.3_2.12:1.3.1,'
             'org.projectnessie.nessie-integrations:nessie-spark-extensions-3.3_2.12:0.67.0,'
             'software.amazon.awssdk:bundle:2.17.178,'
             'software.amazon.awssdk:url-connection-client:2.17.178')
        .set('spark.sql.extensions', 
             'org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions,'
             'org.projectnessie.spark.extensions.NessieSparkSessionExtensions')
        .set('spark.sql.catalog.nessie', 'org.apache.iceberg.spark.SparkCatalog')
        .set('spark.sql.catalog.nessie.uri', 'http://nessie:19120/api/v1')
        .set('spark.sql.catalog.nessie.ref', 'main')
        .set('spark.sql.catalog.nessie.authentication.type', 'NONE')
        .set('spark.sql.catalog.nessie.catalog-impl', 'org.apache.iceberg.nessie.NessieCatalog')
        .set('spark.sql.catalog.nessie.warehouse', 's3a://lakehouse/warehouse')
        .set('spark.sql.catalog.nessie.io-impl', 'org.apache.iceberg.aws.s3.S3FileIO')
        .set('spark.sql.catalog.nessie.s3.endpoint', 'http://minio:9000')
        .set('spark.hadoop.fs.s3a.access.key', 'admin')
        .set('spark.hadoop.fs.s3a.secret.key', 'password123')
        .set('spark.hadoop.fs.s3a.endpoint', 'http://minio:9000')
        .set('spark.hadoop.fs.s3a.path.style.access', 'true')
        .set('spark.hadoop.fs.s3a.connection.ssl.enabled', 'false')
        .set('spark.hadoop.fs.s3a.impl', 'org.apache.hadoop.fs.s3a.S3AFileSystem')
)

# Create Spark session
spark = SparkSession.builder.config(conf=conf).getOrCreate()

print("✅ Spark session ready!")
print(f"Spark version: {spark.version}")
```

---

## 📊 Example Queries

### Query 1: List All Tables

```python
# Cell 2: Show all tables
spark.sql("SHOW TABLES IN nessie.ecommerce").show()
```

**Output**:
```
+---------+------------------+-----------+
|namespace|         tableName|isTemporary|
+---------+------------------+-----------+
|ecommerce|customer_summary  |      false|
+---------+------------------+-----------+
```

---

### Query 2: View Customer Summaries

```python
# Cell 3: Query gold layer
df = spark.sql("""
    SELECT 
        customer_id,
        name,
        total_orders,
        total_revenue,
        customer_lifetime_value,
        customer_segment
    FROM nessie.ecommerce.customer_summary
    ORDER BY customer_lifetime_value DESC
    LIMIT 10
""")

# Show in table format
df.show(truncate=False)
```

**Output**:
```
+-----------+-------------+------------+-------------+----------------------+----------------+
|customer_id|name         |total_orders|total_revenue|customer_lifetime_value|customer_segment|
+-----------+-------------+------------+-------------+----------------------+----------------+
|CUST0042   |Customer 42  |15          |1458.50      |1458.50               |Premium         |
|CUST0089   |Customer 89  |12          |1205.25      |1205.25               |Premium         |
|CUST0015   |Customer 15  |10          |875.00       |875.00                |Gold            |
+-----------+-------------+------------+-------------+----------------------+----------------+
```

---

### Query 3: Statistics by Customer Segment

```python
# Cell 4: Aggregations
spark.sql("""
    SELECT 
        customer_segment,
        COUNT(*) as customer_count,
        ROUND(AVG(total_orders), 2) as avg_orders,
        ROUND(SUM(total_revenue), 2) as segment_revenue,
        ROUND(AVG(customer_lifetime_value), 2) as avg_clv
    FROM nessie.ecommerce.customer_summary
    GROUP BY customer_segment
    ORDER BY segment_revenue DESC
""").show(truncate=False)
```

**Output**:
```
+----------------+---------------+----------+---------------+--------+
|customer_segment|customer_count |avg_orders|segment_revenue|avg_clv |
+----------------+---------------+----------+---------------+--------+
|Premium         |23             |8.5       |45230.75       |1966.99 |
|Gold            |45             |5.2       |35482.50       |788.50  |
|Silver          |58             |3.1       |25678.25       |442.73  |
|Bronze          |25             |1.8       |2847.96        |113.92  |
|No Orders       |49             |0.0       |0.00           |0.00    |
+----------------+---------------+----------+---------------+--------+
```

---

### Query 4: Cross-Branch Queries

```python
# Cell 5: Compare data across branches

# Read from bronze branch
bronze_orders = spark.sql("""
    SELECT COUNT(*) as count, 'Bronze' as layer
    FROM nessie.ecommerce.`orders_bronze@bronze`
""")

# Read from silver branch
silver_orders = spark.sql("""
    SELECT COUNT(*) as count, 'Silver' as layer
    FROM nessie.ecommerce.`orders_silver@silver`
""")

# Combine results
bronze_orders.union(silver_orders).show()
```

**Output**:
```
+-----+------+
|count|layer |
+-----+------+
|1000 |Bronze|
|950  |Silver|
+-----+------+
```

---

### Query 5: Data Quality Checks

```python
# Cell 6: Check data quality scores
spark.sql("""
    SELECT 
        data_quality_score,
        COUNT(*) as record_count,
        ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) as percentage
    FROM nessie.ecommerce.`orders_silver@silver`
    GROUP BY data_quality_score
    ORDER BY data_quality_score DESC
""").show()
```

---

### Query 6: Join Tables from Different Branches

```python
# Cell 7: Join customers and orders
result = spark.sql("""
    SELECT 
        c.customer_id,
        c.name,
        c.email,
        COUNT(o.order_id) as order_count,
        SUM(o.total_amount) as total_spent
    FROM nessie.ecommerce.`customers_silver@silver` c
    LEFT JOIN nessie.ecommerce.`orders_silver@silver` o
        ON c.customer_id = o.customer_id
    WHERE o.status = 'completed'
    GROUP BY c.customer_id, c.name, c.email
    HAVING order_count > 5
    ORDER BY total_spent DESC
    LIMIT 10
""")

result.show(truncate=False)
```

---

## 📈 Visualization in Jupyter

### Create Charts

```python
# Cell 8: Visualize with pandas and matplotlib
import pandas as pd
import matplotlib.pyplot as plt

# Get data as pandas DataFrame
segment_stats = spark.sql("""
    SELECT customer_segment, COUNT(*) as count
    FROM nessie.ecommerce.customer_summary
    GROUP BY customer_segment
    ORDER BY count DESC
""").toPandas()

# Create bar chart
plt.figure(figsize=(10, 6))
plt.bar(segment_stats['customer_segment'], segment_stats['count'])
plt.title('Customers by Segment')
plt.xlabel('Segment')
plt.ylabel('Number of Customers')
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()

# Print data
print(segment_stats)
```

---

## 🖥️ Option 2: PySpark Shell (Terminal)

Quick queries from terminal without notebook:

```bash
# Enter PySpark shell
docker exec -it lakehouse-spark pyspark \
  --packages org.apache.iceberg:iceberg-spark-runtime-3.3_2.12:1.3.1,org.projectnessie.nessie-integrations:nessie-spark-extensions-3.3_2.12:0.67.0,software.amazon.awssdk:bundle:2.17.178 \
  --conf spark.sql.extensions=org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions,org.projectnessie.spark.extensions.NessieSparkSessionExtensions \
  --conf spark.sql.catalog.nessie=org.apache.iceberg.spark.SparkCatalog \
  --conf spark.sql.catalog.nessie.uri=http://nessie:19120/api/v1 \
  --conf spark.sql.catalog.nessie.ref=main \
  --conf spark.sql.catalog.nessie.authentication.type=NONE \
  --conf spark.sql.catalog.nessie.catalog-impl=org.apache.iceberg.nessie.NessieCatalog \
  --conf spark.sql.catalog.nessie.warehouse=s3a://lakehouse/warehouse \
  --conf spark.sql.catalog.nessie.io-impl=org.apache.iceberg.aws.s3.S3FileIO \
  --conf spark.sql.catalog.nessie.s3.endpoint=http://minio:9000 \
  --conf spark.hadoop.fs.s3a.access.key=admin \
  --conf spark.hadoop.fs.s3a.secret.key=password123 \
  --conf spark.hadoop.fs.s3a.endpoint=http://minio:9000 \
  --conf spark.hadoop.fs.s3a.path.style.access=true \
  --conf spark.hadoop.fs.s3a.connection.ssl.enabled=false
```

**Then run queries**:
```python
# In PySpark shell
>>> spark.sql("SELECT COUNT(*) FROM nessie.ecommerce.customer_summary").show()
+--------+
|count(1)|
+--------+
|     200|
+--------+

>>> spark.sql("SELECT customer_segment, COUNT(*) FROM nessie.ecommerce.customer_summary GROUP BY customer_segment").show()
```

**Exit**: Type `exit()` or press `Ctrl+D`

---

## 🎯 Option 3: Quick One-Liner Queries

For simple queries without opening a shell:

```bash
# Count records in gold layer
docker exec lakehouse-spark python3 << 'EOF'
from pyspark.sql import SparkSession
import pyspark

conf = (pyspark.SparkConf()
    .setAppName('quick-query')
    .set('spark.jars.packages', 
         'org.apache.iceberg:iceberg-spark-runtime-3.3_2.12:1.3.1,'
         'org.projectnessie.nessie-integrations:nessie-spark-extensions-3.3_2.12:0.67.0,'
         'software.amazon.awssdk:bundle:2.17.178,'
         'software.amazon.awssdk:url-connection-client:2.17.178')
    .set('spark.sql.extensions', 
         'org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions,'
         'org.projectnessie.spark.extensions.NessieSparkSessionExtensions')
    .set('spark.sql.catalog.nessie', 'org.apache.iceberg.spark.SparkCatalog')
    .set('spark.sql.catalog.nessie.uri', 'http://nessie:19120/api/v1')
    .set('spark.sql.catalog.nessie.ref', 'main')
    .set('spark.sql.catalog.nessie.authentication.type', 'NONE')
    .set('spark.sql.catalog.nessie.catalog-impl', 'org.apache.iceberg.nessie.NessieCatalog')
    .set('spark.sql.catalog.nessie.warehouse', 's3a://lakehouse/warehouse')
    .set('spark.sql.catalog.nessie.io-impl', 'org.apache.iceberg.aws.s3.S3FileIO')
    .set('spark.sql.catalog.nessie.s3.endpoint', 'http://minio:9000')
    .set('spark.hadoop.fs.s3a.access.key', 'admin')
    .set('spark.hadoop.fs.s3a.secret.key', 'password123')
    .set('spark.hadoop.fs.s3a.endpoint', 'http://minio:9000')
    .set('spark.hadoop.fs.s3a.path.style.access', 'true')
    .set('spark.hadoop.fs.s3a.connection.ssl.enabled', 'false')
    .set('spark.hadoop.fs.s3a.impl', 'org.apache.hadoop.fs.s3a.S3AFileSystem'))

spark = SparkSession.builder.config(conf=conf).getOrCreate()

# Your query here
spark.sql("""
    SELECT customer_segment, COUNT(*) as count
    FROM nessie.ecommerce.customer_summary
    GROUP BY customer_segment
    ORDER BY count DESC
""").show()

spark.stop()
EOF
```

---

## 📝 Create a Helper Script

Save this as `scripts/query_helper.py`:

```python
#!/usr/bin/env python3
"""
Quick query helper - run SQL on your lakehouse
Usage: python3 query_helper.py "SELECT * FROM nessie.ecommerce.customer_summary LIMIT 5"
"""

import sys
import pyspark
from pyspark.sql import SparkSession

def get_spark():
    conf = (pyspark.SparkConf()
        .setAppName('query-helper')
        .set('spark.jars.packages', 
             'org.apache.iceberg:iceberg-spark-runtime-3.3_2.12:1.3.1,'
             'org.projectnessie.nessie-integrations:nessie-spark-extensions-3.3_2.12:0.67.0,'
             'software.amazon.awssdk:bundle:2.17.178,'
             'software.amazon.awssdk:url-connection-client:2.17.178')
        .set('spark.sql.extensions', 
             'org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions,'
             'org.projectnessie.spark.extensions.NessieSparkSessionExtensions')
        .set('spark.sql.catalog.nessie', 'org.apache.iceberg.spark.SparkCatalog')
        .set('spark.sql.catalog.nessie.uri', 'http://nessie:19120/api/v1')
        .set('spark.sql.catalog.nessie.ref', 'main')
        .set('spark.sql.catalog.nessie.authentication.type', 'NONE')
        .set('spark.sql.catalog.nessie.catalog-impl', 'org.apache.iceberg.nessie.NessieCatalog')
        .set('spark.sql.catalog.nessie.warehouse', 's3a://lakehouse/warehouse')
        .set('spark.sql.catalog.nessie.io-impl', 'org.apache.iceberg.aws.s3.S3FileIO')
        .set('spark.sql.catalog.nessie.s3.endpoint', 'http://minio:9000')
        .set('spark.hadoop.fs.s3a.access.key', 'admin')
        .set('spark.hadoop.fs.s3a.secret.key', 'password123')
        .set('spark.hadoop.fs.s3a.endpoint', 'http://minio:9000')
        .set('spark.hadoop.fs.s3a.path.style.access', 'true')
        .set('spark.hadoop.fs.s3a.connection.ssl.enabled', 'false')
        .set('spark.hadoop.fs.s3a.impl', 'org.apache.hadoop.fs.s3a.S3AFileSystem'))
    
    return SparkSession.builder.config(conf=conf).getOrCreate()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 query_helper.py 'SQL QUERY'")
        sys.exit(1)
    
    query = sys.argv[1]
    spark = get_spark()
    
    try:
        result = spark.sql(query)
        result.show(100, truncate=False)
    except Exception as e:
        print(f"Error: {e}")
    finally:
        spark.stop()
```

**Usage**:
```bash
# Copy to container
docker cp scripts/query_helper.py lakehouse-spark:/home/jovyan/

# Run queries
docker exec lakehouse-spark python3 /home/jovyan/query_helper.py \
  "SELECT COUNT(*) FROM nessie.ecommerce.customer_summary"

docker exec lakehouse-spark python3 /home/jovyan/query_helper.py \
  "SELECT * FROM nessie.ecommerce.customer_summary LIMIT 5"
```

---

## 🎁 Pre-Made Notebook Template

Save this as `notebooks/Explore_Lakehouse.ipynb` (manual copy to Jupyter):

```python
# ============================================
# Lakehouse Explorer Notebook
# ============================================

# 1. Setup
import pyspark
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
import pandas as pd
import matplotlib.pyplot as plt

# Configure Spark (run once)
# ... (use configuration from above)

# 2. Available Tables
print("📊 Available Tables:")
spark.sql("SHOW TABLES IN nessie.ecommerce").show()

# 3. Quick Stats
print("\n📈 Quick Stats:")
print(f"Total Customers: {spark.sql('SELECT COUNT(*) FROM nessie.ecommerce.customer_summary').collect()[0][0]}")
print(f"Bronze Orders: {spark.sql('SELECT COUNT(*) FROM nessie.ecommerce.`orders_bronze@bronze`').collect()[0][0]}")
print(f"Silver Orders: {spark.sql('SELECT COUNT(*) FROM nessie.ecommerce.`orders_silver@silver`').collect()[0][0]}")

# 4. Your queries here...
```

---

## ✅ Quick Start Commands

```bash
# 1. Get Jupyter URL
docker exec lakehouse-spark jupyter server list

# 2. Open browser to http://localhost:8888

# 3. Create new Python 3 notebook

# 4. Copy-paste the Spark setup code from above

# 5. Start querying!
```

---

## 🎯 Summary: Best Practices

| Method | Best For | Pros | Cons |
|--------|----------|------|------|
| **Jupyter Notebook** | Exploration, visualization | Interactive, save work, charts | Requires browser |
| **PySpark Shell** | Quick terminal queries | Fast, no setup | Output formatting limited |
| **One-liner Scripts** | Automation, CI/CD | Reproducible | Verbose |
| **Helper Script** | Repeated queries | Reusable, clean | Setup required |

**My Recommendation**: Start with **Jupyter Notebook** for exploring your data! 🚀
