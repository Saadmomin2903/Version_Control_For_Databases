
import pyspark
from pyspark.sql import SparkSession
import os

# Configuration (Same as others)
NESSIE_URI = os.getenv("NESSIE_URI", "http://172.18.0.2:19120/api/v1")
WAREHOUSE = "s3a://lakehouse-prod/warehouse"
AWS_S3_ENDPOINT = "https://bmcfe6z38foz.compat.objectstorage.ap-mumbai-1.oraclecloud.com"

conf = (
    pyspark.SparkConf()
    .setAppName('merge-gold-to-main')
    .set('spark.jars.packages', 'org.apache.iceberg:iceberg-spark-runtime-3.3_2.12:1.3.1,org.projectnessie.nessie-integrations:nessie-spark-extensions-3.3_2.12:0.67.0,software.amazon.awssdk:bundle:2.17.178,software.amazon.awssdk:url-connection-client:2.17.178')
    .set('spark.sql.extensions', 'org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions,org.projectnessie.spark.extensions.NessieSparkSessionExtensions')
    .set('spark.sql.catalog.nessie', 'org.apache.iceberg.spark.SparkCatalog')
    .set('spark.sql.catalog.nessie.uri', NESSIE_URI)
    .set('spark.sql.catalog.nessie.ref', 'main')
    .set('spark.sql.catalog.nessie.authentication.type', 'NONE')
    .set('spark.sql.catalog.nessie.catalog-impl', 'org.apache.iceberg.nessie.NessieCatalog')
    .set('spark.sql.catalog.nessie.warehouse', WAREHOUSE)
    .set('spark.sql.catalog.nessie.io-impl', 'org.apache.iceberg.aws.s3.S3FileIO')
    .set('spark.hadoop.fs.s3a.access.key', "962c9f862226831e4edea90cfcfafb8a8dffcd51") # Oracle Key
    .set('spark.hadoop.fs.s3a.secret.key', "sd2rGU918DTmn35E4xJ8EV7BX2XUt7DkqC8v6WDNDUw=") # Oracle Secret
    .set('spark.hadoop.fs.s3a.endpoint', AWS_S3_ENDPOINT)
    .set('spark.hadoop.fs.s3a.path.style.access', 'true')
    .set('spark.hadoop.fs.s3a.connection.ssl.enabled', 'true')
    .set('spark.hadoop.fs.s3a.impl', 'org.apache.hadoop.fs.s3a.S3AFileSystem')
)

spark = SparkSession.builder.config(conf=conf).getOrCreate()

print("🔀 Merging 'gold' branch into 'main'...")
try:
    spark.sql("MERGE BRANCH gold INTO main IN nessie")
    print("✅ Merge Successful: Gold tables are now available on Main.")
except Exception as e:
    print(f"❌ Merge Failed: {e}")
    # It might fail if no changes, which is fine
    pass

spark.stop()
