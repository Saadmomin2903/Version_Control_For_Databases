"""
Gold Layer Factory - "The Aggregator"
Computes business-level aggregates from Silver data and stores them in the Gold layer.

Target Branch: gold
Source Table: nessie.ecommerce.orders_silver@main
"""

import os
import sys
import pyspark
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import DoubleType, LongType

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
            .setAppName('gold_layer_builder')
            # FIX 4: Use CLUSTER MODE to utilize VM2 Workers (Optimization)
            .set("spark.master", "spark://spark-master:7077")
            .set('spark.sql.shuffle.partitions', '200')  # Lower shuffle for aggregations
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
            .set('spark.sql.catalog.nessie.ref', 'gold') # Write to GOLD branch
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

def build_gold_layer():
    spark = get_spark_session()
    
    print("=" * 60)
    print("🏆 GOLD LAYER FACTORY: STARTING BUILD")
    print("=" * 60)

    # 1. Read Silver (Source of Truth)
    # Note: Reading from 'main' (Production Silver)
    print("\nPRODUCING FROM: nessie.ecommerce.orders_silver@main")
    silver_df = spark.sql("SELECT * FROM nessie.ecommerce.`orders_silver@main`")
    
    # ---------------------------------------------------------
    # GOLD TABLE 1: DAILY SALES
    # ---------------------------------------------------------
    print("\n[1/4] Building: daily_sales_gold")
    # Only COUNT purchases for revenue, but count ALL events for traffic
    daily_sales = silver_df.groupBy("order_date").agg(
        F.sum(F.when(F.col("event_type") == "purchase", F.col("price")).otherwise(0)).alias("total_revenue"),
        F.count(F.when(F.col("event_type") == "purchase", 1)).alias("total_orders"),
        F.countDistinct("customer_id").alias("unique_customers"),
        F.avg(F.when(F.col("event_type") == "purchase", F.col("price"))).alias("avg_order_value")
    ).orderBy("order_date")
    
    # Write
    print("   -> Writing to Iceberg (Partitioned by Year)...")
    # FIX: Sort by partition key to prevent "records violate writer assumption" error
    daily_sales.sortWithinPartitions("order_date").writeTo("nessie.ecommerce.daily_sales_gold").createOrReplace()
    print("   ✅ Done.")

    # ---------------------------------------------------------
    # GOLD TABLE 2: BRAND PERFORMANCE
    # ---------------------------------------------------------
    print("\n[2/4] Building: brand_performance_gold")
    brand_stats = silver_df.filter(F.col("brand").isNotNull()).groupBy("brand").agg(
        F.sum(F.when(F.col("event_type") == "purchase", F.col("price")).otherwise(0)).alias("total_revenue"),
        F.count(F.when(F.col("event_type") == "purchase", 1)).alias("total_orders"),
        F.countDistinct("customer_id").alias("unique_customers")
    )
    
    print("   -> Writing to Iceberg...")
    brand_stats.sortWithinPartitions("brand").writeTo("nessie.ecommerce.brand_performance_gold").createOrReplace()
    print("   ✅ Done.")

    # ---------------------------------------------------------
    # GOLD TABLE 3: CUSTOMER STATS (LTV)
    # ---------------------------------------------------------
    print("\n[3/4] Building: customer_stats_gold (Heavy Aggregation)")
    # Filter for known customers
    customer_df = silver_df.filter(F.col("customer_id").isNotNull())
    
    customer_stats = customer_df.groupBy("customer_id").agg(
        F.sum(F.when(F.col("event_type") == "purchase", F.col("price")).otherwise(0)).alias("total_spend"),
        F.count(F.when(F.col("event_type") == "purchase", 1)).alias("total_orders"),
        F.min("order_date").alias("first_order_date"),
        F.max("order_date").alias("last_order_date")
    )
    
    # Add Segmentation Logic (Business Rule)
    customer_stats = customer_stats.withColumn(
        "customer_segment",
        F.when(F.col("total_spend") > 2000, "VIP")
         .when(F.col("total_spend") > 500, "Regular")
         .otherwise("New")
    )

    print("   -> Writing to Iceberg (Bucketed by User)...")
    print("   -> Writing to Iceberg (Bucketed by User) - Using FANOUT Writer...")
    # FIX 3: THE NUCLEAR OPTION - Fanout Writer
    # The error happens because sorting isn't perfect across tasks. 
    # Fanout keeps files open (safe here because only 16 buckets).
    
    # 1. Create table with Fanout enabled
    spark.sql(f"""
        CREATE OR REPLACE TABLE nessie.ecommerce.customer_stats_gold (
            customer_id LONG,
            total_spend DOUBLE,
            total_orders LONG,
            first_order_date DATE,
            last_order_date DATE,
            customer_segment STRING
        )
        USING iceberg
        PARTITIONED BY (bucket(16, customer_id))
        TBLPROPERTIES ('write.spark.fanout.enabled'='true')
    """)
    
    # 2. Write data (Sorting is no longer required, but good practice)
    customer_stats.writeTo("nessie.ecommerce.customer_stats_gold").append()
    print("   ✅ Done.")

    # ---------------------------------------------------------
    # GOLD TABLE 4: CATEGORY ANALYTICS
    # ---------------------------------------------------------
    print("\n[4/4] Building: category_stats_gold")
    # Extract category level 1 (simplified)
    # Assuming code is likely "electronics.smartphone" -> "electronics"
    cat_df = silver_df.withColumn("category_main", F.split(F.col("category_code"), "\.")[0])
    
    cat_stats = cat_df.filter(F.col("category_main").isNotNull()).groupBy("category_main").agg(
        F.sum(F.when(F.col("event_type") == "purchase", F.col("price")).otherwise(0)).alias("total_revenue"),
        F.count("event_type").alias("total_events"),
        F.count(F.when(F.col("event_type") == "purchase", 1)).alias("total_sales")
    )

    print("   -> Writing to Iceberg...")
    cat_stats.writeTo("nessie.ecommerce.category_stats_gold").createOrReplace()
    print("   ✅ Done.")

    print("\n" + "=" * 60)
    print("✨ GOLD LAYER BUILD COMPLETE")
    print("=" * 60)
    spark.stop()

if __name__ == "__main__":
    build_gold_layer()
