"""
ML Pipeline - Create Demo Tables
Creates Gold/Platinum layer tables with sample data
Fixed AWS region configuration for S3FileIO
"""

from pyspark.sql import SparkSession
from pyspark.sql.types import StructType, StructField, StringType, DoubleType, IntegerType

# S3 Config
AWS_ACCESS_KEY = "962c9f862226831e4edea90cfcfafb8a8dffcd51"
AWS_SECRET_KEY = "sd2rGU918DTmn35E4xJ8EV7BX2XUt7DkqC8v6WDNDUw="
AWS_S3_ENDPOINT = "https://bmcfe6z38foz.compat.objectstorage.ap-mumbai-1.oraclecloud.com"
AWS_REGION = "ap-mumbai-1"
NESSIE_URI = "http://172.18.0.2:19120/api/v1"
WAREHOUSE = "s3a://lakehouse-prod/warehouse"

print("🚀 Starting ML Pipeline - Creating Demo Tables...")

spark = (SparkSession.builder
    .appName("ml-demo-tables")
    .config("spark.sql.catalog.nessie", "org.apache.iceberg.spark.SparkCatalog")
    .config("spark.sql.catalog.nessie.uri", NESSIE_URI)
    .config("spark.sql.catalog.nessie.ref", "gold")
    .config("spark.sql.catalog.nessie.catalog-impl", "org.apache.iceberg.nessie.NessieCatalog")
    .config("spark.sql.catalog.nessie.warehouse", WAREHOUSE)
    # S3FileIO config with region
    .config("spark.sql.catalog.nessie.io-impl", "org.apache.iceberg.aws.s3.S3FileIO")
    .config("spark.sql.catalog.nessie.s3.endpoint", AWS_S3_ENDPOINT)
    .config("spark.sql.catalog.nessie.s3.region", AWS_REGION)
    .config("spark.sql.catalog.nessie.s3.path-style-access", "true")
    .config("spark.sql.catalog.nessie.s3.access-key-id", AWS_ACCESS_KEY)
    .config("spark.sql.catalog.nessie.s3.secret-access-key", AWS_SECRET_KEY)
    # AWS SDK client config 
    .config("spark.sql.catalog.nessie.client.region", AWS_REGION)
    .config("spark.sql.catalog.nessie.s3.client.region", AWS_REGION)
    # Hadoop S3A config
    .config("spark.hadoop.fs.s3a.access.key", AWS_ACCESS_KEY)
    .config("spark.hadoop.fs.s3a.secret.key", AWS_SECRET_KEY)
    .config("spark.hadoop.fs.s3a.endpoint", AWS_S3_ENDPOINT)
    .config("spark.hadoop.fs.s3a.path.style.access", "true")
    .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem")
    # AWS environment variables workaround
    .config("spark.executorEnv.AWS_REGION", AWS_REGION)
    .config("spark.driverEnv.AWS_REGION", AWS_REGION)
    .getOrCreate())

print("✅ Spark Session Created")

