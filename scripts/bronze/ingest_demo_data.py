#!/usr/bin/env python3
"""
Quick Ingest Demo Data (April 2020) - 3.1M Records
Restores the demo dataset using the CORRECT S3FileIO configuration.
"""

import os
import sys
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, to_date, year, month
from datetime import datetime

# Configuration
DATA_PATH = os.getenv("DATA_PATH", "/home/jovyan/data/firebolt-raw")
NESSIE_URI = os.getenv("NESSIE_URI", "http://nessie:19120/api/v1")
WAREHOUSE = os.getenv("WAREHOUSE", "s3a://lakehouse-prod/warehouse")
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY", "962c9f862226831e4edea90cfcfafb8a8dffcd51")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_KEY", "sd2rGU918DTmn35E4xJ8EV7BX2XUt7DkqC8v6WDNDUw=")
AWS_S3_ENDPOINT = os.getenv("AWS_S3_ENDPOINT", "https://bmcfe6z38foz.compat.objectstorage.ap-mumbai-1.oraclecloud.com")
AWS_REGION = "ap-mumbai-1"

def get_spark_session():
    import pyspark
    conf = (
        pyspark.SparkConf()
            .setAppName('demo-data-ingest')
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

def ingest_april_2020():
    spark = get_spark_session()
    
    print("\n" + "="*60)
    print("🚀 INGESTING DEMO DATA (April 2020)")
    print("="*60)
    
    # Create namespace
    spark.sql("CREATE NAMESPACE IF NOT EXISTS nessie.ecommerce")
    
    # Read Schema from first file
    print("Reading schema...")
    raw_df = spark.read.parquet(f"{DATA_PATH}/*.parquet")
    
    # Filter for April 2020 (Month 4)
    # Note: Using year=2020 and month=4 based on event_time
    print("Filtering for April 2020...")
    
    # Convert event_time to timestamp and create date columns
    df_transformed = raw_df \
        .withColumn("event_time", col("event_time").cast("timestamp")) \
        .withColumn("event_date", to_date(col("event_time"))) \
        .withColumn("year", year(col("event_time"))) \
        .withColumn("month", month(col("event_time")))
    
    # Filter April 2020
    april_df = df_transformed.filter((col("year") == 2020) & (col("month") == 4))
    
    # Count before write
    count = april_df.count()
    print(f"✅ Found {count:,} records for April 2020")
    
    if count == 0:
        print("❌ No data found for April 2020!")
        spark.stop()
        return

    # Write to Bronze table
    print(f"Writing {count:,} records to nessie.ecommerce.orders_bronze...")
    
    try:
        # Check if table exists
        try:
            spark.sql("DESCRIBE nessie.ecommerce.orders_bronze")
            print("Table exists, appending...")
            mode = "append"
        except:
            print("Table does not exist, creating...")
            mode = "overwrite" # Use overwrite to be safe for a fresh demo start

        # Write using Iceberg
        april_df.drop("year", "month") \
            .writeTo("nessie.ecommerce.orders_bronze") \
            .using("iceberg") \
            .tableProperty("write.format.default", "parquet") \
            .createOrReplace() # Force create/replace for demo restore
            
        print("✅ Write complete!")
        
        # Verify
        final_count = spark.read.format("iceberg").load("nessie.ecommerce.orders_bronze").count()
        print(f"📊 Final accessible Bronze count: {final_count:,}")
        
    except Exception as e:
        print(f"❌ Error writing table: {e}")
        import traceback
        traceback.print_exc()
        
    spark.stop()

if __name__ == "__main__":
    ingest_april_2020()
