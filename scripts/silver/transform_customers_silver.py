"""
Silver Customers Transformation - Write-Audit-Publish Pattern

Reads from customers_bronze@bronze, applies transformations, writes to customers_silver@silver
"""

import os
import sys
import pyspark
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import StringType

# Add utils to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from utils.quality_checks import QualityChecker

# Configuration
NESSIE_URI = os.getenv("NESSIE_URI", "http://172.18.0.2:19120/api/v1")
WAREHOUSE = os.getenv("WAREHOUSE", "s3a://lakehouse/warehouse")
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID", "admin")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "password123")
AWS_S3_ENDPOINT = os.getenv("AWS_S3_ENDPOINT", "http://minio:9000")

print("=" * 70)
print("SILVER CUSTOMERS TRANSFORMATION - Write-Audit-Publish Pattern")
print("=" * 70)
print("")

# Spark configuration
conf = (
    pyspark.SparkConf()
        .setAppName('silver-customers')
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
bronze_df = spark.sql("SELECT * FROM nessie.ecommerce.`customers_bronze@bronze`")
bronze_count = bronze_df.count()
print(f"✓ Read {bronze_count} records from bronze branch")
print("")

print("🔧 Step 2: Apply Silver transformations")
print("-" * 70)

# Remove duplicates by customer_id
silver_df = bronze_df.dropDuplicates(["customer_id"])

# Standardize email - lowercase
silver_df = silver_df.withColumn("email", F.lower(F.col("email")))

# Validate email format (contains @)
silver_df = silver_df.withColumn(
    "email_valid",
    F.col("email").contains("@")
)

# Calculate data quality score
silver_df = silver_df.withColumn(
    "data_quality_score",
    F.when(
        (F.col("customer_id").isNotNull()) &
        (F.col("email").isNotNull()) &
        (F.col("email_valid") == True) &
        (F.col("name").isNotNull()),
        100
    ).when(
        (F.col("customer_id").isNotNull()) &
        (F.col("email").isNotNull()),
        75
    ).otherwise(50)
)

# Add processing metadata
silver_df = silver_df.withColumn("processed_at", F.current_timestamp())
silver_df = silver_df.withColumn("source_branch", F.lit("bronze"))

silver_count = silver_df.count()
duplicates_removed = bronze_count - silver_count
print(f"✓ Removed {duplicates_removed} duplicates")
print(f"✓ Standardized email addresses (lowercase)")
print(f"✓ Added email validation flag")
print(f"✓ Calculated quality scores")
print(f"✓ {silver_count} records ready for Silver")
print("")

print("✅ Step 3: Quality Checks")
print("-" * 70)
try:
    checker = QualityChecker(silver_df, "customers_silver")
    checker.check_row_count(min_expected=int(bronze_count * 0.90))
    checker.check_nulls(["customer_id", "email", "name"])
    checker.check_duplicates(["customer_id"])
    
    # Check email validity - at least 95% should be valid
    valid_emails = silver_df.filter(F.col("email_valid") == True).count()
    email_validity_rate = (valid_emails / silver_count) * 100
    print(f"  ✓ Email validity rate: {email_validity_rate:.1f}%")
    
    if email_validity_rate < 95:
        raise Exception(f"Email validity rate {email_validity_rate:.1f}% below threshold (95%)")
    
    checker.validate(raise_on_failure=True)
except Exception as e:
    print(f"✗ Quality checks failed: {e}")
    spark.stop()
    sys.exit(1)

print("")

print("💾 Step 4: Write to SILVER branch")
print("-" * 70)

# Create temp view
silver_df.createOrReplaceTempView("silver_customers_temp")

# Create namespace if needed
try:
    spark.sql("CREATE NAMESPACE IF NOT EXISTS nessie.ecommerce")
    print("✓ Namespace verified")
except:
    pass

# Write to silver branch using @silver syntax
print(f"✓ Writing {silver_count} records to silver branch...")
spark.sql("""
    CREATE OR REPLACE TABLE nessie.ecommerce.`customers_silver@silver`
    USING iceberg
    AS SELECT * FROM silver_customers_temp
""")
print("✓ Table created on silver branch")

# Verify the write
verify_count = spark.sql("SELECT COUNT(*) as cnt FROM nessie.ecommerce.`customers_silver@silver`").collect()[0]['cnt']
print(f"✓ Verified: {verify_count} records in customers_silver on silver branch")

# Show sample data
print("\n📊 Sample Silver data:")
spark.sql("""
    SELECT customer_id, name, email, signup_date, is_active, email_valid, data_quality_score 
    FROM nessie.ecommerce.`customers_silver@silver` 
    LIMIT 5
""").show(truncate=False)

# Show quality score distribution
print("\n📈 Quality Score Distribution:")
spark.sql("""
    SELECT data_quality_score, COUNT(*) as count
    FROM nessie.ecommerce.`customers_silver@silver`
    GROUP BY data_quality_score
    ORDER BY data_quality_score DESC
""").show()

spark.stop()

print("")
print("=" * 70)
print("✅ SILVER CUSTOMERS TRANSFORMATION COMPLETE!")
print("=" * 70)
print("")
print("Summary:")
print(f"  📥 Input:  {bronze_count} records from bronze branch")
print(f"  📤 Output: {verify_count} records to silver branch")
print(f"  🧹 Cleaned: Emails lowercase, validated format")
print(f"  ✓ Validated: {email_validity_rate:.1f}% valid emails")
print(f"  🎯 Quality: All checks passed")
print(f"  🌿 Branch: Data isolated on 'silver' branch")
print("=" * 70)
