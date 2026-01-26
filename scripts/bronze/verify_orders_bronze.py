
import os
import pyspark
from pyspark.sql import SparkSession

def create_spark_session():
    # Set AWS Region globally via Env Vars (Required for AWS SDK v2)
    os.environ['AWS_REGION'] = 'ap-mumbai-1'
    os.environ['AWS_DEFAULT_REGION'] = 'ap-mumbai-1'
    
    # Production S3/Iceberg/Nessie config for Oracle Object Storage
    return SparkSession.builder \
        .appName("Verify_Bronze_Orders") \
        .config("spark.jars.packages", "org.apache.iceberg:iceberg-spark-runtime-3.3_2.12:1.3.1,org.projectnessie.nessie-integrations:nessie-spark-extensions-3.3_2.12:0.67.0,software.amazon.awssdk:bundle:2.17.178,org.apache.hadoop:hadoop-aws:3.3.1") \
        .config("spark.sql.extensions", "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions,org.projectnessie.spark.extensions.NessieSparkSessionExtensions") \
        .config("spark.sql.catalog.nessie", "org.apache.iceberg.spark.SparkCatalog") \
        .config("spark.sql.catalog.nessie.uri", "http://172.18.0.2:19120/api/v1") \
        .config("spark.sql.catalog.nessie.ref", "bronze") \
        .config("spark.sql.catalog.nessie.authentication.type", "NONE") \
        .config("spark.sql.catalog.nessie.catalog-impl", "org.apache.iceberg.nessie.NessieCatalog") \
        .config("spark.sql.catalog.nessie.warehouse", "s3a://lakehouse-prod/warehouse") \
        .config("spark.sql.catalog.nessie.io-impl", "org.apache.iceberg.aws.s3.S3FileIO") \
        .config("spark.sql.catalog.nessie.s3.endpoint", "https://bmcfe6z38foz.compat.objectstorage.ap-mumbai-1.oraclecloud.com") \
        .config("spark.sql.catalog.nessie.s3.path-style-access", "true") \
        .config("spark.sql.catalog.nessie.s3.region", "ap-mumbai-1") \
        .config("spark.sql.catalog.nessie.client.region", "ap-mumbai-1") \
        .config("spark.hadoop.fs.s3a.endpoint", "https://bmcfe6z38foz.compat.objectstorage.ap-mumbai-1.oraclecloud.com") \
        .config("spark.hadoop.fs.s3a.access.key", "962c9f862226831e4edea90cfcfafb8a8dffcd51") \
        .config("spark.hadoop.fs.s3a.secret.key", "sd2rGU918DTmn35E4xJ8EV7BX2XUt7DkqC8v6WDNDUw=") \
        .config("spark.hadoop.fs.s3a.path.style.access", "true") \
        .config("spark.hadoop.fs.s3a.endpoint.region", "ap-mumbai-1") \
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
        .getOrCreate()

def verify_table(spark):
    table_name = "nessie.ecommerce.orders_bronze"
    print(f"🔍 Verifying table: {table_name}")
    
    # Check if table exists
    try:
        tables = spark.sql("SHOW TABLES IN nessie.ecommerce").collect()
        exists = any(row.tableName == 'orders_bronze' for row in tables)
        if not exists:
            print(f"❌ Table {table_name} NOT found in catalog!")
            return
        print(f"✅ Table {table_name} found in catalog.")
    except Exception as e:
        print(f"❌ Error listing tables: {e}")
        return

    # Count rows
    print("⏳ Counting rows (this might take a moment)...")
    try:
        count = spark.sql(f"SELECT COUNT(*) as cnt FROM {table_name}").collect()[0]['cnt']
        print(f"✅ Total Row Count: {count:,}")
    except Exception as e:
        print(f"❌ Error counting rows: {e}")

    # Show sample
    print("👀 Sample Data (Top 5):")
    try:
        spark.sql(f"SELECT * FROM {table_name} LIMIT 5").show(truncate=False)
    except Exception as e:
        print(f"❌ Error fetching sample: {e}")

if __name__ == "__main__":
    spark = create_spark_session()
    verify_table(spark)
    spark.stop()
