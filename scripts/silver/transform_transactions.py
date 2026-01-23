import os
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, to_date, min, max, count, row_number, desc
from pyspark.sql.window import Window

def get_spark_session(app_name):
    """
    Creates a Spark session configured for Nessie & Iceberg.
    """
    return SparkSession.builder \
        .appName(app_name) \
        .config("spark.sql.catalog.nessie", "org.apache.iceberg.spark.SparkCatalog") \
        .config("spark.sql.catalog.nessie.uri", os.getenv("NESSIE_URI", "http://140.238.224.207:19120/api/v1")) \
        .config("spark.sql.catalog.nessie.ref", "dev-silver") \
        .config("spark.sql.catalog.nessie.authentication.type", "NONE") \
        .config("spark.sql.catalog.nessie.catalog-impl", "org.apache.iceberg.nessie.NessieCatalog") \
        .config("spark.sql.catalog.nessie.warehouse", os.getenv("WAREHOUSE", "s3a://lakehouse/warehouse")) \
        .getOrCreate()

def transform_silver(spark, input_table, output_namespace):
    print(f"--- STARTING SILVER TRANSFORMATION (SMART AUDIT) ---")
    
    # 1. READ BRONZE
    # We read from main branch (Production Bronze)
    print("Reading from Bronze (main)...")
    bronze_df = spark.sql(f"SELECT * FROM nessie.{input_table}@main")
    
    # AUDIT: Initial Count
    total_rows = bronze_df.count()
    print(f"Input Row Count: {total_rows}")

    # 2. CLEANING & DEDUPLICATION
    # Cast types
    clean_df = bronze_df.select(
        col("event_time").cast("timestamp").alias("event_time"),
        col("event_type"),
        col("product_id").cast("long"),
        col("category_id").cast("long"),
        col("category_code"),
        col("brand"),
        col("price").cast("double"),
        col("user_id").cast("long"),
        col("user_session")
    ).withColumn("event_date", to_date("event_time"))

    # Sanity Check: Filter negative prices
    clean_df = clean_df.filter(col("price") >= 0)

    # CRITICAL: Hard Deduplication
    clean_df = clean_df.dropDuplicates(["user_id", "product_id", "event_time", "event_type"])
    
    # AUDIT: Final Count
    final_rows = clean_df.count()
    dropped_rows = total_rows - final_rows
    print(f"Cleaning Complete.")
    print(f"QUALITY REPORT:")
    print(f"   - Input:   {total_rows}")
    print(f"   - Output:  {final_rows}")
    print(f"   - Dropped: {dropped_rows} rows (Duplicates/Invalid)")

    # 3. WRITE SILVER TRANSACTIONS (Fact Table)
    print("Writing Silver Transactions...")
    silver_transactions = clean_df.select(
        "event_time", "event_date", "event_type",
        "product_id", "user_id", "price", "user_session"
    )
    
    silver_transactions.writeTo(f"nessie.{output_namespace}.silver_transactions") \
        .using("iceberg") \
        .partitionedBy("event_date") \
        .createOrReplace()

    # 4. WRITE SILVER DIMENSIONS (Users & Products)
    print("Building User Dimension...")
    silver_users = clean_df.groupBy("user_id").agg(
        min("event_time").alias("first_seen"),
        max("event_time").alias("last_seen"),
        count("event_type").alias("activity_count")
    )
    
    silver_users.writeTo(f"nessie.{output_namespace}.silver_users") \
        .using("iceberg") \
        .createOrReplace()

    print("Building Product Dimension...")
    product_window = Window.partitionBy("product_id").orderBy(col("event_time").desc())
    
    silver_products = clean_df.withColumn("rank", row_number().over(product_window)) \
        .filter(col("rank") == 1) \
        .select("product_id", "category_code", "brand", "price")

    silver_products.writeTo(f"nessie.{output_namespace}.silver_products") \
        .using("iceberg") \
        .createOrReplace()
        
    print(f"SUCCESS: All 3 Silver Tables Created in 'dev-silver' branch!")

if __name__ == "__main__":
    spark = get_spark_session("SilverTransform")
    transform_silver(spark, "ecommerce.transactions_bronze", "ecommerce")