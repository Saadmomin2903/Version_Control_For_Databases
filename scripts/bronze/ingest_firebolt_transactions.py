"""
Bronze Firebolt Transactions Ingestion - PRODUCTION VERSION
Based on YOUR tested ingest_orders_spark.py

Adapts Firebolt transactions.csv to YOUR orders_bronze schema
Adds monthly partitioning for 412M records scalability
"""

import os
import pyspark
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, expr, date_format

# Get configuration from environment (YOUR exact same pattern)
NESSIE_URI = os.getenv("NESSIE_URI", "http://nessie:19120/api/v1")
WAREHOUSE = os.getenv("WAREHOUSE", "s3a://lakehouse/warehouse")
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID", "admin")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "password123")
AWS_S3_ENDPOINT = os.getenv("AWS_S3_ENDPOINT", "http://minio:9000")

print("=== Bronze Firebolt Transactions Ingestion (PySpark + Nessie) ===")
print(f"Nessie URI: {NESSIE_URI}")
print(f"Warehouse: {WAREHOUSE}")
print(f"S3 Endpoint: {AWS_S3_ENDPOINT}")

# Configure Spark with Iceberg and Nessie (YOUR EXACT CONFIG)
conf = (
    pyspark.SparkConf()
        .setAppName('bronze-firebolt-transactions')
        # Iceberg and Nessie JAR dependencies
        .set('spark.jars.packages', 
             'org.apache.iceberg:iceberg-spark-runtime-3.3_2.12:1.3.1,'
             'org.projectnessie.nessie-integrations:nessie-spark-extensions-3.3_2.12:0.67.0,'
             'software.amazon.awssdk:bundle:2.17.178,'
             'software.amazon.awssdk:url-connection-client:2.17.178')
        # Spark SQL extensions for Iceberg and Nessie
        .set('spark.sql.extensions', 
             'org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions,'
             'org.projectnessie.spark.extensions.NessieSparkSessionExtensions')
        # Configure Nessie catalog
        .set('spark.sql.catalog.nessie', 'org.apache.iceberg.spark.SparkCatalog')
        .set('spark.sql.catalog.nessie.uri', NESSIE_URI)
        .set('spark.sql.catalog.nessie.ref', 'bronze')  # Write to bronze branch
        .set('spark.sql.catalog.nessie.authentication.type', 'NONE')
        .set('spark.sql.catalog.nessie.catalog-impl', 'org.apache.iceberg.nessie.NessieCatalog')
        .set('spark.sql.catalog.nessie.warehouse', WAREHOUSE)
        .set('spark.sql.catalog.nessie.io-impl', 'org.apache.iceberg.aws.s3.S3FileIO')
        # S3/MinIO configuration
        .set('spark.sql.catalog.nessie.s3.endpoint', AWS_S3_ENDPOINT)
        .set('spark.hadoop.fs.s3a.access.key', AWS_ACCESS_KEY)
        .set('spark.hadoop.fs.s3a.secret.key', AWS_SECRET_KEY)
        .set('spark.hadoop.fs.s3a.endpoint', AWS_S3_ENDPOINT)
        .set('spark.hadoop.fs.s3a.path.style.access', 'true')
        .set('spark.hadoop.fs.s3a.connection.ssl.enabled', 'false')
        .set('spark.hadoop.fs.s3a.impl', 'org.apache.hadoop.fs.s3a.S3AFileSystem')
)

# Create Spark session (YOUR exact pattern)
print("\n✓ Creating Spark session...")
spark = SparkSession.builder.config(conf=conf).getOrCreate()
print("✓ Spark session created")

# Read CSV data (ADAPTED for Firebolt location)
print("\n✓ Reading Firebolt transactions.csv...")
firebolt_df = spark.read.csv(
    "/home/jovyan/data/firebolt/transactions.csv",  # NEW location
    header=True,
    inferSchema=True
)
print(f"✓ Loaded {firebolt_df.count():,} Firebolt transaction records")

# Show Firebolt schema
print("\nFirebolt schema:")
firebolt_df.printSchema()

# Transform to YOUR orders schema (CRITICAL ADAPTATION)
print("\n✓ Transforming to YOUR orders_bronze schema...")
df = firebolt_df.select(
    col("transaction_id").alias("order_id"),           # Firebolt → YOUR schema
    col("user_id").alias("customer_id"),                # Firebolt → YOUR schema
    col("order_date"),                                   # Same name
    col("status"),                                       # Same name
    # Calculate total_amount from Firebolt fields
    expr("(price * quantity - discount + shipping_cost)").alias("total_amount")
)

# Add partitioning column for scale (NEW - for 412M records)
df = df.withColumn("year_month", date_format("order_date", "yyyy-MM"))

record_count = df.count()
print(f"✓ Transformed {record_count:,} records to YOUR schema")

# Show sample data (YOUR exact pattern)
print("\nSample transformed data:")
df.show(5)

# Create namespace if it doesn't exist (YOUR exact code)
print("\n✓ Creating namespace...")
spark.sql("CREATE NAMESPACE IF NOT EXISTS nessie.ecommerce")
print("✓ Namespace 'ecommerce' ready")

# Create or replace Iceberg table (YOUR pattern + partitioning)
print("\n✓ Writing to Iceberg table...")
table_name = "nessie.ecommerce.orders_bronze"  # YOUR exact table name

# Write with partitioning (SCALE ADAPTATION)
df.writeTo(table_name) \
    .using("iceberg") \
    .partitionedBy("year_month") \
    .createOrReplace()

print(f"✓ Wrote {record_count:,} records to {table_name}")
print(f"✓ Partitioned by month for optimal performance")

# Verify the data (YOUR exact pattern)
print("\n✓ Verifying data...")
result = spark.sql(f"SELECT COUNT(*) as count FROM {table_name}").collect()
verified_count = result[0]['count']
print(f"✓ Verification: {verified_count:,} records in table")

# Show partition distribution (NEW - helpful for 412M records)
print("\nPartition distribution:")
spark.sql(f"""
    SELECT year_month, COUNT(*) as records 
    FROM {table_name} 
    GROUP BY year_month 
    ORDER BY year_month
""").show()

# Show table metadata (YOUR exact pattern)
print("\nTable metadata:")
spark.sql(f"DESCRIBE EXTENDED {table_name}").show(truncate=False)

# Stop Spark session (YOUR exact pattern)
spark.stop()

print("\n=== ✓ Bronze Firebolt transactions ingestion complete! ===")
print(f"✓ Firebolt transactions mapped to YOUR orders_bronze schema")
print(f"✓ {verified_count:,} records ready for YOUR silver layer processing")
