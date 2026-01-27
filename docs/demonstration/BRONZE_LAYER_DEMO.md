# 🥉 Bronze Layer: Scalable Raw Ingestion

The Bronze Layer is our "Entry Point" into the Lakehouse. It captures raw data from source systems in its original format while providing the benefits of a managed table format (Iceberg) and version control (Nessie).

---

## 🏛️ Architecture Overview
In this production setup, we have successfully ingested the **full 12-month e-commerce dataset** consisting of over **301.7 million records**.

- **Source:** 1,614 Parquet files (approx. 7.6GB raw)
- **Format:** [Apache Iceberg](https://iceberg.apache.org/) (High-performance table format)
- **Catalog:** [Project Nessie](https://projectnessie.org/) (Git-like version control for data)
- **Storage:** Oracle Cloud Object Storage (S3-Compatible)
- **Branching Strategy:** Isolation via the `bronze` branch to ensure absolute stability before transformation.

---

## 🚀 The Ingestion Process
We utilize an optimized PySpark ingestion script that bypasses schema inference and processes data in monthly batches to maintain a low memory footprint.

### 📜 Key Scripts
| Script | Description |
| :--- | :--- |
| `ingest_full_dataset.py` | The production pipeline that handles the 301.8M record batch ingestion. |
| `reset_and_load_demo.py` | Clean-slate utility for subset testing. |
| `force_delete_nessie_table.py` | REST-API utility for metadata recovery and table purging. |

### 📊 Production Statistics
- **Total Records:** 301,758,993
- **Data Period:** December 2019 - November 2020
- **Ingestion Time:** ~45 Minutes (Optimized batching)
- **Verification Hash:** `4be4bde0...` (Nessie Bronze Branch)

---

## 📓 Interactive Exploration (Jupyter)
The Bronze layer is fully searchable via our interactive Jupyter environment on **VM2**.

### 🔗 Access Details
- **URL:** [http://140.245.16.49:8888](http://140.245.16.49:8888)
- **Token:** `c2595d2830639ad3a5cdfa4cb43aa649dedb362084ab932f`

### � Step 1: Initialize Spark (Paste in Cell 1)
```python
from pyspark.sql import SparkSession

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
```

### 📊 Step 2: Query the Bronze Table
```python
# Show the first 10 records
spark.table("nessie.ecommerce.orders_bronze").show(10)

# Quick aggregation: Records per Brand
spark.sql("SELECT brand, count(*) FROM nessie.ecommerce.orders_bronze GROUP BY brand ORDER BY 2 DESC LIMIT 5").show()
```

---

## 🌿 Branching Strategy (Project Nessie)
We use a **Git-for-Data** approach to manage changes. The Bronze layer lives on its own branch, meaning you can query "Bronze-at-this-point-in-time."

1.  **Branch `bronze`**: Contains the raw, 301.8M record dataset.
2.  **Branch `silver`**: Used for staging transformed and deduplicated data (In-Progress).
3.  **Branch `gold`**: Contains the final aggregated business metrics.
4.  **Branch `main`**: The production source of truth for downstream BI/ML.

> [!IMPORTANT]
> **Branch Isolation**
> Because the Bronze ingestion happened on the `bronze` branch, any queries from the `main` branch will return "Table Not Found" until a **Merge** operation is performed. This protects the production `main` branch from ingestion noise.

---

## 🔍 Verification Snapshot
To verify the full scale in your notebook:

```python
# Check record count on the bronze branch
spark.sql("SELECT count(*) FROM nessie.ecommerce.`orders_bronze@bronze`").show()
```

---

## 🛡️ Metadata Stability
To achieve this scale, we transitioned from `S3FileIO` to `HadoopFileIO` with `S3AFileSystem`. This resolved memory-pressure issues during the commit phase of the 301M records, ensuring 100% metadata consistency in the Nessie Catalog.
