#!/usr/bin/env python3
"""
Recreate Bronze Table with Correct S3FileIO Configuration
This script will drop and recreate the Bronze table metadata to fix the io-impl issue.
The actual data in S3 will not be deleted.
"""

import pyspark
from pyspark.sql import SparkSession
import os

# Configuration - Oracle Cloud Object Storage
NESSIE_URI = "http://172.18.0.2:19120/api/v1"
WAREHOUSE = "s3a://lakehouse-prod/warehouse"
AWS_ACCESS_KEY = "962c9f862226831e4edea90cfcfafb8a8dffcd51"
AWS_SECRET_KEY = "sd2rGU918DTmn35E4xJ8EV7BX2XUt7DkqC8v6WDNDUw="
AWS_S3_ENDPOINT = "https://bmcfe6z38foz.compat.objectstorage.ap-mumbai-1.oraclecloud.com"
AWS_REGION = "ap-mumbai-1"

print("\n" + "="*70)
print("BRONZE TABLE FIX - Recreate with S3FileIO")
print("="*70)

# Create Spark session with CORRECT S3FileIO configuration
conf = (
    pyspark.SparkConf()
        .setAppName('bronze-table-fix')
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
        .set('spark.sql.catalog.nessie.io-impl', 'org.apache.iceberg.aws.s3.S3FileIO')  # FIXED: was HadoopFileIO
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

spark = SparkSession.builder.config(conf=conf).getOrCreate()

print("\n✅ Spark session created with S3FileIO")

# Step 1: Try to get current table location
print("\n📍 Step 1: Checking current Bronze table metadata...")
try:
    current_table = spark.sql("DESCRIBE EXTENDED nessie.ecommerce.orders_bronze")
    location_row = current_table.filter("col_name == 'Location'").collect()
    if location_row:
        current_location = location_row[0]['data_type']
        print(f"Current table location: {current_location}")
    else:
        print("⚠️ Location not found in metadata")
except Exception as e:
    print(f"⚠️ Cannot read current table: {e}")

# Step 2: Drop the table (metadata only, data stays in S3)
print("\n🗑️  Step 2: Dropping Bronze table metadata...")
try:
    spark.sql("DROP TABLE IF EXISTS nessie.ecommerce.orders_bronze")
    print("✅ Table metadata dropped")
except Exception as e:
    print(f"⚠️ Drop failed (table may not exist): {e}")

# Step 3: Read data from S3 source location
print("\n📖 Step 3: Reading data from S3...")
try:
    # Read from the Bronze S3 location
    bronze_path = "s3a://lakehouse-prod/bronze/ecommerce/*.parquet"
    print(f"Reading from: {bronze_path}")
    df = spark.read.parquet(bronze_path)
    
    record_count = df.count()
    print(f"✅ Found {record_count:,} records in S3")
    
    # Show schema
    print("\nSchema:")
    df.printSchema()
    
    # Step 4: Recreate table with correct configuration
    print("\n💾 Step 4: Recreating Bronze table with S3FileIO...")
    
    # Create namespace
    spark.sql("CREATE NAMESPACE IF NOT EXISTS nessie.ecommerce")
    
    # Create the table by writing the data
    df.writeTo("nessie.ecommerce.orders_bronze") \
        .using("iceberg") \
        .tableProperty("write.format.default", "parquet") \
        .tableProperty("write.parquet.compression-codec", "snappy") \
        .create()
    
    print("✅ Bronze table recreated with S3FileIO")
    
    # Step 5: Verify
    print("\n✅ Step 5: Verifying new table...")
    verify_count = spark.sql("SELECT COUNT(*) as cnt FROM nessie.ecommerce.orders_bronze").collect()[0]['cnt']
    print(f"Verified count: {verify_count:,} records")
    
    # Show table details
    print("\nTable Details:")
    spark.sql("DESCRIBE EXTENDED nessie.ecommerce.orders_bronze").filter("col_name IN ('Location', 'Provider')").show(truncate=False)
    
    # Sample data
    print("\nSample Data:")
    spark.sql("SELECT * FROM nessie.ecommerce.orders_bronze LIMIT 5").show(truncate=False)
    
    print("\n" + "="*70)
    print("✅ BRONZE TABLE FIX COMPLETE!")
    print("="*70)
    print(f"✅ Table accessible with {verify_count:,} records")
    print("✅ Using S3FileIO (correct configuration)")
    print("✅ Ready for Silver layer transformations")
    
except Exception as e:
    print(f"\n❌ Error during recreation: {e}")
    print("\nThis likely means the data is NOT in s3a://lakehouse-prod/bronze/ecommerce/")
    print("You may need to re-run the full ingestion with the corrected script.")
    import traceback
    traceback.print_exc()

spark.stop()
