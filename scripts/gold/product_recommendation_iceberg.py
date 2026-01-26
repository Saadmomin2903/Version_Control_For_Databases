"""
Product Recommendation Engine
------------------------------
Uses Spark MLlib FPGrowth algorithm to generate product association rules.
Reads from: nessie.ecommerce.orders_silver@main
Writes to: nessie.ecommerce.product_recommendations@gold
"""

import os
import pyspark
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, collect_set, size, explode, array, struct
from pyspark.ml.fpm import FPGrowth

# Configuration
NESSIE_URI = os.getenv("NESSIE_URI", "http://nessie:19120/api/v1")
WAREHOUSE = os.getenv("WAREHOUSE", "s3a://lakehouse-prod/warehouse")
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY", "962c9f862226831e4edea90cfcfafb8a8dffcd51")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_KEY", "sd2rGU918DTmn35E4xJ8EV7BX2XUt7DkqC8v6WDNDUw=")
AWS_S3_ENDPOINT = os.getenv("AWS_S3_ENDPOINT", "https://bmcfe6z38foz.compat.objectstorage.ap-mumbai-1.oraclecloud.com")

def get_spark_session():
    """Initialize Spark with Nessie + Iceberg + S3 configuration"""
    conf = (
        pyspark.SparkConf()
        .setAppName('ml-product-recommendations')
        .set('spark.jars.packages',
             'org.apache.iceberg:iceberg-spark-runtime-3.3_2.12:1.3.1,'
             'org.projectnessie.nessie-integrations:nessie-spark-extensions-3.3_2.12:0.67.0,'
             'org.apache.hadoop:hadoop-aws:3.3.1')
        .set('spark.sql.extensions',
             'org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions,'
             'org.projectnessie.spark.extensions.NessieSparkSessionExtensions')
        .set('spark.sql.catalog.nessie', 'org.apache.iceberg.spark.SparkCatalog')
        .set('spark.sql.catalog.nessie.uri', NESSIE_URI)
        .set('spark.sql.catalog.nessie.ref', 'gold')
        .set('spark.sql.catalog.nessie.catalog-impl', 'org.apache.iceberg.nessie.NessieCatalog')
        .set('spark.sql.catalog.nessie.warehouse', WAREHOUSE)
        .set('spark.sql.catalog.nessie.io-impl', 'org.apache.iceberg.hadoop.HadoopFileIO')
        .set('spark.hadoop.fs.s3a.access.key', AWS_ACCESS_KEY)
        .set('spark.hadoop.fs.s3a.secret.key', AWS_SECRET_KEY)
        .set('spark.hadoop.fs.s3a.endpoint', AWS_S3_ENDPOINT)
        .set('spark.hadoop.fs.s3a.path.style.access', 'true')
        .set('spark.hadoop.fs.s3a.connection.ssl.enabled', 'true')
    )
    return SparkSession.builder.config(conf=conf).getOrCreate()

def run_product_recommendation():
    """Generate product recommendations using FPGrowth"""
    spark = get_spark_session()
    spark.sparkContext.setLogLevel("WARN")
    
    try:
        print("📊 Loading transaction data from Silver layer...")
        # Read from production Silver table
        transactions_df = spark.sql("""
            SELECT user_session, product_id, event_type
            FROM nessie.ecommerce.`orders_silver@main`
            WHERE event_type = 'purchase'
            AND user_session IS NOT NULL
            AND product_id IS NOT NULL
        """)
        
        print("🛒 Grouping transactions by session...")
        baskets = transactions_df.groupBy("user_session").agg(
            collect_set("product_id").alias("items")
        )
        
        # Filter baskets with at least 1 item
        baskets = baskets.filter(size(col("items")) > 0)
        basket_count = baskets.count()
        print(f"✅ Total Baskets: {basket_count}")
        
        # Hyperparameter sweep
        min_supports = [0.001, 0.005, 0.01]
        min_confidences = [0.1, 0.3, 0.5]
        
        best_model = None
        best_params = {}
        best_num_rules = -1
        
        print("\n🔍 Starting Hyperparameter Sweep...")
        
        for min_sup in min_supports:
            for min_conf in min_confidences:
                print(f"\n  Training with minSupport={min_sup}, minConfidence={min_conf}...")
                fp_growth = FPGrowth(
                    itemsCol="items",
                    minSupport=min_sup,
                    minConfidence=min_conf
                )
                model = fp_growth.fit(baskets)
                
                num_rules = model.associationRules.count()
                print(f"  Generated {num_rules} rules.")
                
                if num_rules > best_num_rules:
                    best_num_rules = num_rules
                    best_model = model
                    best_params = {'minSupport': min_sup, 'minConfidence': min_conf}
        
        if best_model is None:
            print("❌ No valid rules found with any parameter combination.")
            return
        
        print(f"\n🎯 Best Parameters: {best_params} with {best_num_rules} rules")
        
        # Display top rules
        print("\n📋 Top 10 Association Rules (sorted by lift):")
        best_model.associationRules.sort(col("lift").desc()).show(10, truncate=False)
        
        # Prepare rules for Iceberg (convert arrays to strings for compatibility)
        rules_df = best_model.associationRules
        rules_df = rules_df.withColumn("antecedent_str", col("antecedent").cast("string"))
        rules_df = rules_df.withColumn("consequent_str", col("consequent").cast("string"))
        rules_df = rules_df.select(
            "antecedent_str",
            "consequent_str", 
            "confidence",
            "lift",
            col("support").alias("rule_support")
        )
        
        # Write to Gold layer as Iceberg table
        print("\n💾 Writing recommendations to Gold layer...")
        rules_df.writeTo("nessie.ecommerce.product_recommendations").createOrReplace()
        
        print(f"✅ Saved {best_num_rules} association rules to nessie.ecommerce.product_recommendations@gold")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        raise
    finally:
        spark.stop()

if __name__ == "__main__":
    run_product_recommendation()
