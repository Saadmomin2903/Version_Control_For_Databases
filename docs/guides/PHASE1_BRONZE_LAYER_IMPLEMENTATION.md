# Phase 1: Bronze Layer Implementation Guide

This guide details the steps to ingest raw data into the **Bronze Layer**. This is the foundation of the Lakehouse, where raw data is stored in its original fidelity but structured as Iceberg tables.

---

## 🎯 Objective

1.  **Ingest Raw Data**: Load 411M records from Oracle Object Storage (CSV/Parquet) into Iceberg tables.
2.  **Partitioning**: Implement hidden partitioning (`days(event_time)`) for performance.
3.  **Namespace**: Create the `nessie.ecommerce` namespace.

---

## 🛠️ Step 1: Spark Configuration

To interact with Nessie and Iceberg, your Spark session must be configured correctly.

**Key Configurations:**
- `spark.sql.catalog.nessie`: Main entry point.
- `spark.sql.catalog.nessie.ref`: Branch name (e.g., `bronze` or `main`).
- `spark.hadoop.fs.s3a...`: Credentials for Oracle Object Storage.

---

## 💾 Step 2: Implementation Logic

### 2.1 Create Namespace
We need a logical container for our tables.

```python
spark.sql("CREATE NAMESPACE IF NOT EXISTS nessie.ecommerce")
```

### 2.2 Ingest Orders Table
This is the largest table (411M records).

**Schema:**
- `event_time`: timestamp
- `event_type`: string
- `product_id`: long
- `category_id`: long
- `category_code`: string
- `brand`: string
- `price`: double
- `user_id`: long
- `user_session`: string

**Partitioning Strategy:**
```sql
PARTITIONED BY (
    days(event_time),
    bucket(16, user_id)
)
```
*Why?* `days` helps query by date ranges. `bucket` helps evenly distribute data for joins by user.

### 2.3 Ingest Customers Table
A dimension table for user details.

---

## 📝 Script: `scripts/bronze/ingest_orders_spark.py`

Create or update this script with the following production-ready code:

```python
from pyspark.sql import SparkSession
from pyspark.sql.types import StructType, StructField, StringType, DoubleType, LongType, TimestampType
import os

def create_spark_session():
    # Use standard S3/Iceberg/Nessie config
    return SparkSession.builder \
        .appName("Bronze_Ingestion_Orders") \
        .config("spark.jars.packages", "org.apache.iceberg:iceberg-spark-runtime-3.3_2.12:1.3.1,org.projectnessie.nessie-integrations:nessie-spark-extensions-3.3_2.12:0.67.0,software.amazon.awssdk:bundle:2.17.178") \
        .config("spark.sql.extensions", "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions,org.projectnessie.spark.extensions.NessieSparkSessionExtensions") \
        .config("spark.sql.catalog.nessie", "org.apache.iceberg.spark.SparkCatalog") \
        .config("spark.sql.catalog.nessie.uri", "http://nessie:19120/api/v1") \
        .config("spark.sql.catalog.nessie.ref", "bronze") \
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
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
        .getOrCreate()

def ingest_orders(spark):
    print("🚀 Starting Bronze Ingestion...")
    
    # 1. Define Schema (Avoid inference for speed)
    schema = StructType([
        StructField("event_time", TimestampType(), True),
        StructField("event_type", StringType(), True),
        StructField("product_id", LongType(), True),
        StructField("category_id", LongType(), True),
        StructField("category_code", StringType(), True),
        StructField("brand", StringType(), True),
        StructField("price", DoubleType(), True),
        StructField("user_id", LongType(), True),
        StructField("user_session", StringType(), True)
    ])
    
    # 2. Read Raw Data (Simulated or S3)
    # Using local/simulated path for this script template. 
    # In production: "s3a://oracle-bucket/raw/2024-data.csv"
    input_path = "/home/jovyan/data/raw/orders.csv" 
    
    df = spark.read \
        .option("header", "true") \
        .schema(schema) \
        .csv(input_path)

    # 3. Create Namespace
    spark.sql("CREATE NAMESPACE IF NOT EXISTS nessie.ecommerce")
    
    # 4. Write to Iceberg (Partitioned)
    print("💾 Writing to nessie.ecommerce.orders_bronze...")
    df.writeTo("nessie.ecommerce.orders_bronze") \
        .partitionedBy(spark.sql("days(event_time)"), spark.sql("bucket(16, user_id)")) \
        .using("iceberg") \
        .createOrReplace()
        
    print("✅ Ingestion Complete!")

if __name__ == "__main__":
    spark = create_spark_session()
    ingest_orders(spark)
    spark.stop()
```

---

## 🏃 Execution

1.  **Ensure Branch Exists**:
    ```bash
    python3 scripts/utils/create_nessie_branches.py --branch bronze --source main
    ```

2.  **Run Ingestion**:
    ```bash
    docker exec lakehouse-spark python3 /home/jovyan/scripts/bronze/ingest_orders_spark.py
    ```

3.  **Verify**:
    ```bash
    # Count rows
    docker exec lakehouse-spark python3 -c "from pyspark.sql import SparkSession; spark=SparkSession.builder.getOrCreate(); print(spark.sql('SELECT COUNT(*) FROM nessie.ecommerce.orders_bronze').collect())"
    ```
