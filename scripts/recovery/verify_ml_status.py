"""
Verify ML Table Status
Checks if Real ML pipeline (SparkML) or SQL pipeline populated the tables
by comparing row counts and checking table history.
"""

from pyspark.sql import SparkSession
import sys

# S3 Config
AWS_ACCESS_KEY = "962c9f862226831e4edea90cfcfafb8a8dffcd51"
AWS_SECRET_KEY = "sd2rGU918DTmn35E4xJ8EV7BX2XUt7DkqC8v6WDNDUw="
AWS_S3_ENDPOINT = "https://bmcfe6z38foz.compat.objectstorage.ap-mumbai-1.oraclecloud.com"
AWS_REGION = "ap-mumbai-1"
NESSIE_URI = "http://172.18.0.2:19120/api/v1"
WAREHOUSE = "s3a://lakehouse-prod/warehouse"

spark = (SparkSession.builder
    .appName("verify-ml-status")
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

print("\n" + "="*50)
print("🔍 VERIFYING TABLE STATUS")
print("="*50)

tables_to_check = [
    "nessie.ecommerce.churn_predictions_full",
    "nessie.ecommerce.churn_predictions_ml",
    "nessie.ecommerce.customer_segments_ml",
    "nessie.ecommerce.clv_predictions_ml"
]

for table in tables_to_check:
    print(f"\nChecking {table}...")
    try:
        # Check Row Count
        count = spark.table(table).count()
        print(f"   📊 Row Count: {count:,}")
        
        # Check History (last commit)
        history = spark.sql(f"SELECT committed_at, snapshot_id FROM {table}.history ORDER BY committed_at DESC LIMIT 1").collect()
        if history:
            print(f"   🕒 Last Updated: {history[0]['committed_at']}")
            print(f"   🆔 Snapshot ID: {history[0]['snapshot_id']}")
        
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")

print("\n" + "="*50)
spark.stop()
