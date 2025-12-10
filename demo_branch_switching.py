"""
Nessie Branch Switching Demonstration

This script demonstrates Git-like branch operations with Nessie + Iceberg:
1. Create branches (bronze, silver)
2. Switch between branches
3. Write data to different branches
4. Query data from specific branches  
5. Show branch isolation

This is the CORE concept of your project!
"""

import pyspark
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
import os

# Configuration
NESSIE_URI = os.getenv("NESSIE_URI", "http://nessie:19120/api/v1")
WAREHOUSE = os.getenv("WAREHOUSE", "s3a://lakehouse/warehouse")
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID", "admin")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "password123")
AWS_S3_ENDPOINT = os.getenv("AWS_S3_ENDPOINT", "http://minio:9000")

print("=" * 70)
print("NESSIE BRANCH SWITCHING DEMONSTRATION")
print("Git-like Version Control for Data")
print("=" * 70)
print("")

# Spark configuration
conf = (
    pyspark.SparkConf()
        .setAppName('nessie-branch-demo')
        .set('spark.jars.packages', 
             'org.apache.iceberg:iceberg-spark-runtime-3.3_2.12:1.3.1,'
             'org.projectnessie.nessie-integrations:nessie-spark-extensions-3.3_2.12:0.67.0,'
             'software.amazon.awssdk:bundle:2.17.178,'
             'software.amazon.awssdk:url-connection-client:2.17.178')
        .set('spark.sql.extensions', 
             'org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions,'
             'org.projectnessie.spark.extensions.NessieSparkSessionExtensions')
        .set('spark.sql.catalog.nessie', 'org.apache.iceberg.spark.SparkCatalog')
        .set('spark.sql.catalog.nessie.uri', NESSIE_URI)
        .set('spark.sql.catalog.nessie.ref', 'main')  # Start on main
        .set('spark.sql.catalog.nessie.authentication.type', 'NONE')
        .set('spark.sql.catalog.nessie.catalog-impl', 'org.apache.iceberg.nessie.NessieCatalog')
        .set('spark.sql.catalog.nessie.warehouse', WAREHOUSE)
        .set('spark.sql.catalog.nessie.io-impl', 'org.apache.iceberg.aws.s3.S3FileIO')
        .set('spark.sql.catalog.nessie.s3.endpoint', AWS_S3_ENDPOINT)
        .set('spark.hadoop.fs.s3a.access.key', AWS_ACCESS_KEY)
        .set('spark.hadoop.fs.s3a.secret.key', AWS_SECRET_KEY)
        .set('spark.hadoop.fs.s3a.endpoint', AWS_S3_ENDPOINT)
        .set('spark.hadoop.fs.s3a.path.style.access', 'true')
        .set('spark.hadoop.fs.s3a.connection.ssl.enabled', 'false')
        .set('spark.hadoop.fs.s3a.impl', 'org.apache.hadoop.fs.s3a.S3AFileSystem')
)

spark = SparkSession.builder.config(conf=conf).getOrCreate()

# Demo Step 1: List available branches
print("Step 1: Listing available branches")
print("-" * 70)
spark.sql("LIST REFERENCES IN nessie").show()

# Demo Step 2: Create demo branches if they don't exist
print("\nStep 2: Creating demo branches")
print("-" * 70)
try:
    spark.sql("CREATE BRANCH IF NOT EXISTS demo_dev IN nessie")
    print("✓ Created 'demo_dev' branch")
except:
    print("  Branch 'demo_dev' already exists")

try:
    spark.sql("CREATE BRANCH IF NOT EXISTS demo_staging IN nessie")
    print("✓ Created 'demo_staging' branch")
except:
    print("  Branch 'demo_staging' already exists")

# Demo Step 3: Switch to main and create sample data
print("\nStep 3: Working on MAIN branch")
print("-" * 70)
spark.sql("USE REFERENCE main IN nessie")
print("✓ Switched to 'main' branch")

# Create namespace
try:
    spark.sql("CREATE NAMESPACE IF NOT EXISTS nessie.demo")
except:
    pass

