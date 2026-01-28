
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, to_date
import os

def run_silver_demo():
    # Configuration
    NESSIE_URI = os.getenv("NESSIE_URI", "http://nessie:19120/api/v1")
    WAREHOUSE = os.getenv("WAREHOUSE", "s3a://lakehouse-prod/warehouse")
    AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY", "962c9f862226831e4edea90cfcfafb8a8dffcd51")
    AWS_SECRET_KEY = os.getenv("AWS_SECRET_KEY", "sd2rGU918DTmn35E4xJ8EV7BX2XUt7DkqC8v6WDNDUw=")
    AWS_S3_ENDPOINT = os.getenv("AWS_S3_ENDPOINT", "https://bmcfe6z38foz.compat.objectstorage.ap-mumbai-1.oraclecloud.com")
    
    spark = SparkSession.builder \
        .appName("Silver-Orders-Demo") \
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

    print("🥈 Starting Silver Transformation Demo...")
    
    # Read from Bronze Demo table
    df = spark.read.table("nessie.ecommerce.orders_bronze_demo")
    
    # Simple cleaning (Corrected customer_id to user_id)
    df_clean = df.withColumn("order_date", to_date(col("event_time"))) \
                 .filter(col("user_id").isNotNull()) \
                 .dropDuplicates()
    
    print(f"✅ Transformed {df_clean.count()} rows. Writing to nessie.ecommerce.orders_silver_demo...")
    
    df_clean.writeTo("nessie.ecommerce.orders_silver_demo").createOrReplace()
    
    print("✨ Silver Demo Complete.")
    spark.stop()

if __name__ == "__main__":
    run_silver_demo()
