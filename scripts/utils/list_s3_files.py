
from pyspark.sql import SparkSession
import os

def list_s3_files():
    # Credentials from ingest_orders_spark.py
    os.environ['AWS_REGION'] = 'ap-mumbai-1'
    os.environ['AWS_DEFAULT_REGION'] = 'ap-mumbai-1'
    
    spark = SparkSession.builder \
        .appName("List_S3_Files") \
        .master("local[*]") \
        .config("spark.jars.packages", "org.apache.iceberg:iceberg-spark-runtime-3.3_2.12:1.3.1,org.projectnessie.nessie-integrations:nessie-spark-extensions-3.3_2.12:0.67.0,software.amazon.awssdk:bundle:2.17.178,org.apache.hadoop:hadoop-aws:3.3.1") \
        .config("spark.hadoop.fs.s3a.endpoint", "https://bmcfe6z38foz.compat.objectstorage.ap-mumbai-1.oraclecloud.com") \
        .config("spark.hadoop.fs.s3a.access.key", "962c9f862226831e4edea90cfcfafb8a8dffcd51") \
        .config("spark.hadoop.fs.s3a.secret.key", "sd2rGU918DTmn35E4xJ8EV7BX2XUt7DkqC8v6WDNDUw=") \
        .config("spark.hadoop.fs.s3a.path.style.access", "true") \
        .config("spark.hadoop.fs.s3a.endpoint.region", "ap-mumbai-1") \
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
        .config("spark.hadoop.fs.s3a.connection.ssl.enabled", "true") \
        .getOrCreate()

    path = "s3a://lakehouse-prod/bronze/ecommerce/"
    print(f"Listing files in: {path}")
    
    # Use Hadoop FileSystem API
    fs = spark._jvm.org.apache.hadoop.fs.FileSystem.get(spark._jsc.hadoopConfiguration())
    path_obj = spark._jvm.org.apache.hadoop.fs.Path(path)
    
    try:
        status = fs.listStatus(path_obj)
        print(f"Found {len(status)} files:")
        for file_status in status:
            print(f" - {file_status.getPath().getName()} ({file_status.getLen()} bytes)")
    except Exception as e:
        print(f"Error listing files: {e}")

    spark.stop()

if __name__ == "__main__":
    list_s3_files()
