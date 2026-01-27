"""
Create Synthetic Customers Silver from Bronze Orders
---------------------------------------------------
This script fills the gap for the missing customers dataset.
It extracts unique 'user_id's from orders_bronze and generates 
synthetic attributes (name, email, signup_date) to unblock 
Silver/Gold/ML layers.

Reads from: nessie.ecommerce.orders_bronze@bronze
Writes to: nessie.ecommerce.customers_silver@silver
"""

import os
import sys
import pyspark
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from datetime import datetime

# Configuration
NESSIE_URI = os.getenv("NESSIE_URI", "http://172.18.0.2:19120/api/v1")
WAREHOUSE = "s3a://lakehouse-prod/warehouse"
AWS_ACCESS_KEY = "962c9f862226831e4edea90cfcfafb8a8dffcd51"
AWS_SECRET_KEY = "sd2rGU918DTmn35E4xJ8EV7BX2XUt7DkqC8v6WDNDUw="
AWS_S3_ENDPOINT = "https://bmcfe6z38foz.compat.objectstorage.ap-mumbai-1.oraclecloud.com"
AWS_REGION = "ap-mumbai-1"

print("=" * 70)
print("🚀 SYNTHETIC CUSTOMER GENERATION (Full Dataset Mode)")
print("=" * 70)

def get_spark_session():
    conf = (
        pyspark.SparkConf()
            .setAppName('synthetic-customers-gen')
            .set('spark.sql.shuffle.partitions', '200')
            .set('spark.jars.packages', 
                 'org.apache.iceberg:iceberg-spark-runtime-3.3_2.12:1.3.1,'
                 'org.projectnessie.nessie-integrations:nessie-spark-extensions-3.3_2.12:0.67.0,'
                 'software.amazon.awssdk:bundle:2.17.178,'
                 'software.amazon.awssdk:url-connection-client:2.17.178,'
                 'org.apache.hadoop:hadoop-aws:3.3.1')
            .set('spark.sql.extensions', 
                 'org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions,'
                 'org.projectnessie.spark.extensions.NessieSparkSessionExtensions')
            .set('spark.sql.catalog.nessie', 'org.apache.iceberg.spark.SparkCatalog')
            .set('spark.sql.catalog.nessie.uri', NESSIE_URI)
            .set('spark.sql.catalog.nessie.ref', 'silver') 
            .set('spark.sql.catalog.nessie.authentication.type', 'NONE')
            .set('spark.sql.catalog.nessie.catalog-impl', 'org.apache.iceberg.nessie.NessieCatalog')
            .set('spark.sql.catalog.nessie.warehouse', WAREHOUSE)
            .set('spark.sql.catalog.nessie.io-impl', 'org.apache.iceberg.hadoop.HadoopFileIO')
            .set('spark.sql.catalog.nessie.s3.endpoint', AWS_S3_ENDPOINT)
            .set('spark.sql.catalog.nessie.s3.region', AWS_REGION)
            .set('spark.sql.catalog.nessie.s3.path-style-access', 'true')
            .set('spark.hadoop.fs.s3a.access.key', AWS_ACCESS_KEY)
            .set('spark.hadoop.fs.s3a.secret.key', AWS_SECRET_KEY)
            .set('spark.hadoop.fs.s3a.endpoint', AWS_S3_ENDPOINT)
            .set('spark.hadoop.fs.s3a.path-style-access', 'true')
            .set('spark.hadoop.fs.s3a.connection.ssl.enabled', 'true')
            .set('spark.hadoop.fs.s3a.impl', 'org.apache.hadoop.fs.s3a.S3AFileSystem')
            .set('spark.hadoop.fs.s3a.endpoint.region', AWS_REGION)
    )
    return SparkSession.builder.config(conf=conf).getOrCreate()

def run_gen():
    spark = get_spark_session()
    
    try:
        print("📖 Step 1: Extracting unique customer IDs from Bronze Orders...")
        # Get unique user_ids from orders_bronze (pointing to bronze branch)
        unique_users = spark.table("nessie.ecommerce.`orders_bronze@bronze`") \
            .select(F.col("user_id").alias("customer_id")) \
            .filter(F.col("customer_id").isNotNull()) \
            .distinct()
        
        count = unique_users.count()
        print(f"✓ Found {count:,} unique customers.")
        
        print("\n🔧 Step 2: Synthesizing Master Data...")
        # Generate names and emails based on customer_id
        # We use consistent hashing or simple string concat for deterministic results
        synthetic_customers = unique_users \
            .withColumn("name", F.concat(F.lit("Customer_"), F.col("customer_id"))) \
            .withColumn("email", F.concat(F.col("name"), F.lit("@example.com"))) \
            .withColumn("signup_date", F.to_date(F.lit("2019-01-01"))) \
            .withColumn("is_active", F.lit(True)) \
            .withColumn("data_quality_score", F.lit(100)) \
            .withColumn("processed_at", F.current_timestamp()) \
            .withColumn("source_branch", F.lit("synthetic_bronze_extract")) \
            .withColumn("email_valid", F.lit(True))
        
        print("\n💾 Step 3: Writing to customers_silver@silver...")
        spark.sql("CREATE NAMESPACE IF NOT EXISTS nessie.ecommerce")
        
        # Use simple createOrReplace for the small dimension table
        synthetic_customers.writeTo("nessie.ecommerce.`customers_silver@silver`") \
            .using("iceberg") \
            .createOrReplace()
        
        print(f"✅ Success! Generated {count:,} customer records in nessie.ecommerce.`customers_silver@silver`.")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        raise e
    finally:
        spark.stop()

if __name__ == "__main__":
    run_gen()
