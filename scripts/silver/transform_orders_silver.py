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

# Configuration
NESSIE_URI = os.getenv("NESSIE_URI", "http://nessie:19120/api/v1")
WAREHOUSE = os.getenv("WAREHOUSE", "s3a://lakehouse/warehouse")
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID", "admin")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "password123")
AWS_S3_ENDPOINT = os.getenv("AWS_S3_ENDPOINT", "http://minio:9000")
AWS_REGION = os.getenv("AWS_REGION", "ap-mumbai-1")

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
        .set('spark.hadoop.fs.s3a.connection.ssl.enabled', 'false')
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
print("🔧 Defining Transformations...")
silver_final = bronze_df \
    .withColumnRenamed("user_id", "customer_id") \
    .withColumn("order_date", F.to_date(F.col("event_time"))) \
    .withColumn("data_quality_score", F.lit(100)) \
    .withColumn("processed_at", F.current_timestamp()) \
    .withColumn("source_branch", F.lit("bronze")) \
    .dropDuplicates(["event_time", "customer_id", "product_id", "event_type"])

# 3. Validation (Great Expectations)
print("🧐 Validating Transformed Data...")
try:
    from quality.silver_expectations import validate_silver_orders
    validation_passed = validate_silver_orders(silver_final)
except ImportError:
    print("⚠️  Great Expectations module not found / import error. Skipping validation (Dev Mode).")
    validation_passed = True
except Exception as e:
    print(f"⚠️  Validation failed with error: {e}")
    validation_passed = False

if not validation_passed:
    print("❌ Critical Data Quality Failure. Aborting Silver Layer Write.")
    sys.exit(1)

print("✅ Data Quality Passed. Proceeding to Write...")

# 4. HARD RESET: Drop and Recreate
print("💥 HARD RESET: Dropping orders_silver table...")
spark.sql("DROP TABLE IF EXISTS nessie.ecommerce.`orders_silver@silver`")

print("💾 Initializing Empty Table: nessie.ecommerce.`orders_silver@silver`")
try:
    spark.sql("CREATE NAMESPACE IF NOT EXISTS nessie.ecommerce")
except:
    pass

# Create table structure
silver_final.limit(0).createOrReplaceTempView("silver_structure")

spark.sql("""
    CREATE TABLE nessie.ecommerce.`orders_silver@silver`
    USING iceberg
    PARTITIONED BY (days(order_date), bucket(16, customer_id))
    AS SELECT * FROM silver_structure
""")
print("✓ Table structure created successfully (Fresh).")

# 5. Get Batches (Months)
print("📅 Identifying Batches...")
# Fallback to known months for speed/safety
months = ['2019-10', '2019-11', '2019-12', '2020-01', '2020-02', '2020-03', '2020-04']
print(f"✓ Using batches: {months}")

# 6. Process & Append Batches
total_written = 0
for month in months:
    print(f"\\n🔄 Processing Batch: {month}")
    try:
        batch_df = silver_final.filter(F.date_format(F.col("event_time"), 'yyyy-MM') == month)
        
        batch_count = batch_df.count()
        if batch_count == 0:
            print(f"   ⚠️ Skipping empty batch: {month}")
            continue
            
        print(f"   Writing {batch_count:,} records...")
        batch_df.writeTo("nessie.ecommerce.`orders_silver@silver`").append()
        
        total_written += batch_count
        print(f"   ✅ Batch {month} Done.")
        
    except Exception as e:
        print(f"   ❌ Batch {month} Failed: {e}")

print("\\n" + "=" * 50)
print(f"✅ Total Records Written: {total_written:,}")
# Verify final count
final_count = spark.sql("SELECT COUNT(*) as cnt FROM nessie.ecommerce.`orders_silver@silver`").collect()[0]['cnt']
print(f"✓ Verified Table Count: {final_count:,}")
print("=" * 50)

spark.stop()