# Create sample data on main
main_data = [
    (1, "Production Data", "v1.0"),
    (2, "Stable Release", "v1.0"),
]
main_df = spark.createDataFrame(main_data, ["id", "description", "version"])
main_df.writeTo("nessie.demo.sample_table").using("iceberg").createOrReplace()
print("✓ Created table with PRODUCTION data on main")

spark.sql("SELECT * FROM nessie.demo.sample_table").show()

# Demo Step 4: Switch to demo_dev and modify data
print("\nStep 4: Switching to DEMO_DEV branch")
print("-" * 70)
spark.sql("USE REFERENCE demo_dev IN nessie")
print("✓ Switched to 'demo_dev' branch")

# Create different data on dev branch
dev_data = [
    (1, "Development Data", "v2.0-dev"),
    (2, "Experimental Feature", "v2.0-dev"),
    (3, "New Feature Test", "v2.0-dev"),
]
dev_df = spark.createDataFrame(dev_data, ["id", "description", "version"])

try:
    spark.sql("CREATE NAMESPACE IF NOT EXISTS nessie.demo")
except:
    pass

dev_df.writeTo("nessie.demo.sample_table").using("iceberg").createOrReplace()
print("✓ Created table with DEVELOPMENT data on demo_dev")

spark.sql("SELECT * FROM nessie.demo.sample_table").show()

# Demo Step 5: Switch to demo_staging
print("\nStep 5: Switching to DEMO_STAGING branch")
print("-" * 70)
spark.sql("USE REFERENCE demo_staging IN nessie")
print("✓ Switched to 'demo_staging' branch")

# Create different data on staging
staging_data = [
    (1, "Staging Data", "v1.5-rc"),
    (2, "Pre-release", "v1.5-rc"),
]
staging_df = spark.createDataFrame(staging_data, ["id", "description", "version"])

try:
    spark.sql("CREATE NAMESPACE IF NOT EXISTS nessie.demo")
except:
    pass

staging_df.writeTo("nessie.demo.sample_table").using("iceberg").createOrReplace()
print("✓ Created table with STAGING data on demo_staging")

spark.sql("SELECT * FROM nessie.demo.sample_table").show()

# Demo Step 6: Show branch isolation
print("\nStep 6: Demonstrating Branch Isolation")
print("=" * 70)
print("The SAME table has DIFFERENT data on each branch!")
print("=" * 70)

print("\n📊 Table on MAIN branch:")
spark.sql("USE REFERENCE main IN nessie")
spark.sql("SELECT * FROM nessie.demo.sample_table").show()

print("\n📊 Table on DEMO_DEV branch:")
spark.sql("USE REFERENCE demo_dev IN nessie")
spark.sql("SELECT * FROM nessie.demo.sample_table").show()

print("\n📊 Table on DEMO_STAGING branch:")
spark.sql("USE REFERENCE demo_staging IN nessie")
spark.sql("SELECT * FROM nessie.demo.sample_table").show()

# Demo Step 7: Show branch details
print("\nStep 7: Branch Management Operations")
print("-" * 70)
print("Current branches:")
spark.sql("LIST REFERENCES IN nessie").show()

print("\nCurrent branch details:")
spark.sql("SHOW REFERENCE IN nessie").show()

# Cleanup demo branches (optional)
print("\nDemo complete! To clean up demo branches, run:")
print("  spark.sql(\"DROP BRANCH IF EXISTS demo_dev IN nessie\")")
print("  spark.sql(\"DROP BRANCH IF EXISTS demo_staging IN nessie\")")

spark.stop()

print("")
print("=" * 70)
print("✓ BRANCH SWITCHING DEMONSTRATION COMPLETE!")
print("=" * 70)
print("")
print("Key Takeaways:")
print("  1. ✓ Created multiple branches (main, demo_dev, demo_staging)")
print("  2. ✓ Switched between branches using USE REFERENCE")
print("  3. ✓ Each branch has independent data")
print("  4. ✓ Same table name, different content per branch")
print("  5. ✓ This is Git for Data!  ")
print("")
print("This demonstrates the CORE CONCEPT of your project:")
print("  - Write-Audit-Publish pattern")
print("  - Branch isolation")
print("  - Data versioning")
print("  - Safe experimentation")
print("=" * 70)
