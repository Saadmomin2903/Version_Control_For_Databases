
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, when, rand
import os

def run_platinum_demo():
    # Configuration
    NESSIE_URI = os.getenv("NESSIE_URI", "http://nessie:19120/api/v1")
    WAREHOUSE = os.getenv("WAREHOUSE", "s3a://lakehouse-prod/warehouse")
    AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY", "962c9f862226831e4edea90cfcfafb8a8dffcd51")
    AWS_SECRET_KEY = os.getenv("AWS_SECRET_KEY", "sd2rGU918DTmn35E4xJ8EV7BX2XUt7DkqC8v6WDNDUw=")
    AWS_S3_ENDPOINT = os.getenv("AWS_S3_ENDPOINT", "https://bmcfe6z38foz.compat.objectstorage.ap-mumbai-1.oraclecloud.com")

    spark = SparkSession.builder \
        .appName("Platinum-ML-Demo") \
        .master("local[*]") \
        .config("spark.jars.packages", "org.apache.iceberg:iceberg-spark-runtime-3.3_2.12:1.3.1,org.projectnessie.nessie-integrations:nessie-spark-extensions-3.3_2.12:0.67.0,org.apache.hadoop:hadoop-aws:3.3.1") \
        .config("spark.sql.extensions", "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions,org.projectnessie.spark.extensions.NessieSparkSessionExtensions") \
        .config("spark.sql.catalog.nessie", "org.apache.iceberg.spark.SparkCatalog") \
        .config("spark.sql.catalog.nessie.uri", NESSIE_URI) \
        .config("spark.sql.catalog.nessie.ref", "main") \
        .config("spark.sql.catalog.nessie.catalog-impl", "org.apache.iceberg.nessie.NessieCatalog") \
        .config("spark.sql.catalog.nessie.warehouse", WAREHOUSE) \
        .config("spark.sql.catalog.nessie.io-impl", "org.apache.iceberg.hadoop.HadoopFileIO") \
        .config("spark.hadoop.fs.s3a.access.key", AWS_ACCESS_KEY) \
        .config("spark.hadoop.fs.s3a.secret.key", AWS_SECRET_KEY) \
        .config("spark.hadoop.fs.s3a.endpoint", AWS_S3_ENDPOINT) \
        .config("spark.hadoop.fs.s3a.path.style.access", "true") \
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
        .getOrCreate()

    print("💎 Starting Platinum ML Insights Demo...")
    
    # Read from Gold Demo
    df = spark.read.table("nessie.ecommerce.daily_sales_demo")
    
    # Simulate ML results (Segmentation based on revenue)
    platinum_df = df.withColumn("segment", 
        when(col("total_revenue") > 100, "High Value")
        .when(col("total_revenue") > 50, "Promising")
        .otherwise("Standard")
    ).withColumn("churn_probability", rand())
    
    print("✅ Generated ML insights. Writing to nessie.ecommerce.ml_insights_demo...")
    
    platinum_df.writeTo("nessie.ecommerce.ml_insights_demo").createOrReplace()
    
    print("✨ Platinum Demo Complete.")
    spark.stop()

if __name__ == "__main__":
    run_platinum_demo()
