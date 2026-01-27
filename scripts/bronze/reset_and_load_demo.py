#!/usr/bin/env python3
"""
RESET and Load Demo Data (April 2020)
Aggressively drops the existing table to clear bad metadata, then re-loads the demo data.
"""

import os
import sys
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, to_date, year, month
from datetime import datetime

# Configuration
DATA_PATH = os.getenv("DATA_PATH", "/home/jovyan/data/firebolt-raw")
NESSIE_URI = os.getenv("NESSIE_URI", "http://nessie:19120/api/v1")
# Ensure the warehouse path is correct for S3
WAREHOUSE = os.getenv("WAREHOUSE", "s3a://lakehouse-prod/warehouse")
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY", "962c9f862226831e4edea90cfcfafb8a8dffcd51")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_KEY", "sd2rGU918DTmn35E4xJ8EV7BX2XUt7DkqC8v6WDNDUw=")
AWS_S3_ENDPOINT = os.getenv("AWS_S3_ENDPOINT", "https://bmcfe6z38foz.compat.objectstorage.ap-mumbai-1.oraclecloud.com")
AWS_REGION = "ap-mumbai-1"

def get_spark_session():
    import pyspark
    conf = (
        pyspark.SparkConf()
            .setAppName('reset-demo-load')
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
            .set('spark.sql.catalog.nessie.s3.region', AWS_REGION)
            .set('spark.sql.catalog.nessie.client.region', AWS_REGION)
            .set('spark.hadoop.fs.s3a.access.key', AWS_ACCESS_KEY)
            .set('spark.hadoop.fs.s3a.secret.key', AWS_SECRET_KEY)
            .set('spark.hadoop.fs.s3a.endpoint', AWS_S3_ENDPOINT)
            .set('spark.hadoop.fs.s3a.path.style.access', 'true')
            .set('spark.hadoop.fs.s3a.connection.ssl.enabled', 'true')
            .set('spark.hadoop.fs.s3a.impl', 'org.apache.hadoop.fs.s3a.S3AFileSystem')
            .set('spark.hadoop.fs.s3a.endpoint.region', AWS_REGION)
    )
    return SparkSession.builder.config(conf=conf).getOrCreate()

def reset_and_load():
    spark = get_spark_session()
    
    print("\n" + "="*60)
    print("🧹 RESETTING BRONZE TABLE & LOADING DEMO DATA")
    print("="*60)
    
    # 1. DROP EXISTING TABLE
    print("Drop existing table to clear bad metadata...")
    spark.sql("DROP TABLE IF EXISTS nessie.ecommerce.orders_bronze")
    print("✅ Table dropped (metadata cleared).")

    # 2. CREATE NAMESPACE
    spark.sql("CREATE NAMESPACE IF NOT EXISTS nessie.ecommerce")
    
    # 3. READ DATA
    print("Reading source data...")
    raw_df = spark.read.parquet(f"{DATA_PATH}/*.parquet")
    
    # Convert and Filter April 2020
    print("Filtering for April 2020...")
    df_transformed = raw_df \
        .withColumn("event_time", col("event_time").cast("timestamp")) \
        .withColumn("event_date", to_date(col("event_time"))) \
        .withColumn("year", year(col("event_time"))) \
        .withColumn("month", month(col("event_time")))
    
    april_df = df_transformed.filter((col("year") == 2020) & (col("month") == 4))
    
    count = april_df.count()
    print(f"✅ Ready to ingest {count:,} records.")
    
    if count == 0:
        print("❌ No data found! Aborting.")
        spark.stop()
        return

    # 4. WRITE NEW TABLE
    print(f"Writing to nessie.ecommerce.orders_bronze (Location: {WAREHOUSE})...")
    
    # Using 'create' instead of 'createOrReplace' to ensure clean creation
    april_df.drop("year", "month") \
        .writeTo("nessie.ecommerce.orders_bronze") \
        .using("iceberg") \
        .tableProperty("write.format.default", "parquet") \
        .create()
        
    print("✅ Write complete!")
    
    # 5. VERIFY
    print("\n🔍 Verification:")
    
    # Check count
    final_count = spark.table("nessie.ecommerce.orders_bronze").count()
    print(f"  Final Count: {final_count:,}")
    
    # Check Location
    print("  Table Location:")
    spark.sql("DESCRIBE EXTENDED nessie.ecommerce.orders_bronze").filter("col_name == 'Location'").show(truncate=False)
    
    location_row = spark.sql("DESCRIBE EXTENDED nessie.ecommerce.orders_bronze").filter("col_name == 'Location'").collect()
    if location_row:
        loc = location_row[0]['data_type']
        if "s3a://" in loc or "s3://" in loc:
             print("✅ Location looks correct (S3).")
        else:
             print(f"⚠️ WARNING: Location does NOT look like S3: {loc}")

    spark.stop()

if __name__ == "__main__":
    reset_and_load()
