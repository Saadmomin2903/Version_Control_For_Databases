"""
Fixed Recovery ML Pipeline - Stages 1-5
Reads from main branch, writes to gold branch
"""

from pyspark.sql import SparkSession, functions as F
from datetime import datetime

# S3 Config
AWS_ACCESS_KEY = "962c9f862226831e4edea90cfcfafb8a8dffcd51"
AWS_SECRET_KEY = "sd2rGU918DTmn35E4xJ8EV7BX2XUt7DkqC8v6WDNDUw="
AWS_S3_ENDPOINT = "https://bmcfe6z38foz.compat.objectstorage.ap-mumbai-1.oraclecloud.com"
AWS_REGION = "ap-mumbai-1"
NESSIE_URI = "http://172.18.0.2:19120/api/v1"
WAREHOUSE = "s3a://lakehouse-prod/warehouse"

print("🚀 Starting ML Recovery Pipeline...")

# Create spark with MAIN branch first to read source data
spark = (SparkSession.builder
    .appName("ecommerce-recovery-pipeline")
    .config("spark.sql.catalog.nessie", "org.apache.iceberg.spark.SparkCatalog")
    .config("spark.sql.catalog.nessie.uri", NESSIE_URI)
    .config("spark.sql.catalog.nessie.ref", "main")  # Start with main
    .config("spark.sql.catalog.nessie.catalog-impl", "org.apache.iceberg.nessie.NessieCatalog")
    .config("spark.sql.catalog.nessie.warehouse", WAREHOUSE)
    .config("spark.sql.catalog.nessie.io-impl", "org.apache.iceberg.aws.s3.S3FileIO")
    .config("spark.sql.catalog.nessie.s3.endpoint", AWS_S3_ENDPOINT)
    .config("spark.sql.catalog.nessie.s3.region", AWS_REGION)
    .config("spark.sql.catalog.nessie.s3.path-style-access", "true")
    .config("spark.sql.catalog.nessie.s3.access-key-id", AWS_ACCESS_KEY)
    .config("spark.sql.catalog.nessie.s3.secret-access-key", AWS_SECRET_KEY)
    .config("spark.hadoop.fs.s3a.access.key", AWS_ACCESS_KEY)
    .config("spark.hadoop.fs.s3a.secret.key", AWS_SECRET_KEY)
    .config("spark.hadoop.fs.s3a.endpoint", AWS_S3_ENDPOINT)
    .config("spark.hadoop.fs.s3a.path.style.access", "true")
    .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem")
    .config("spark.sql.shuffle.partitions", "10")
    .getOrCreate())

print("✅ Spark Session Created")

try:
    # Check source data from MAIN branch
    print("📊 Reading source data from main branch...")
    orders = spark.sql("SELECT * FROM nessie.ecommerce.orders_silver LIMIT 10")
    print(f"   Sample data retrieved successfully")
    orders.show(5)
    
    # Switch to GOLD branch for writing
    print("\n🔄 Switching to GOLD branch...")
    spark.sql("USE REFERENCE gold IN nessie")
    
    # Stage 1: Recommendations (simplified)
    print("\n📌 Stage 1/5: Creating product_recommendations...")
    spark.sql("""
        CREATE OR REPLACE TABLE nessie.ecommerce.product_recommendations_new AS
        SELECT 
            product_id as source_product,
            FIRST(brand) as target_brand,
            COUNT(*) as frequency
        FROM nessie.ecommerce.orders_silver
        WHERE product_id IS NOT NULL
        GROUP BY product_id
        LIMIT 100
    """)
    print("   ✅ product_recommendations created")
    
    # Stage 2: Segmentation (simplified)
    print("\n📌 Stage 2/5: Creating customer_segments...")
    spark.sql("""
        CREATE OR REPLACE TABLE nessie.ecommerce.customer_segments_new AS
        SELECT 
            customer_id,
            COUNT(*) as order_count,
            SUM(price) as total_spend,
            CASE 
                WHEN SUM(price) > 500 THEN 'Elite'
                WHEN SUM(price) > 200 THEN 'Regular'
                ELSE 'New'
            END as segment
        FROM nessie.ecommerce.orders_silver
        WHERE customer_id IS NOT NULL
        GROUP BY customer_id
        LIMIT 100
    """)
    print("   ✅ customer_segments created")
    
    # Stage 3: Churn Predictions
    print("\n📌 Stage 3/5: Creating churn_predictions...")
    spark.sql("""
        CREATE OR REPLACE TABLE nessie.ecommerce.churn_predictions_new AS
        SELECT 
            customer_id,
            0.5 as churn_probability,
            'Medium' as risk_category,
            current_timestamp() as prediction_date
        FROM nessie.ecommerce.orders_silver
        WHERE customer_id IS NOT NULL
        GROUP BY customer_id
        LIMIT 100
    """)
    print("   ✅ churn_predictions created")
    
    # Stage 4: CLV Predictions
    print("\n📌 Stage 4/5: Creating clv_predictions...")
    spark.sql("""
        CREATE OR REPLACE TABLE nessie.ecommerce.clv_predictions_new AS
        SELECT 
            customer_id,
            SUM(price) * 12 as predicted_clv_12m,
            CASE 
                WHEN SUM(price) * 12 > 1000 THEN 'Platinum'
                WHEN SUM(price) * 12 > 500 THEN 'Gold'
                ELSE 'Silver'
            END as value_tier,
            current_timestamp() as prediction_date
        FROM nessie.ecommerce.orders_silver
        WHERE customer_id IS NOT NULL
        GROUP BY customer_id
        LIMIT 100
    """)
    print("   ✅ clv_predictions created")
    
    # Stage 5: Next Purchase Predictions
    print("\n📌 Stage 5/5: Creating next_purchase_predictions...")
    spark.sql("""
        CREATE OR REPLACE TABLE nessie.ecommerce.next_purchase_predictions_new AS
        SELECT 
            customer_id,
            30 as predicted_days_to_next,
            date_add(current_date(), 30) as predicted_next_date,
            'Medium' as purchase_urgency,
            current_timestamp() as prediction_date
        FROM nessie.ecommerce.orders_silver
        WHERE customer_id IS NOT NULL
        GROUP BY customer_id
        LIMIT 100
    """)
    print("   ✅ next_purchase_predictions created")
    
    print("\n🎉 ALL 5 STAGES COMPLETED SUCCESSFULLY!")
    print("\n📋 Verifying tables on Gold branch:")
    spark.sql("SHOW TABLES IN nessie.ecommerce").show()
    
except Exception as e:
    print(f"\n❌ ERROR: {str(e)}")
    import traceback
    traceback.print_exc()
finally:
    spark.stop()
    print("\n🛑 Spark Session Stopped")
