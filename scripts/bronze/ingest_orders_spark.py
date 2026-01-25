"""
Bronze Orders Ingestion using PySpark with Nessie Catalog

This script is designed to run inside the Spark notebook container.
It reads CSV data and writes to Iceberg tables managed by Nessie.
"""

import os
import pyspark
from pyspark.sql import SparkSession
from pyspark.sql.types import StructType, StructField, StringType, DoubleType, LongType, TimestampType
from pyspark.sql.functions import col

def create_spark_session():
    # Set AWS Region globally via Env Vars (Required for AWS SDK v2)
    os.environ['AWS_REGION'] = 'ap-mumbai-1'
    os.environ['AWS_DEFAULT_REGION'] = 'ap-mumbai-1'
    
    # Production S3/Iceberg/Nessie config for Oracle Object Storage
    return SparkSession.builder \
        .appName("Bronze_Ingestion_Orders") \
        .config("spark.jars.packages", "org.apache.iceberg:iceberg-spark-runtime-3.3_2.12:1.3.1,org.projectnessie.nessie-integrations:nessie-spark-extensions-3.3_2.12:0.67.0,software.amazon.awssdk:bundle:2.17.178,org.apache.hadoop:hadoop-aws:3.3.1") \
        .config("spark.sql.extensions", "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions,org.projectnessie.spark.extensions.NessieSparkSessionExtensions") \
        .config("spark.sql.catalog.nessie", "org.apache.iceberg.spark.SparkCatalog") \
        .config("spark.sql.catalog.nessie.uri", os.environ.get("NESSIE_URI", "http://nessie:19120/api/v1")) \
        .config("spark.sql.catalog.nessie.ref", "bronze") \
        .config("spark.sql.catalog.nessie.authentication.type", "NONE") \
        .config("spark.sql.catalog.nessie.catalog-impl", "org.apache.iceberg.nessie.NessieCatalog") \
        .config("spark.sql.catalog.nessie.warehouse", "s3a://lakehouse-prod/warehouse") \
        .config("spark.sql.catalog.nessie.io-impl", "org.apache.iceberg.aws.s3.S3FileIO") \
        .config("spark.sql.catalog.nessie.s3.endpoint", "https://bmcfe6z38foz.compat.objectstorage.ap-mumbai-1.oraclecloud.com") \
        .config("spark.sql.catalog.nessie.s3.path-style-access", "true") \
        .config("spark.sql.catalog.nessie.s3.region", "ap-mumbai-1") \
        .config("spark.sql.catalog.nessie.client.region", "ap-mumbai-1") \
        .config("spark.hadoop.fs.s3a.endpoint", "https://bmcfe6z38foz.compat.objectstorage.ap-mumbai-1.oraclecloud.com") \
        .config("spark.hadoop.fs.s3a.access.key", "962c9f862226831e4edea90cfcfafb8a8dffcd51") \
        .config("spark.hadoop.fs.s3a.secret.key", "sd2rGU918DTmn35E4xJ8EV7BX2XUt7DkqC8v6WDNDUw=") \
        .config("spark.hadoop.fs.s3a.path.style.access", "true") \
        .config("spark.hadoop.fs.s3a.endpoint.region", "ap-mumbai-1") \
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
        .getOrCreate()

def ingest_orders(spark):
    print("🚀 Starting Bronze Ingestion...")
    
    # 2. Read Raw Data (Allow Schema Inference to handle Binary/String mismatches)
    input_path = "s3a://lakehouse-prod/bronze/ecommerce/" 
    print(f"Reading from: {input_path}")
    print("This may take a few minutes...")
    
    df = spark.read.parquet(input_path)
    
    # Cache to avoid re-reading for count and write
    # df.cache() 
    
    record_count = df.count()
    print(f"✅ Loaded {record_count:,} records")

    # Show schema
    print("\n📋 Schema:")
    df.printSchema()
    
    # 3. Create Namespace
    spark.sql("CREATE NAMESPACE IF NOT EXISTS nessie.ecommerce")
    
    # 4. Create Table and Write (using SQL to enforce Partitioning as per Vision)
    table_name = "nessie.ecommerce.orders_bronze"
    print(f"💾 Creating/Replacing table {table_name} with Partitioning (Vision Aligned)...")
    
    # We use SQL DDL because it supports Iceberg transforms (days, bucket) natively
    spark.sql(f"""
        CREATE OR REPLACE TABLE {table_name} (
            event_time TIMESTAMP,
            event_type STRING,
            product_id LONG,
            category_id STRING,
            category_code STRING,
            brand STRING,
            price DOUBLE,
            user_id STRING,
            user_session STRING
        )
        USING iceberg
        PARTITIONED BY (days(event_time), bucket(16, user_id))
    """)
    
    print(f"💾 Appending data to {table_name}...")
    df.writeTo(table_name).append()
    
    print("✅ Ingestion Complete!")

# Call the ingestion function
if __name__ == "__main__":
    spark = create_spark_session()
    ingest_orders(spark)
    spark.stop()
