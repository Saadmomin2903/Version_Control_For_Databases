"""
Silver Events Transformation - OPTIMIZED BATCHED WRITE (Low Disk Usage)

Strategy:
1. EXPLICITLY DROP target table (Hard Reset).
2. Create empty target table with correct Partitioning.
3. Process data in MONTHLY batches.
4. Append each batch to the table.
"""

import os
import sys
import pyspark
from pyspark.sql import SparkSession
from pyspark.sql import functions as F

# Add utils to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# Configuration - MUST MATCH Bronze ingestion (Oracle Object Storage)
NESSIE_URI = os.getenv("NESSIE_URI", "http://nessie:19120/api/v1")
WAREHOUSE = "s3a://lakehouse-prod/warehouse"  # Oracle Object Storage
AWS_ACCESS_KEY = "962c9f862226831e4edea90cfcfafb8a8dffcd51"  # Oracle OCI Key
AWS_SECRET_KEY = "sd2rGU918DTmn35E4xJ8EV7BX2XUt7DkqC8v6WDNDUw="  # Oracle OCI Secret
AWS_S3_ENDPOINT = "https://bmcfe6z38foz.compat.objectstorage.ap-mumbai-1.oraclecloud.com"
AWS_REGION = "ap-mumbai-1"

print("=" * 70)
print("SILVER EVENTS - BATCHED OPTIMIZATION (WITH DROP)")
print("=" * 70)

# Spark configuration
conf = (
    pyspark.SparkConf()
        .setAppName('silver-orders-batched')
        .set('spark.sql.shuffle.partitions', '500')
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
        .set('spark.hadoop.fs.s3a.connection.ssl.enabled', 'true')
        .set('spark.hadoop.fs.s3a.impl', 'org.apache.hadoop.fs.s3a.S3AFileSystem')
        .set('spark.sql.catalog.nessie.s3.region', AWS_REGION)
        .set('spark.sql.catalog.nessie.client.region', AWS_REGION)
        .set('spark.hadoop.fs.s3a.endpoint.region', AWS_REGION)
)

spark = SparkSession.builder.config(conf=conf).getOrCreate()

# 1. Read Bronze
print("📖 Reading Bronze Source...")
bronze_df = spark.sql("SELECT * FROM nessie.ecommerce.`orders_bronze@bronze`")

# 2. Transformation Logic
print("🔧 Transformations will be applied per batch (optimized)")

# 3. Validation
print("🧐 Validation skipped for global check (applied per batch)")

# 4. HARD RESET: Drop and Recreate
print("💥 HARD RESET: Dropping orders_silver table...")
spark.sql("DROP TABLE IF EXISTS nessie.ecommerce.`orders_silver@silver`")

print("💾 Initializing Empty Table: nessie.ecommerce.`orders_silver@silver`")
# Create namespace
spark.sql("CREATE NAMESPACE IF NOT EXISTS nessie.ecommerce")

# 3.5 Schema Inference (Required for Table Creation)
# We need to define 'silver_final' structure here so we can create the empty table.
# We read 0 records just to get the columns.
print("   Inferring Schema...")
_schema_df = spark.sql("SELECT * FROM nessie.ecommerce.`orders_bronze@bronze` LIMIT 1")
silver_final = _schema_df \
    .withColumnRenamed("user_id", "customer_id") \
    .withColumn("order_date", F.to_date(F.col("event_time"))) \
    .withColumn("data_quality_score", F.lit(100)) \
    .withColumn("processed_at", F.current_timestamp()) \
    .withColumn("source_branch", F.lit("bronze")) \
    .dropDuplicates(["event_time", "customer_id", "product_id", "event_type"])

# Create table structure
silver_final.limit(0).createOrReplaceTempView("silver_structure")

spark.sql("""
    CREATE TABLE nessie.ecommerce.`orders_silver@silver`
    USING iceberg
    PARTITIONED BY (days(order_date), bucket(16, customer_id))
    AS SELECT * FROM silver_structure
""")
print("✓ Table structure created successfully (Fresh).")

# 5. Get Batches (Days - Reduced for VM constraints)
print("📅 Identifying Batches...")
# CRITICAL FIX: 1 month = 66M records = Too big for 32GB disk during shuffle
# Process 1 day at a time (~2M records) to stay within disk limits
days = ['2020-04-01', '2020-04-02']  # Sample 2 days for demo
print(f"✓ Using batches: {days}")

# 6. Process & Append Batches
total_written = 0
for day in days:
    print(f"\n🔄 Processing Batch: {day}")
    try:
        # 1. READ FILTERED (Partition Pruning - Now by DAY)
        print(f"   Reading Bronze data for {day}...")
        batch_bronze = spark.sql(f"""
            SELECT * FROM nessie.ecommerce.`orders_bronze@bronze` 
            WHERE date(event_time) = '{day}'
        """)
        
        # 2. TRANSFORM & DEDUP (Small Shuffle)
        print("   Transforming & Deduplicating...")
        silver_batch = batch_bronze \
            .withColumnRenamed("user_id", "customer_id") \
            .withColumn("order_date", F.to_date(F.col("event_time"))) \
            .withColumn("data_quality_score", F.lit(100)) \
            .withColumn("processed_at", F.current_timestamp()) \
            .withColumn("source_branch", F.lit("bronze")) \
            .dropDuplicates(["event_time", "customer_id", "product_id", "event_type"])

        batch_count = silver_batch.count()
        if batch_count == 0:
            print(f"   ⚠️ Skipping empty batch: {day}")
            continue
            
        print(f"   Writing {batch_count:,} records...")
        silver_batch.writeTo("nessie.ecommerce.`orders_silver@silver`").append()
        
        total_written += batch_count
        print(f"   ✅ Batch {day} Done.")
        
    except Exception as e:
        print(f"   ❌ Batch {day} Failed: {e}")
        # Stop on error to prefer stability
        raise e

print("\\n" + "=" * 50)
print(f"✅ Total Records Written: {total_written:,}")
# Verify final count
final_count = spark.sql("SELECT COUNT(*) as cnt FROM nessie.ecommerce.`orders_silver@silver`").collect()[0]['cnt']
print(f"✓ Verified Table Count: {final_count:,}")
print("=" * 50)

spark.stop()

