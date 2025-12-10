"""
Silver Orders Transformation - CORRECTED VERSION

Based on official Nessie documentation:
- Use @branch syntax to write to specific branch
- Example: nessie.db.`table@my_branch`
"""

import os
import sys
import pyspark
from pyspark.sql import SparkSession
from pyspark.sql import functions as F

# Add utils to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from utils.quality_checks import QualityChecker

# Configuration
NESSIE_URI = os.getenv("NESSIE_URI", "http://nessie:19120/api/v1")
WAREHOUSE = os.getenv("WAREHOUSE", "s3a://lakehouse/warehouse")
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID", "admin")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "password123")
AWS_S3_ENDPOINT = os.getenv("AWS_S3_ENDPOINT", "http://minio:9000")

print("=" * 70)
print("SILVER ORDERS TRANSFORMATION - Write-Audit-Publish Pattern")
print("=" * 70)
print("")

# Spark configuration - start on main, will switch branches
conf = (
    pyspark.SparkConf()
        .setAppName('silver-orders')
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
)

spark = SparkSession.builder.config(conf=conf).getOrCreate()

print("📖 Step 1: Read from BRONZE branch")
print("-" * 70)
# Read from bronze branch using @branch syntax in table name
bronze_df = spark.sql("SELECT * FROM nessie.ecommerce.`orders_bronze@bronze`")
bronze_count = bronze_df.count()
print(f"✓ Read {bronze_count} records from bronze branch")
print("")

print("🔧 Step 2: Apply Silver transformations")
print("-" * 70)
# Remove duplicates
silver_df = bronze_df.dropDuplicates(["order_id"])

# Add data quality score
silver_df = silver_df.withColumn(
    "data_quality_score",
    F.when(
        (F.col("order_id").isNotNull()) &
        (F.col("customer_id").isNotNull()) &
        (F.col("total_amount") > 0) &
        (F.col("status").isNotNull()),
        100
    ).otherwise(50)
)

# Add processing metadata
silver_df = silver_df.withColumn("processed_at", F.current_timestamp())
silver_df = silver_df.withColumn("source_branch", F.lit("bronze"))

silver_count = silver_df.count()
print(f"✓ Removed {bronze_count - silver_count} duplicates")
print(f"✓ Added quality score and metadata")
print(f"✓ {silver_count} records ready for Silver")
print("")

print("✅ Step 3: Quality Checks")
print("-" * 70)
try:
    checker = QualityChecker(silver_df, "orders_silver")
    checker.check_row_count(min_expected=int(bronze_count * 0.90))
    checker.check_nulls(["order_id", "customer_id"])
    checker.check_duplicates(["order_id"])
    checker.check_value_range("total_amount", min_val=0)
    checker.validate(raise_on_failure=True)
except Exception as e:
    print(f"✗ Quality checks failed: {e}")
    spark.stop()
    sys.exit(1)

print("")

print("💾 Step 4: Write to SILVER branch")
print("-" * 70)
# Create temp view
silver_df.createOrReplaceTempView("silver_temp")

# Create namespace if needed
try:
    spark.sql("CREATE NAMESPACE IF NOT EXISTS nessie.ecommerce")
    print("✓ Namespace verified")
except:
    pass

# Write to silver branch using @silver syntax
print(f"✓ Writing {silver_count} records to silver branch...")
spark.sql("""
    CREATE OR REPLACE TABLE nessie.ecommerce.`orders_silver@silver`
    USING iceberg
    AS SELECT * FROM silver_temp
""")
print("✓ Table created on silver branch")

# Verify the write
verify_count = spark.sql("SELECT COUNT(*) as cnt FROM nessie.ecommerce.`orders_silver@silver`").collect()[0]['cnt']
print(f"✓ Verified: {verify_count} records in orders_silver on silver branch")

# Show sample
print("\n📊 Sample Silver data:")
spark.sql("SELECT order_id, customer_id, total_amount, status, data_quality_score FROM nessie.ecommerce.`orders_silver@silver` LIMIT 5").show()

spark.stop()

print("")
print("=" * 70)
print("✅ SILVER TRANSFORMATION COMPLETE!")
print("=" * 70)
print("")
print("Summary:")
print(f"  📥 Input:  {bronze_count} records from bronze branch")
print(f"  📤 Output: {verify_count} records to silver branch")
print(f"  🎯 Quality: All checks passed")
print(f"  🌿 Branch: Data isolated on 'silver' branch")
print("=" * 70)
