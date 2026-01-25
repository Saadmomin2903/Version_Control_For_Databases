"""
Merge Silver Branch to Main - WAP Pattern

1. Validate the silver branch.
2. Merge silver -> main.
3. Tag the release.
"""

import os
import sys
import pyspark
from pyspark.sql import SparkSession

# Configuration
NESSIE_URI = os.getenv("NESSIE_URI", "http://nessie:19120/api/v1")
WAREHOUSE = os.getenv("WAREHOUSE", "s3a://lakehouse/warehouse")
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID", "admin")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "password123")
AWS_S3_ENDPOINT = os.getenv("AWS_S3_ENDPOINT", "http://minio:9000")
AWS_REGION = os.getenv("AWS_REGION", "ap-mumbai-1")

print("=" * 70)
print("MERGE SILVER -> MAIN")
print("=" * 70)

conf = (
    pyspark.SparkConf()
        .setAppName('merge-silver')
        .set('spark.jars.packages', 
             'org.apache.iceberg:iceberg-spark-runtime-3.3_2.12:1.3.1,'
             'org.projectnessie.nessie-integrations:nessie-spark-extensions-3.3_2.12:0.67.0,'
             'software.amazon.awssdk:bundle:2.17.178,'
             'software.amazon.awssdk:url-connection-client:2.17.178')
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
        .set('spark.hadoop.fs.s3a.connection.ssl.enabled', 'false')
        .set('spark.hadoop.fs.s3a.impl', 'org.apache.hadoop.fs.s3a.S3AFileSystem')
        .set('spark.sql.catalog.nessie.s3.region', AWS_REGION)
        .set('spark.sql.catalog.nessie.client.region', AWS_REGION)
        .set('spark.hadoop.fs.s3a.endpoint.region', AWS_REGION)
)

spark = SparkSession.builder.config(conf=conf).getOrCreate()

print("🔧 Performing Merge: MERGE BRANCH silver INTO main IN nessie")
try:
    # Explicitly specify catalog 'nessie'
    spark.sql("MERGE BRANCH silver INTO main IN nessie")
    print("✅ Merge Successful!")
except Exception as e:
    print(f"❌ Merge Failed: {e}")
    sys.exit(1)

print("")
print("📊 Verifying 'main' branch content:")
try:
    # Check if table exists and has data in main
    count = spark.sql("SELECT COUNT(*) as cnt FROM nessie.ecommerce.orders_silver").collect()[0]['cnt']
    print(f"   Row Check: {count} records found in nessie.ecommerce.orders_silver (on main)")
    
    # Show history (optional, just to prove commit)
    # spark.sql("SHOW LOG IN nessie.ecommerce.orders_silver").show(3, truncate=False)
    
except Exception as e:
    print(f"⚠️ Verification warning: {e}")

spark.stop()
print("=" * 70)
