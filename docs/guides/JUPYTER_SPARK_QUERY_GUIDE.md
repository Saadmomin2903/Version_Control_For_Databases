# 📓 Jupyter Notebook Query Guide (Iceberg & Nessie)

You can query the **Bronze**, **Silver**, and **Gold** tables directly through the Jupyter Notebook environment running on **VM2**.

### 🔗 Access Details
- **URL:** [http://140.245.16.49:8888](http://140.245.16.49:8888)
- **Token:** `c2595d2830639ad3a5cdfa4cb43aa649dedb362084ab932f`

---

### 🚀 Step 1: Initialize Spark in Jupyter
Create a new Python notebook and paste this configuration. It is pre-configured to connect to your Nessie Catalog on VM1 and the Oracle S3 Storage.

```python
from pyspark.sql import SparkSession

# Configuration for Nessie & Iceberg
spark = SparkSession.builder \
    .appName("Jupyter-Nessie-Query") \
    .config("spark.jars.packages", "org.apache.iceberg:iceberg-spark-runtime-3.3_2.12:1.3.1,org.projectnessie.nessie-integrations:nessie-spark-extensions-3.3_2.12:0.67.0,org.apache.hadoop:hadoop-aws:3.3.1") \
    .config("spark.sql.extensions", "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions,org.projectnessie.spark.extensions.NessieSparkSessionExtensions") \
    .config("spark.sql.catalog.nessie", "org.apache.iceberg.spark.SparkCatalog") \
    .config("spark.sql.catalog.nessie.uri", "http://140.238.224.207:19120/api/v1") \
    .config("spark.sql.catalog.nessie.ref", "bronze") \
    .config("spark.sql.catalog.nessie.catalog-impl", "org.apache.iceberg.nessie.NessieCatalog") \
    .config("spark.sql.catalog.nessie.warehouse", "s3a://lakehouse-prod/warehouse") \
    .config("spark.sql.catalog.nessie.io-impl", "org.apache.iceberg.hadoop.HadoopFileIO") \
    .config("spark.hadoop.fs.s3a.access.key", "962c9f862226831e4edea90cfcfafb8a8dffcd51") \
    .config("spark.hadoop.fs.s3a.secret.key", "sd2rGU918DTmn35E4xJ8EV7BX2XUt7DkqC8v6WDNDUw=") \
    .config("spark.hadoop.fs.s3a.endpoint", "https://bmcfe6z38foz.compat.objectstorage.ap-mumbai-1.oraclecloud.com") \
    .config("spark.hadoop.fs.s3a.path.style.access", "true") \
    .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
    .getOrCreate()

print("✅ Spark Session Active with Nessie Catalog")
```

---

### 📊 Step 2: Query the Bronze Table
In a new cell, run the following to see the first 20 records:

```python
df = spark.table("nessie.ecommerce.orders_bronze")
df.show(20)
```

---

### 💡 Tips for Analysis
1.  **Switching Branches:** Change `.config("spark.sql.catalog.nessie.ref", "bronze")` to `main`, `silver`, or `gold` to see data in other layers.
2.  **Aggregation Example:**
    ```python
    # Count records per event type
    df.groupBy("event_type").count().show()
    ```
3.  **SQL Mode:**
    ```python
    spark.sql("SELECT brand, AVG(price) FROM nessie.ecommerce.orders_bronze GROUP BY brand ORDER BY 2 DESC LIMIT 10").show()
    ```
