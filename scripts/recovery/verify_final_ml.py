from pyspark.sql import SparkSession
import os
import sys

# S3 Config
AWS_ACCESS_KEY = "962c9f862226831e4edea90cfcfafb8a8dffcd51"
AWS_SECRET_KEY = "sd2rGU918DTmn35E4xJ8EV7BX2XUt7DkqC8v6WDNDUw="
AWS_S3_ENDPOINT = "https://bmcfe6z38foz.compat.objectstorage.ap-mumbai-1.oraclecloud.com"
AWS_REGION = "ap-mumbai-1"
NESSIE_URI = "http://172.18.0.2:19120/api/v1"
WAREHOUSE = "s3a://lakehouse-prod/warehouse"

spark = (SparkSession.builder
    .appName("verify-final-ml")
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
    .getOrCreate())

tables = [
    "product_recommendations_ml",
    "customer_segments_ml",
    "churn_predictions_ml",
    "clv_predictions_ml",
    "next_purchase_predictions_ml"
]

print("="*60)
print("🔍 VERIFYING FINAL ML TABLES (FULL RUN)")
print("="*60)

for tbl in tables:
    try:
        full_name = f"nessie.ecommerce.{tbl}"
        df = spark.table(full_name)
        count = df.count()
        print(f"✅ {tbl}: {count:,} rows")
        
        # Show sample to verify schema/data quality
        print(f"   Sample Data for {tbl}:")
        df.show(3, False)
        
    except Exception as e:
        print(f"❌ {tbl}: FAILED / MISSING")
        print(f"   Error: {str(e)}")

print("\nDONE.")
spark.stop()