try:
    # Stage 1: Product Recommendations
    print("\n📌 Stage 1/5: Creating product_recommendations_demo...")
    rec_data = [
        ("P001", "P002", 0.85, "electronics"),
        ("P001", "P003", 0.72, "electronics"),
        ("P002", "P001", 0.85, "electronics"),
        ("P003", "P004", 0.68, "appliances"),
        ("P004", "P005", 0.91, "appliances"),
    ]
    rec_schema = StructType([
        StructField("source_product", StringType(), False),
        StructField("recommended_product", StringType(), False),
        StructField("confidence", DoubleType(), False),
        StructField("category", StringType(), True),
    ])
    rec_df = spark.createDataFrame(rec_data, rec_schema)
    rec_df.writeTo("nessie.ecommerce.product_recommendations_demo").createOrReplace()
    print("   ✅ product_recommendations_demo created (5 rows)")

    # Stage 2: Customer Segments
    print("\n📌 Stage 2/5: Creating customer_segments_demo...")
    seg_data = [
        ("C001", 15, 2500.0, "Elite"),
        ("C002", 8, 850.0, "Regular"),
        ("C003", 3, 150.0, "New"),
        ("C004", 22, 4200.0, "Elite"),
        ("C005", 5, 320.0, "Regular"),
    ]
    seg_schema = StructType([
        StructField("customer_id", StringType(), False),
        StructField("order_count", IntegerType(), False),
        StructField("total_spend", DoubleType(), False),
        StructField("segment", StringType(), False),
    ])
    seg_df = spark.createDataFrame(seg_data, seg_schema)
    seg_df.writeTo("nessie.ecommerce.customer_segments_demo").createOrReplace()
    print("   ✅ customer_segments_demo created (5 rows)")

    # Stage 3: Churn Predictions (Platinum)
    print("\n📌 Stage 3/5: Creating churn_predictions_demo...")
    churn_data = [
        ("C001", 0.12, "Low"),
        ("C002", 0.45, "Medium"),
        ("C003", 0.78, "High"),
        ("C004", 0.08, "Low"),
        ("C005", 0.55, "Medium"),
    ]
    churn_schema = StructType([
        StructField("customer_id", StringType(), False),
        StructField("churn_probability", DoubleType(), False),
        StructField("risk_category", StringType(), False),
    ])
    churn_df = spark.createDataFrame(churn_data, churn_schema)
    churn_df.writeTo("nessie.ecommerce.churn_predictions_demo").createOrReplace()
    print("   ✅ churn_predictions_demo created (5 rows)")

    # Stage 4: CLV Predictions (Platinum)
    print("\n📌 Stage 4/5: Creating clv_predictions_demo...")
    clv_data = [
        ("C001", 15000.0, "Platinum"),
        ("C002", 5200.0, "Gold"),
        ("C003", 900.0, "Silver"),
        ("C004", 25000.0, "Platinum"),
        ("C005", 2100.0, "Silver"),
    ]
    clv_schema = StructType([
        StructField("customer_id", StringType(), False),
        StructField("predicted_clv_12m", DoubleType(), False),
        StructField("value_tier", StringType(), False),
    ])
    clv_df = spark.createDataFrame(clv_data, clv_schema)
    clv_df.writeTo("nessie.ecommerce.clv_predictions_demo").createOrReplace()
    print("   ✅ clv_predictions_demo created (5 rows)")

    # Stage 5: Next Purchase Predictions (Platinum)
    print("\n📌 Stage 5/5: Creating next_purchase_predictions_demo...")
    npp_data = [
        ("C001", 7, "2026-02-04", "High"),
        ("C002", 21, "2026-02-18", "Medium"),
        ("C003", 45, "2026-03-14", "Low"),
        ("C004", 5, "2026-02-02", "High"),
        ("C005", 30, "2026-02-27", "Medium"),
    ]
    npp_schema = StructType([
        StructField("customer_id", StringType(), False),
        StructField("predicted_days_to_next", IntegerType(), False),
        StructField("predicted_next_date", StringType(), False),
        StructField("purchase_urgency", StringType(), False),
    ])
    npp_df = spark.createDataFrame(npp_data, npp_schema)
    npp_df.writeTo("nessie.ecommerce.next_purchase_predictions_demo").createOrReplace()
    print("   ✅ next_purchase_predictions_demo created (5 rows)")

    print("\n🎉 ALL 5 STAGES COMPLETED SUCCESSFULLY!")
    print("\n📋 Verifying tables on Gold branch:")
    spark.sql("SHOW TABLES IN nessie.ecommerce").show(20, False)
    
except Exception as e:
    print(f"\n❌ ERROR: {str(e)}")
    import traceback
    traceback.print_exc()
finally:
    spark.stop()
    print("\n🛑 Spark Session Stopped")
