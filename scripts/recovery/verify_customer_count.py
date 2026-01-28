from pyspark.sql import SparkSession
import os

# S3 Config (Same as pipeline)
AWS_ACCESS_KEY = "962c9f862226831e4edea90cfcfafb8a8dffcd51"
AWS_SECRET_KEY = "sd2rGU918DTmn35E4xJ8EV7BX2XUt7DkqC8v6WDNDUw="
AWS_S3_ENDPOINT = "https://bmcfe6z38foz.compat.objectstorage.ap-mumbai-1.oraclecloud.com"
AWS_REGION = "ap-mumbai-1"
NESSIE_URI = "http://172.18.0.2:19120/api/v1"
WAREHOUSE = "s3a://lakehouse-prod/warehouse"

spark = (SparkSession.builder
    .appName("verify-customer-count")
    .config("spark.sql.catalog.nessie", "org.apache.iceberg.spark.SparkCatalog")
    .config("spark.sql.catalog.nessie.uri", NESSIE_URI)
    .config("spark.sql.catalog.nessie.ref", "main")
    .config("spark.sql.catalog.nessie.catalog-impl", "org.apache.iceberg.nessie.NessieCatalog")
    .config("spark.sql.catalog.nessie.warehouse", WAREHOUSE)
    .config("spark.sql.catalog.nessie.io-impl", "org.apache.iceberg.aws.s3.S3FileIO")
    .config("spark.sql.catalog.nessie.s3.endpoint", AWS_S3_ENDPOINT)
    .config("spark.sql.catalog.nessie.s3.region", AWS_REGION)
    .config("spark.sql.catalog.nessie.s3.path-style-access", "true")
    .config("spark.sql.catalog.nessie.s3.access-key-id", AWS_ACCESS_KEY)
    .config("spark.sql.catalog.nessie.s3.secret-access-key", AWS_SECRET_KEY)
    .config("spark.sql.catalog.nessie.client.region", AWS_REGION)
    .config("spark.hadoop.fs.s3a.access.key", AWS_ACCESS_KEY)
    .config("spark.hadoop.fs.s3a.secret.key", AWS_SECRET_KEY)
    .config("spark.hadoop.fs.s3a.endpoint", AWS_S3_ENDPOINT)
    .config("spark.hadoop.fs.s3a.path.style.access", "true")
    .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem")
    .config("spark.executor.memory", "4g")
    .getOrCreate())

print("="*60)
print("🔍 VERIFYING DISTINCT CUSTOMERS (SOURCE vs OUTPUT)")
print("="*60)

# Check Source Count (Distinct Customers)
print("Counting distinct customers in 'orders_silver'...")
source_customers = spark.sql("SELECT COUNT(DISTINCT customer_id) FROM nessie.ecommerce.orders_silver WHERE customer_id IS NOT NULL").collect()[0][0]
print(f"✅ Source (orders_silver) Unique Customers: {source_customers:,}")

# Check Output Count
print("Counting rows in 'churn_predictions_ml'...")
output_rows = spark.table("nessie.ecommerce.churn_predictions_ml").count()
print(f"✅ Output (churn_predictions_ml) Rows: {output_rows:,}")

# Ratio
print(f"📊 Ratio: {output_rows/source_customers:.4f} (Should be 1.0)")
spark.stop()
