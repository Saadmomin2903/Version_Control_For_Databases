#!/usr/bin/env python3
import os
import sys
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, to_date, year, month
from pyspark.sql.types import StructType, StructField, StringType, LongType, DoubleType, TimestampType
from datetime import datetime

# Configuration
DATA_PATH = os.getenv("DATA_PATH", "/home/jovyan/data/firebolt-raw")
NESSIE_URI = os.getenv("NESSIE_URI", "http://172.18.0.2:19120/api/v1")
WAREHOUSE = "s3a://lakehouse-prod/warehouse"
AWS_ACCESS_KEY = "962c9f862226831e4edea90cfcfafb8a8dffcd51"
AWS_SECRET_KEY = "sd2rGU918DTmn35E4xJ8EV7BX2XUt7DkqC8v6WDNDUw="
AWS_S3_ENDPOINT = "https://bmcfe6z38foz.compat.objectstorage.ap-mumbai-1.oraclecloud.com"

# Define Fixed Schema to avoid expensive inference
ECOM_SCHEMA = StructType([
    StructField("event_time", TimestampType(), True),
    StructField("event_type", StringType(), True),
    StructField("product_id", LongType(), True),
    StructField("category_id", StringType(), True),
    StructField("category_code", StringType(), True),
    StructField("brand", StringType(), True),
    StructField("price", DoubleType(), True),
    StructField("user_id", StringType(), True),
    StructField("user_session", StringType(), True)
])

def get_spark_session():
    import pyspark
    conf = (
        pyspark.SparkConf()
        .setAppName('full-dataset-ingestion')
        .set('spark.sql.shuffle.partitions', '200')
        # Use slightly more memory if available, but keep it safe
        .set('spark.driver.memory', '4g')
        .set('spark.executor.memory', '4g')
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
        .set('spark.sql.catalog.nessie.catalog-impl', 'org.apache.iceberg.nessie.NessieCatalog')
        .set('spark.sql.catalog.nessie.uri', NESSIE_URI)
        .set('spark.sql.catalog.nessie.ref', 'bronze')
        .set('spark.sql.catalog.nessie.authentication.type', 'NONE')
        .set('spark.sql.catalog.nessie.warehouse', WAREHOUSE)
        .set('spark.sql.catalog.nessie.io-impl', 'org.apache.iceberg.hadoop.HadoopFileIO')
        .set('spark.sql.catalog.nessie.s3.endpoint', AWS_S3_ENDPOINT)
        .set('spark.sql.catalog.nessie.s3.region', 'ap-mumbai-1')
        .set('spark.sql.catalog.nessie.s3.path-style-access', 'true')
        .set('spark.hadoop.fs.s3a.access.key', AWS_ACCESS_KEY)
        .set('spark.hadoop.fs.s3a.secret.key', AWS_SECRET_KEY)
        .set('spark.hadoop.fs.s3a.endpoint', AWS_S3_ENDPOINT)
        .set('spark.hadoop.fs.s3a.path.style.access', 'true')
        .set('spark.hadoop.fs.s3a.connection.ssl.enabled', 'true')
        .set('spark.hadoop.fs.s3a.impl', 'org.apache.hadoop.fs.s3a.S3AFileSystem')
        .set('spark.hadoop.fs.s3a.endpoint.region', 'ap-mumbai-1')
    )
    return SparkSession.builder.config(conf=conf).getOrCreate()

def run_reingestion():
    print("\n" + "="*60)
    print("🚀 PRODUCTION RE-INGESTION (Dec 2019 - Nov 2020)")
    print(f"⏰ Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    sys.stdout.flush()

    spark = get_spark_session()
    
    print("🧹 Cleaning slate...")
    # These are fast metadata operations
    spark.sql("CREATE NAMESPACE IF NOT EXISTS nessie.ecommerce")
    # We already dropped the table via API, but this is a safety check
    spark.sql("DROP TABLE IF EXISTS nessie.ecommerce.orders_bronze")
    sys.stdout.flush()
    
    batches = [
        (2019, 12),
        (2020, 1), (2020, 2), (2020, 3), (2020, 4),
        (2020, 5), (2020, 6), (2020, 7), (2020, 8),
        (2020, 9), (2020, 10), (2020, 11)
    ]
    
    total_records = 0
    
    # Read the full dataset ONCE (lazy evaluation)
    print(f"📖 Scanning source directory: {DATA_PATH}...")
    all_data_df = spark.read.schema(ECOM_SCHEMA).parquet(f"{DATA_PATH}/*.parquet")
    sys.stdout.flush()

    for i, (year_val, month_val) in enumerate(batches):
        month_name = datetime(year_val, month_val, 1).strftime('%B')
        print(f"\n🔄 Processing {month_name} {year_val}...")
        sys.stdout.flush()
        
        # Filter for specific month
        month_df = all_data_df.filter(
            (year(col("event_time")) == year_val) &
            (month(col("event_time")) == month_val)
        )
        
        # Write to Bronze table
        try:
            if i == 0:
                print("💾 Creating table and writing first batch...")
                month_df.writeTo("nessie.ecommerce.orders_bronze") \
                    .using("iceberg") \
                    .tableProperty("write.format.default", "parquet") \
                    .create()
            else:
                print("💾 Appending batch to table...")
                month_df.writeTo("nessie.ecommerce.orders_bronze").append()
            
            # Get count for verification
            batch_count = month_df.count()
            total_records += batch_count
            print(f"✅ Ingested {batch_count:,} records (Total: {total_records:,})")
            sys.stdout.flush()
            
        except Exception as e:
            print(f"❌ Error in batch {year_val}-{month_val}: {e}")
            sys.stdout.flush()
            # We don't break here, we try next month if possible, but for Bronze we usually want all.
            # However, if one fails, subsequent might fail too.
            break

    print(f"\n" + "="*60)
    print(f"✅ FINAL SUMMARY")
    print(f"Total Records Re-ingested: {total_records:,}")
    print(f"⏰ End Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    sys.stdout.flush()
    
    spark.stop()

if __name__ == "__main__":
    run_reingestion()
