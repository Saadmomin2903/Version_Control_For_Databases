"""
Debug ML Pipeline - Testing Nessie/Iceberg Connection
"""

from pyspark.sql import SparkSession

# S3 Config
AWS_ACCESS_KEY = "962c9f862226831e4edea90cfcfafb8a8dffcd51"
AWS_SECRET_KEY = "sd2rGU918DTmn35E4xJ8EV7BX2XUt7DkqC8v6WDNDUw="
AWS_S3_ENDPOINT = "https://bmcfe6z38foz.compat.objectstorage.ap-mumbai-1.oraclecloud.com"
AWS_REGION = "ap-mumbai-1"
NESSIE_URI = "http://172.18.0.2:19120/api/v1"
WAREHOUSE = "s3a://lakehouse-prod/warehouse"

print("🔍 DEBUG: Testing Spark-Nessie Connection...")

spark = (SparkSession.builder
    .appName("debug-nessie")
    .config("spark.sql.catalog.nessie", "org.apache.iceberg.spark.SparkCatalog")
    .config("spark.sql.catalog.nessie.uri", NESSIE_URI)
    .config("spark.sql.catalog.nessie.ref", "main")
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
    .getOrCreate())

print("✅ Spark Session Created")

try:
    print("\n📋 Step 1: Show catalogs...")
    spark.sql("SHOW CATALOGS").show()
    
    print("\n📋 Step 2: Show namespaces in nessie...")
    spark.sql("SHOW NAMESPACES IN nessie").show()
    
    print("\n📋 Step 3: Show tables in nessie.ecommerce...")
    spark.sql("SHOW TABLES IN nessie.ecommerce").show()
    
    print("\n📋 Step 4: Read orders_silver...")
    df = spark.table("nessie.ecommerce.orders_silver")
    print(f"   Row count: {df.count()}")
    df.show(5)
    
except Exception as e:
    print(f"\n❌ ERROR: {str(e)}")
    import traceback
    traceback.print_exc()
finally:
    spark.stop()
    print("\n🛑 Done")
