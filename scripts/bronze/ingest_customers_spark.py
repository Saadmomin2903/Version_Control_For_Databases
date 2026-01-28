"""
Bronze Customers Ingestion using PySpark with Nessie Catalog

This script is designed to run inside the Spark notebook container.
It reads CSV data and writes to Iceberg tables managed by Nessie.
"""

import os
import pyspark
from pyspark.sql import SparkSession

# Get configuration from environment
NESSIE_URI = os.getenv("NESSIE_URI", "http://172.18.0.2:19120/api/v1")
WAREHOUSE = os.getenv("WAREHOUSE", "s3a://lakehouse/warehouse")
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID", "admin")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "password123")
AWS_S3_ENDPOINT = os.getenv("AWS_S3_ENDPOINT", "http://minio:9000")

print("=== Bronze Customers Ingestion (PySpark + Nessie) ===")
print(f"Nessie URI: {NESSIE_URI}")
print(f"Warehouse: {WAREHOUSE}")
print(f"S3 Endpoint: {AWS_S3_ENDPOINT}")

# Configure Spark with Iceberg and Nessie
conf = (
    pyspark.SparkConf()
        .setAppName('bronze-customers-ingestion')
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

# Create Spark session
print("\n✓ Creating Spark session...")
spark = SparkSession.builder.config(conf=conf).getOrCreate()
print("✓ Spark session created")

# Read CSV data
print("\n✓ Reading customers.csv...")
df = spark.read.csv(
    "/home/jovyan/data/raw/customers.csv",
    header=True,
    inferSchema=True
).limit(1000)
record_count = df.count()
print(f"✓ Loaded {record_count} records")

# Show sample data
print("\nSample data:")
df.show(5)

# Create namespace if it doesn't exist
print("\n✓ Creating namespace...")
spark.sql("CREATE NAMESPACE IF NOT EXISTS nessie.ecommerce")
print("✓ Namespace 'ecommerce' ready")

# Create or replace Iceberg table
print("\n✓ Writing to Iceberg table...")
table_name = "nessie.ecommerce.customers_bronze"

df.writeTo(table_name).using("iceberg").createOrReplace()
print(f"✓ Wrote {record_count} records to {table_name}")

# Verify the data
print("\n✓ Verifying data...")
result = spark.sql(f"SELECT COUNT(*) as count FROM {table_name}").collect()
verified_count = result[0]['count']
print(f"✓ Verification: {verified_count} records in table")

# Show table metadata
print("\nTable metadata:")
spark.sql(f"DESCRIBE EXTENDED {table_name}").show(truncate=False)

# Stop Spark session
spark.stop()

print("\n=== ✓ Bronze customers ingestion complete! ===")
