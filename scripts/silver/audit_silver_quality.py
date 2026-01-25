"""
Silver Layer Smart Audit
Generates a Quality Report comparing Bronze (Raw) vs Silver (Clean).
"""

import os
import sys
import pyspark
from pyspark.sql import SparkSession
from pyspark.sql import functions as F

# Configuration
NESSIE_URI = os.getenv("NESSIE_URI", "http://nessie:19120/api/v1")
WAREHOUSE = os.getenv("WAREHOUSE", "s3a://lakehouse/warehouse")
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID", "admin")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "password123")
AWS_S3_ENDPOINT = os.getenv("AWS_S3_ENDPOINT", "http://minio:9000")
AWS_REGION = os.getenv("AWS_REGION", "ap-mumbai-1")

print("=" * 70)
print("SILVER LAYER - SMART AUDIT REPORT")
print("=" * 70)

conf = (
    pyspark.SparkConf()
        .setAppName('silver-audit')
        .set('spark.jars.packages', 
             'org.apache.iceberg:iceberg-spark-runtime-3.3_2.12:1.3.1,'
             'org.projectnessie.nessie-integrations:nessie-spark-extensions-3.3_2.12:0.67.0,'
             'software.amazon.awssdk:bundle:2.17.178,'
             'software.amazon.awssdk:url-connection-client:2.17.178')
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
        .set('spark.hadoop.fs.s3a.connection.ssl.enabled', 'false')
        .set('spark.hadoop.fs.s3a.impl', 'org.apache.hadoop.fs.s3a.S3AFileSystem')
        .set('spark.sql.catalog.nessie.s3.region', AWS_REGION)
        .set('spark.sql.catalog.nessie.client.region', AWS_REGION)
        .set('spark.hadoop.fs.s3a.endpoint.region', AWS_REGION)
)

spark = SparkSession.builder.config(conf=conf).getOrCreate()

# 1. READ BRONZE (Raw Input)
print("Reading from Bronze (main)...")
try:
    bronze_df = spark.sql("SELECT * FROM nessie.ecommerce.orders_bronze")
    total_rows_bronze = bronze_df.count()
    print(f"✓ Bronze Count: {total_rows_bronze}")
except Exception as e:
    print(f"⚠️ Could not read Bronze table (Likely path mismatch): {e}")
    total_rows_bronze = None

# 2. READ SILVER (Clean Output)
print("Reading from Silver (main)...")
silver_df = spark.sql("SELECT * FROM nessie.ecommerce.orders_silver")
total_rows_silver = silver_df.count()

# 3. CALCULATE DROPPED
if total_rows_bronze is not None:
    dropped_rows = total_rows_bronze - total_rows_silver
    dropped_pct = (dropped_rows/total_rows_bronze)*100
else:
    dropped_rows = "N/A"
    dropped_pct = 0.0

print("\n" + "-" * 30)
print("QUALITY REPORT")
print("-" * 30)
print(f"   - Input (Bronze): {total_rows_bronze if total_rows_bronze is not None else 'N/A'}")
print(f"   - Output (Silver): {total_rows_silver:,}")
if total_rows_bronze is not None:
    print(f"   - Dropped Rows:    {dropped_rows:,} ({dropped_pct:.2f}%)")
else:
    print(f"   - Dropped Rows:    (Comparison Skipped)")
print("-" * 30)

# 4. DEEP DIVE CHECKS
print("\nRunning Deep Dive Integrity Checks...")

# Check 1: Nulls in Critical Keys
null_keys = silver_df.filter("event_time IS NULL OR customer_id IS NULL").count()
print(f"   - Null Critical Keys: {null_keys} (Should be 0)")

# Check 2: Negative Prices
neg_prices = silver_df.filter("price < 0").count()
print(f"   - Negative Prices:    {neg_prices} (Should be 0)")

# Check 3: Duplicates scan (Sample check on a single day to avoid OOM)
print("   - Duplicate Check (Sample Day 2019-12-01)...")
day_df = silver_df.filter("order_date = '2019-12-01'")
day_count = day_df.count()
distinct_count = day_df.dropDuplicates(["event_time", "customer_id", "product_id", "event_type"]).count()

if day_count == distinct_count:
    print(f"     ✓ PASSED (Count: {day_count})")
else:
    print(f"     ❌ FAILED (Found {day_count - distinct_count} duplicates)")

print("\n" + "=" * 70)
print("AUDIT COMPLETE")
print("=" * 70)

spark.stop()
