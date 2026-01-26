"""
Full Dataset Ingestion - Batch Processing by Month
---------------------------------------------------
Processes 411M e-commerce records from April-November 2020 in monthly batches.
Avoids OOM by processing one month at a time.

Current state: April 2020 (3.1M records) already loaded
To load: May-November 2020 (~370M additional records)
"""

import os
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, to_date, year, month
from datetime import datetime

# Configuration
# Data is in the locally mounted directory (accessible via Docker volume)
DATA_PATH = os.getenv("DATA_PATH", "/home/jovyan/data/firebolt-raw")
NESSIE_URI = os.getenv("NESSIE_URI", "http://nessie:19120/api/v1")
WAREHOUSE = os.getenv("WAREHOUSE", "s3a://lakehouse-prod/warehouse")
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY", "962c9f862226831e4edea90cfcfafb8a8dffcd51")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_KEY", "sd2rGU918DTmn35E4xJ8EV7BX2XUt7DkqC8v6WDNDUw=")
AWS_S3_ENDPOINT = os.getenv("AWS_S3_ENDPOINT", "https://bmcfe6z38foz.compat.objectstorage.ap-mumbai-1.oraclecloud.com")

def get_spark_session():
    """Initialize Spark with Nessie + Iceberg + S3"""
    import pyspark
    conf = (
        pyspark.SparkConf()
        .setAppName('full-dataset-ingestion')
        .set('spark.sql.adaptive.enabled', 'true')
        .set('spark.sql.adaptive.coalescePartitions.enabled', 'true')
        .set('spark.jars.packages',
             'org.apache.iceberg:iceberg-spark-runtime-3.3_2.12:1.3.1,'
             'org.projectnessie.nessie-integrations:nessie-spark-extensions-3.3_2.12:0.67.0,'
             'org.apache.hadoop:hadoop-aws:3.3.1')
        .set('spark.sql.extensions',
             'org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions,'
             'org.projectnessie.spark.extensions.NessieSparkSessionExtensions')
        .set('spark.sql.catalog.nessie', 'org.apache.iceberg.spark.SparkCatalog')
        .set('spark.sql.catalog.nessie.uri', NESSIE_URI)
        .set('spark.sql.catalog.nessie.ref', 'bronze')
        .set('spark.sql.catalog.nessie.catalog-impl', 'org.apache.iceberg.nessie.NessieCatalog')
        .set('spark.sql.catalog.nessie.warehouse', WAREHOUSE)
        .set('spark.sql.catalog.nessie.io-impl', 'org.apache.iceberg.hadoop.HadoopFileIO')
        .set('spark.hadoop.fs.s3a.access.key', AWS_ACCESS_KEY)
        .set('spark.hadoop.fs.s3a.secret.key', AWS_SECRET_KEY)
        .set('spark.hadoop.fs.s3a.endpoint', AWS_S3_ENDPOINT)
        .set('spark.hadoop.fs.s3a.path.style.access', 'true')
        .set('spark.hadoop.fs.s3a.connection.ssl.enabled', 'true')
    )
    return SparkSession.builder.config(conf=conf).getOrCreate()

def get_current_count():
    """Get current record count in Bronze table"""
    spark = get_spark_session()
    try:
        count = spark.sql("SELECT COUNT(*) as cnt FROM nessie.ecommerce.orders_bronze").collect()[0]['cnt']
        return count
    except Exception as e:
        print(f"⚠️  Table doesn't exist or error: {e}")
        return 0
    finally:
        spark.stop()

def ingest_month(year_val, month_val, dry_run=False):
    """
    Ingest a single month of data
    
    Args:
        year_val: Year (2020)
        month_val: Month (1-12)
        dry_run: If True, only count records without writing
    """
    spark = get_spark_session()
    
    try:
        month_name = datetime(year_val, month_val, 1).strftime('%B')
        print(f"\n{'='*60}")
        print(f"📅 Processing {month_name} {year_val}")
        print(f"{'='*60}")
        
        # Read full dataset
        print("📖 Reading source data...")
        df = spark.read.parquet(f"{DATA_PATH}/*.parquet")
        
        # Filter for specific month
        print(f"🔍 Filtering for {month_name} {year_val}...")
        month_df = df.filter(
            (year(to_date(col("event_time"))) == year_val) &
            (month(to_date(col("event_time"))) == month_val)
        )
        
        # Count records
        record_count = month_df.count()
        print(f"📊 Found {record_count:,} records for {month_name}")
        
        if record_count == 0:
            print(f"⚠️  No data for {month_name} {year_val}, skipping...")
            return 0
        
        if dry_run:
            print(f"✅ Dry run complete. Would process {record_count:,} records.")
            return record_count
        
        # Write to Bronze table
        print(f"💾 Writing to Bronze table...")
        month_df.writeTo("nessie.ecommerce.orders_bronze").append()
        
        print(f"✅ Successfully ingested {record_count:,} records for {month_name} {year_val}")
        return record_count
        
    except Exception as e:
        print(f"❌ Error processing {month_name} {year_val}: {e}")
        raise
    finally:
        spark.stop()

def ingest_all_months(start_month=5, end_month=11, dry_run=False):
    """
    Ingest multiple months sequentially
    
    Args:
        start_month: Starting month (5 = May)
        end_month: Ending month (11 = November)
        dry_run: If True, only count without writing
    """
    year = 2020
    total_records = 0
    
    print("\n" + "="*60)
    print("🚀 FULL DATASET INGESTION")
    print("="*60)
    
    # Show current state
    current_count = get_current_count()
    print(f"📊 Current Bronze table count: {current_count:,} records")
    
    if dry_run:
        print("\n⚠️  DRY RUN MODE - NO DATA WILL BE WRITTEN\n")
    
    # Process each month
    for month_val in range(start_month, end_month + 1):
        try:
            records = ingest_month(year, month_val, dry_run=dry_run)
            total_records += records
        except Exception as e:
            print(f"\n❌ Failed at month {month_val}, stopping ingestion")
            print(f"Error: {e}")
            break
    
    # Final summary
    print("\n" + "="*60)
    print("📈 INGESTION SUMMARY")
    print("="*60)
    print(f"Total new records: {total_records:,}")
    if not dry_run:
        final_count = get_current_count()
        print(f"Final Bronze count: {final_count:,}")
        print(f"Expected: {current_count + total_records:,}")
        if final_count == current_count + total_records:
            print("✅ Counts match!")
        else:
            print("⚠️  Count mismatch!")

if __name__ == "__main__":
    import sys
    
    # Parse arguments
    dry_run = "--dry-run" in sys.argv
    
    if dry_run:
        print("\n🔍 Running in DRY RUN mode (count only)\n")
    
    # Ingest May-November 2020
    ingest_all_months(start_month=5, end_month=11, dry_run=dry_run)
    
    print("\n✅ Full dataset ingestion complete!")
