#!/usr/bin/env python3
"""
Standalone Bronze Table Query Script (No Dependencies)
"""

import pyspark
from pyspark.sql import SparkSession
from pyspark.sql import functions as F

# Configuration - Oracle Cloud Object Storage
NESSIE_URI = "http://172.18.0.2:19120/api/v1"
WAREHOUSE = "s3a://lakehouse-prod/warehouse"
AWS_ACCESS_KEY = "962c9f862226831e4edea90cfcfafb8a8dffcd51"
AWS_SECRET_KEY = "sd2rGU918DTmn35E4xJ8EV7BX2XUt7DkqC8v6WDNDUw="
AWS_S3_ENDPOINT = "https://bmcfe6z38foz.compat.objectstorage.ap-mumbai-1.oraclecloud.com"
AWS_REGION = "ap-mumbai-1"

print("\n" + "="*70)
print("BRONZE TABLE QUERY - STANDALONE")
print("="*70)

# Create Spark session with full configuration
conf = (
    pyspark.SparkConf()
        .setAppName('bronze-query')
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
        .set('spark.hadoop.fs.s3a.access.key', AWS_ACCESS_KEY)
        .set('spark.hadoop.fs.s3a.secret.key', AWS_SECRET_KEY)
        .set('spark.hadoop.fs.s3a.endpoint', AWS_S3_ENDPOINT)
        .set('spark.hadoop.fs.s3a.path.style.access', 'true')
        .set('spark.hadoop.fs.s3a.connection.ssl.enabled', 'true')
        .set('spark.hadoop.fs.s3a.impl', 'org.apache.hadoop.fs.s3a.S3AFileSystem')
        .set('spark.sql.catalog.nessie.s3.region', AWS_REGION)
        .set('spark.sql.catalog.nessie.client.region', AWS_REGION)
        .set('spark.hadoop.fs.s3a.endpoint.region', AWS_REGION)
)

spark = SparkSession.builder.config(conf=conf).getOrCreate()

print("\n✅ Spark session created")

# Load Bronze table
print("\n📖 Reading Bronze table...")
df = spark.table('nessie.ecommerce.orders_bronze')

# Total count
total = df.count()
print(f"\n📊 Total Records: {total:,}")

# Schema
print("\n📋 Schema:")
df.printSchema()

# Date range
date_stats = df.agg(
    F.min('event_time').alias('min_date'),
    F.max('event_time').alias('max_date')
).collect()[0]
print(f"\n📅 Date Range:")
print(f"  Start: {date_stats['min_date']}")
print(f"  End:   {date_stats['max_date']}")

# Monthly breakdown
print("\n📈 Monthly Breakdown:")
monthly = df.groupBy(
    F.year('event_time').alias('year'),
    F.month('event_time').alias('month')
).agg(
    F.count('*').alias('records'),
    F.countDistinct('user_id').alias('users'),
    F.countDistinct('product_id').alias('products'),
    F.sum('price').alias('revenue')
).orderBy('year', 'month')
monthly.show(truncate=False)

# Event types
print("\n🎯 Event Type Distribution:")
df.groupBy('event_type').count().orderBy(F.desc('count')).show()

# Sample data (5 rows)
print("\n📋 Sample Data:")
df.show(5, truncate=False)

# Top categories
print("\n🏷️ Top 10 Categories:")
df.groupBy('category_code').count().orderBy(F.desc('count')).limit(10).show(truncate=False)

# Price statistics
print("\n💰 Price Statistics:")
price_stats = df.agg(
    F.min('price').alias('min_price'),
    F.avg('price').alias('avg_price'),
    F.max('price').alias('max_price'),
    F.sum('price').alias('total_revenue')
).collect()[0]

print(f"  Min Price:     ${price_stats['min_price']:.2f}")
print(f"  Avg Price:     ${price_stats['avg_price']:.2f}")
print(f"  Max Price:     ${price_stats['max_price']:.2f}")
print(f"  Total Revenue: ${price_stats['total_revenue']:,.2f}")

print("\n" + "="*70)
print("✅ Query Complete!")
print("="*70 + "\n")

spark.stop()
