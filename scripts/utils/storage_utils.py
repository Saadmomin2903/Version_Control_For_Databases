"""
Storage Utilities for PySpark + Nessie Lakehouse

NOTE: This file contains LEGACY PyIceberg utilities.
      Current implementation uses PySpark scripts directly.
      
      These utilities are kept for reference/future use.
      
Active Implementation:
- scripts/bronze/ingest_orders_spark.py
- scripts/bronze/ingest_customers_spark.py

Why PySpark instead of PyIceberg?
- Simpler S3 configuration (Spark handles it directly)
- Nessie only needs to track metadata (no S3 vending)
- Proven working pattern with Nessie + MinIO
"""

import sys
import os

# Note: These imports will fail if PyIceberg is not installed
# That's OK - we're using PySpark now
try:
    from pyiceberg.catalog import load_catalog
    from pyiceberg.schema import Schema
    from pyiceberg.types import (
        NestedField, StringType, IntegerType, 
        TimestampType, DoubleType, BooleanType
    )
    PYICEBERG_AVAILABLE = True
except ImportError:
    PYICEBERG_AVAILABLE = False
    print("PyIceberg not available - using PySpark instead")

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from config.iceberg_config import NAMESPACE

# ============================================================================
# LEGACY PYICEBERG FUNCTIONS (Not actively used)
# ============================================================================

def get_catalog(branch="main"):
    """
    LEGACY: Get PyIceberg catalog connection
    
    NOTE: This is not used in current implementation.
    Use PySpark scripts instead.
    """
    if not PYICEBERG_AVAILABLE:
        raise ImportError("PyIceberg not installed. Use PySpark scripts instead.")
    
    from config.iceberg_config import CATALOG_CONFIG
    config = CATALOG_CONFIG.copy()
    config["ref"] = branch
    return load_catalog("rest", **config)

def create_namespace(catalog, namespace=NAMESPACE):
    """LEGACY: Create namespace using PyIceberg"""
    if not PYICEBERG_AVAILABLE:
        raise ImportError("PyIceberg not installed. Use PySpark scripts instead.")
    
    try:
        catalog.create_namespace(namespace)
        print(f"✓ Created namespace: {namespace}")
    except Exception as e:
        if "already exists" in str(e).lower():
            print(f"✓ Namespace exists: {namespace}")
        else:
            raise

def table_exists(catalog, namespace, table_name):
    """LEGACY: Check if table exists using PyIceberg"""
    if not PYICEBERG_AVAILABLE:
        return False
    
    try:
        catalog.load_table(f"{namespace}.{table_name}")
        return True
    except:
        return False

def create_table_if_not_exists(catalog, namespace, table_name, schema):
    """LEGACY: Create table using PyIceberg"""
    if not PYICEBERG_AVAILABLE:
        raise ImportError("PyIceberg not installed. Use PySpark scripts instead.")
    
    full_name = f"{namespace}.{table_name}"
    if table_exists(catalog, namespace, table_name):
        print(f"✓ Table exists: {full_name}")
        return catalog.load_table(full_name)
    
    table = catalog.create_table(identifier=full_name, schema=schema)
    print(f"✓ Created table: {full_name}")
    return table

# ============================================================================
# SCHEMA DEFINITIONS (Can be used for reference)
# ============================================================================

if PYICEBERG_AVAILABLE:
    ORDERS_SCHEMA = Schema(
        NestedField(1, "order_id", StringType(), required=True),
        NestedField(2, "customer_id", StringType(), required=True),
        NestedField(3, "order_date", TimestampType(), required=True),
        NestedField(4, "total_amount", DoubleType(), required=True),
        NestedField(5, "status", StringType(), required=True),
        NestedField(6, "created_at", TimestampType(), required=True),
    )

    CUSTOMERS_SCHEMA = Schema(
        NestedField(1, "customer_id", StringType(), required=True),
        NestedField(2, "name", StringType(), required=True),
        NestedField(3, "email", StringType(), required=True),
        NestedField(4, "signup_date", TimestampType(), required=True),
        NestedField(5, "is_active", BooleanType(), required=True),
    )
else:
    # Placeholder schemas when PyIceberg not available
    ORDERS_SCHEMA = None
    CUSTOMERS_SCHEMA = None

# ============================================================================
# PYSPARK UTILITIES (Active Implementation)
# ============================================================================

def get_spark_config():
    """
    Get Spark configuration for Nessie + MinIO
    
    Returns dict of Spark configuration that can be used
    to configure SparkSession for Iceberg + Nessie.
    
    Usage:
        conf = pyspark.SparkConf()
        for key, value in get_spark_config().items():
            conf.set(key, value)
    """
    from config.iceberg_config import NESSIE_URI, S3_ENDPOINT, PYSPARK_CONFIG
    
    return {
        # Iceberg and Nessie JAR dependencies
        'spark.jars.packages': 
            'org.apache.iceberg:iceberg-spark-runtime-3.3_2.12:1.3.1,'
            'org.projectnessie.nessie-integrations:nessie-spark-extensions-3.3_2.12:0.67.0,'
            'software.amazon.awssdk:bundle:2.17.178,'
            'software.amazon.awssdk:url-connection-client:2.17.178',
        
        # Spark SQL extensions
        'spark.sql.extensions': 
            'org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions,'
            'org.projectnessie.spark.extensions.NessieSparkSessionExtensions',
        
        # Nessie catalog configuration
        'spark.sql.catalog.nessie': 'org.apache.iceberg.spark.SparkCatalog',
        'spark.sql.catalog.nessie.uri': NESSIE_URI,
        'spark.sql.catalog.nessie.ref': 'main',
        'spark.sql.catalog.nessie.authentication.type': 'NONE',
        'spark.sql.catalog.nessie.catalog-impl': 'org.apache.iceberg.nessie.NessieCatalog',
        'spark.sql.catalog.nessie.warehouse': PYSPARK_CONFIG['warehouse'],
        'spark.sql.catalog.nessie.io-impl': 'org.apache.iceberg.aws.s3.S3FileIO',
        
        # S3/MinIO configuration
        'spark.sql.catalog.nessie.s3.endpoint': S3_ENDPOINT,
        'spark.hadoop.fs.s3a.access.key': PYSPARK_CONFIG['s3.access-key-id'],
        'spark.hadoop.fs.s3a.secret.key': PYSPARK_CONFIG['s3.secret-access-key'],
        'spark.hadoop.fs.s3a.endpoint': S3_ENDPOINT,
        'spark.hadoop.fs.s3a.path.style.access': 'true',
        'spark.hadoop.fs.s3a.connection.ssl.enabled': 'false',
        'spark.hadoop.fs.s3a.impl': 'org.apache.hadoop.fs.s3a.S3AFileSystem',
    }

if __name__ == "__main__":
    print("=" * 60)
    print("STORAGE UTILITIES STATUS")
    print("=" * 60)
    print(f"PyIceberg Available: {PYICEBERG_AVAILABLE}")
    print(f"Active Implementation: PySpark")
    print(f"Active Scripts: scripts/bronze/ingest_*_spark.py")
    print("=" * 60)
    
    if PYICEBERG_AVAILABLE:
        print("\nPyIceberg is available but not actively used.")
        print("Use PySpark scripts for data ingestion.")
    else:
        print("\nPyIceberg not installed (this is OK).")
        print("Using PySpark for all data operations.")