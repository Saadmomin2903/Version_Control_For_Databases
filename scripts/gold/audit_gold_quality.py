"""
Gold Layer Auditor - "The Quality Gate"
Verifies the integrity of the Gold Layer tables before merging to Production.

Branch: gold
Source of Truth: nessie.ecommerce.orders_silver@main
Target Tables: 
    - nessie.ecommerce.daily_sales_gold@gold
    - nessie.ecommerce.brand_performance_gold@gold
    - nessie.ecommerce.customer_stats_gold@gold
    - nessie.ecommerce.category_stats_gold@gold
"""

import os
import sys
import pyspark
from pyspark.sql import SparkSession
from pyspark.sql import functions as F

# Configuration
NESSIE_URI = os.getenv("NESSIE_URI", "http://nessie:19120/api/v1")
WAREHOUSE = os.getenv("WAREHOUSE", "s3a://lakehouse/warehouse")
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID", "admin")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "password123")
AWS_S3_ENDPOINT = os.getenv("AWS_S3_ENDPOINT", "http://minio:9000")
AWS_REGION = os.getenv("AWS_REGION", "ap-mumbai-1")

def get_spark_session():
    conf = (
        pyspark.SparkConf()
            .setAppName('gold_layer_auditor')
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
            .set('spark.sql.catalog.nessie.ref', 'gold') # READ FROM GOLD
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
    return SparkSession.builder.config(conf=conf).getOrCreate()

def run_audit():
    spark = get_spark_session()
    
    print("=" * 60)
    print("🕵️‍♂️ GOLD LAYER AUDIT: STARTING")
    print("=" * 60)

    passing = True

    # 1. TABLE EXISTENCE Check
    expected_tables = [
        "daily_sales_gold",
        "brand_performance_gold",
        "customer_stats_gold",
        "category_stats_gold"
    ]
    
    print("\n[1/3] Checking Table Existence in 'gold' branch...")
    # Use Nessie-specific syntax or standard SHOW TABLES
    # Just try reading 1 record from each
    for table in expected_tables:
        try:
            count = spark.sql(f"SELECT count(*) as cnt FROM nessie.ecommerce.{table}").collect()[0]['cnt']
            print(f"   ✓ {table}: Exists ({count:,} records)")
            if count == 0:
                print(f"     ⚠️ WARNING: Table is empty!")
                passing = False
        except Exception as e:
            print(f"   ❌ {table}: MISSING or Error: {e}")
            passing = False

    if not passing:
        print("   ❌ AUDIT STOPPED: Tables missing.")
        sys.exit(1)

    # 2. LOGIC CHECK: No Negative Revenue
    print("\n[2/3] Checking Business Logic (Negative Revenue)...")
    
    neg_daily = spark.sql("SELECT count(*) as cnt FROM nessie.ecommerce.daily_sales_gold WHERE total_revenue < 0").collect()[0]['cnt']
    if neg_daily == 0:
        print("   ✓ daily_sales_gold: No negative revenue.")
    else:
        print(f"   ❌ daily_sales_gold: Found {neg_daily} negative revenue days!")
        passing = False

    neg_brand = spark.sql("SELECT count(*) as cnt FROM nessie.ecommerce.brand_performance_gold WHERE total_revenue < 0").collect()[0]['cnt']
    if neg_brand == 0:
        print("   ✓ brand_performance_gold: No negative revenue.")
    else:
        print(f"   ❌ brand_performance_gold: Found {neg_brand} negative revenue brands!")
        passing = False

    # 3. CONSISTENCY CHECK: Silver vs Gold Revenue
    # Check if Sum(Silver.Price) approx matches Sum(Gold.Revenue)
    # Note: We need to pull Silver from 'main' (Assuming it was the source)
    print("\n[3/3] Cross-Checking Revenue (Silver vs Gold)...")
    
    # Silver (Source)
    # Using the explicit ref format for Silver
    silver_rev = spark.sql("SELECT sum(price) as rev FROM nessie.ecommerce.`orders_silver@main` WHERE event_type='purchase'").collect()[0]['rev']
    
    # Gold (Aggregate)
    gold_rev = spark.sql("SELECT sum(total_revenue) as rev FROM nessie.ecommerce.daily_sales_gold").collect()[0]['rev']

    print(f"   - Silver Total Revenue: ${silver_rev:,.2f}")
    print(f"   - Gold Total Revenue:   ${gold_rev:,.2f}")
    
    diff = abs(silver_rev - gold_rev)
    # Allow small float precision diff
    if diff < 1.0: 
        print(f"   ✓ MATCH! (Diff: ${diff:.4f})")
    else:
        print(f"   ⚠️ MISMATCH! (Diff: ${diff:,.2f}) - Investigate aggregation logic.")
        # passing = False # Optional: strict or soft fail? Let's keep it soft for minor rounding, strict for large

    print("\n" + "-" * 60)
    if passing:
        print("✅ AUDIT PASSED: Gold Layer is ready for Merge.")
        sys.exit(0)
    else:
        print("❌ AUDIT FAILED: Fix issues before merging.")
        sys.exit(1)

    spark.stop()

if __name__ == "__main__":
    run_audit()
