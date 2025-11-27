from pyiceberg.catalog import load_catalog
from pyiceberg.schema import Schema
from pyiceberg.types import NestedField, StringType, IntegerType, TimestampType, DoubleType, BooleanType
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from config.iceberg_config import CATALOG_CONFIG, NAMESPACE

def get_catalog(branch="main"):
    config = CATALOG_CONFIG.copy()
    config["ref"] = branch
    return load_catalog("nessie", **config)

def create_namespace(catalog, namespace=NAMESPACE):
    try:
        catalog.create_namespace(namespace)
        print(f"✓ Created namespace: {namespace}")
    except Exception as e:
        if "already exists" in str(e).lower():
            print(f"✓ Namespace exists: {namespace}")
        else:
            raise

def table_exists(catalog, namespace, table_name):
    try:
        catalog.load_table(f"{namespace}.{table_name}")
        return True
    except:
        return False

def create_table_if_not_exists(catalog, namespace, table_name, schema):
    full_name = f"{namespace}.{table_name}"
    if table_exists(catalog, namespace, table_name):
        print(f"✓ Table exists: {full_name}")
        return catalog.load_table(full_name)
    
    table = catalog.create_table(identifier=full_name, schema=schema)
    print(f"✓ Created table: {full_name}")
    return table

# Schema Definitions
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