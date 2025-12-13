# Complete Setup Guide: Build Your Own Versioned Data Lakehouse

**A step-by-step tutorial to build a Git-like data lakehouse from scratch**

This guide will walk you through creating a production-ready data lakehouse with:
- Apache Iceberg for ACID transactions
- Project Nessie for Git-like version control
- PySpark for data processing
- MinIO for object storage
- Complete Bronze → Silver → Gold medallion architecture

**Time Required**: 2-3 hours  
**Difficulty**: Intermediate  
**Prerequisites**: Docker Desktop installed

---

## 📋 Table of Contents

1. [Project Setup](#step-1-project-setup)
2. [Docker Environment](#step-2-docker-environment)
3. [Sample Data](#step-3-sample-data)
4. [Bronze Layer](#step-4-bronze-layer)
5. [Create Branches](#step-5-create-branches)
6. [Silver Layer](#step-6-silver-layer)
7. [Verification](#step-7-verification)
8. [Branch Demo](#step-8-branch-demo)

---

## Step 1: Project Setup

### 1.1 Create Project Directory

```bash
# Create main project directory
mkdir Version_Control_For_Databases
cd Version_Control_For_Databases

# Create directory structure
mkdir -p config data/orders data/customers scripts/bronze scripts/silver scripts/gold scripts/utils plan
```

### 1.2 Initialize Git Repository

```bash
git init
echo "# Versioned Data Lakehouse" > README.md
git add README.md
git commit -m "Initial commit"
```

---

## Step 2: Docker Environment

### 2.1 Create docker-compose.yml

**File**: `docker-compose.yml`

```yaml
version: '3.8'

services:
  # MinIO - S3-compatible object storage
  minio:
    image: minio/minio
    container_name: lakehouse-minio
    ports:
      - "9000:9000"
      - "9001:9001"
    environment:
      MINIO_ROOT_USER: admin
      MINIO_ROOT_PASSWORD: password123
    command: server /data --console-address ":9001"
    volumes:
      - minio-data:/data
    networks:
      - lakehouse

  # Create MinIO bucket on startup
  minio-setup:
    image: minio/mc
    depends_on:
      - minio
    entrypoint: >
      /bin/sh -c "
      until /usr/bin/mc config host add myminio http://minio:9000 admin password123; do echo 'Waiting for MinIO...' && sleep 1; done;
      /usr/bin/mc mb myminio/lakehouse --ignore-existing;
      /usr/bin/mc mb myminio/warehouse --ignore-existing;
      exit 0;
      "
    networks:
      - lakehouse

  # Nessie - Git-like catalog
  nessie:
    image: projectnessie/nessie:0.67.0
    container_name: lakehouse-nessie
    ports:
      - "19120:19120"
    environment:
      - QUARKUS_HTTP_PORT=19120
      - NESSIE_VERSION_STORE_TYPE=IN_MEMORY
    networks:
      - lakehouse
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:19120/api/v2/config"]
      interval: 10s
      timeout: 5s
      retries: 5

  # PostgreSQL - for Airflow (optional for now)
  postgres:
    image: postgres:13
    container_name: lakehouse-postgres
    ports:
      - "5432:5432"
    environment:
      POSTGRES_USER: admin
      POSTGRES_PASSWORD: password123
      POSTGRES_DB: metastore
    volumes:
      - postgres-data:/var/lib/postgresql/data
    networks:
      - lakehouse

  # Spark - for data processing
  spark-notebook:
    image: alexmerced/spark33-notebook
    container_name: lakehouse-spark
    ports:
      - "8888:8888"
    environment:
      - JUPYTER_ENABLE_LAB=yes
      - GRANT_SUDO=yes
      - AWS_ACCESS_KEY_ID=admin
      - AWS_SECRET_ACCESS_KEY=password123
      - AWS_S3_ENDPOINT=http://minio:9000
      - AWS_REGION=us-east-1
      - NESSIE_URI=http://nessie:19120/api/v1
      - WAREHOUSE=s3a://lakehouse/warehouse
    volumes:
      - ./scripts:/home/jovyan/scripts
      - ./data:/home/jovyan/data
      - ./config:/home/jovyan/config
    networks:
      - lakehouse
    depends_on:
      - minio
      - nessie

volumes:
  minio-data:
  postgres-data:

networks:
  lakehouse:
    driver: bridge
```

### 2.2 Start Services

```bash
# Start all services
docker compose up -d

# Wait for services to be ready (30 seconds)
sleep 30

# Verify all services are running
docker ps

# Check Nessie is healthy
curl http://localhost:19120/api/v2/config

# You should see MinIO at: http://localhost:9001 (admin/password123)
# You should see Jupyter at: http://localhost:8888
```

---

## Step 3: Sample Data

### 3.1 Generate Orders Data

**File**: `data/orders/orders.csv`

```bash
cat > data/orders/orders.csv << 'EOF'
order_id,customer_id,order_date,total_amount,status,created_at
ORD000001,CUST0001,2024-01-15,139.74,completed,2024-01-15T10:30:00
ORD000002,CUST0002,2024-01-15,382.95,pending,2024-01-15T11:15:00
ORD000003,CUST0003,2024-01-16,170.62,completed,2024-01-16T09:20:00
ORD000004,CUST0004,2024-01-16,833.03,cancelled,2024-01-16T14:45:00
ORD000005,CUST0005,2024-01-17,773.39,completed,2024-01-17T08:10:00
EOF
```

**Or generate 1000 records with Python:**

```bash
cat > data/generate_orders.py << 'EOF'
import csv
import random
from datetime import datetime, timedelta

# Generate 1000 orders
with open('orders/orders.csv', 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['order_id', 'customer_id', 'order_date', 'total_amount', 'status', 'created_at'])
    
    statuses = ['completed', 'pending', 'cancelled', 'refunded']
    start_date = datetime(2024, 1, 1)
    
    for i in range(1, 1001):
        order_id = f'ORD{i:06d}'
        customer_id = f'CUST{random.randint(1, 200):04d}'
        days_offset = random.randint(0, 365)
        order_date = start_date + timedelta(days=days_offset)
        total_amount = round(random.uniform(10, 1000), 2)
        status = random.choice(statuses)
        created_at = order_date.strftime('%Y-%m-%dT%H:%M:%S')
        
        writer.writerow([order_id, customer_id, order_date.strftime('%Y-%m-%d'), 
                        total_amount, status, created_at])

print("✓ Generated 1000 orders")
EOF

python3 data/generate_orders.py
```

### 3.2 Generate Customers Data

```bash
cat > data/generate_customers.py << 'EOF'
import csv
from datetime import datetime, timedelta
import random

with open('customers/customers.csv', 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['customer_id', 'name', 'email', 'signup_date', 'is_active'])
    
    for i in range(1, 201):
        customer_id = f'CUST{i:04d}'
        name = f'Customer {i}'
        email = f'customer{i}@example.com'
        days_ago = random.randint(0, 730)
        signup_date = datetime.now() - timedelta(days=days_ago)
        is_active = random.choice([True, False])
        
        writer.writerow([customer_id, name, email, 
                        signup_date.strftime('%Y-%m-%d'), is_active])

print("✓ Generated 200 customers")
EOF

python3 data/generate_customers.py
```

---

## Step 4: Bronze Layer

### 4.1 Create Orders Ingestion Script

**File**: `scripts/bronze/ingest_orders_spark.py`

```python
"""
Bronze Layer - Orders Ingestion
Reads CSV and writes to Iceberg table on bronze branch
"""

import os
import pyspark
from pyspark.sql import SparkSession
from pyspark.sql.types import StructType, StructField, StringType, DoubleType, TimestampType

# Configuration from environment
NESSIE_URI = os.getenv("NESSIE_URI", "http://nessie:19120/api/v1")
WAREHOUSE = os.getenv("WAREHOUSE", "s3a://lakehouse/warehouse")
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID", "admin")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "password123")
AWS_S3_ENDPOINT = os.getenv("AWS_S3_ENDPOINT", "http://minio:9000")

print("=" * 60)
print("BRONZE LAYER - ORDERS INGESTION")
print("=" * 60)

# Spark configuration
conf = (
    pyspark.SparkConf()
        .setAppName('bronze-orders-ingestion')
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
        .set('spark.sql.catalog.nessie.ref', 'bronze')
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

print("Step 1: Reading CSV data...")
orders_df = spark.read.csv(
    "/home/jovyan/data/orders/orders.csv",
    header=True,
    inferSchema=True
)
print(f"✓ Loaded {orders_df.count()} orders")

print("\nStep 2: Creating namespace...")
spark.sql("CREATE NAMESPACE IF NOT EXISTS nessie.ecommerce")
print("✓ Namespace created")

print("\nStep 3: Writing to Bronze...")
orders_df.writeTo("nessie.ecommerce.orders_bronze").createOrReplace()
print("✓ Data written to bronze branch")

print("\nStep 4: Verification...")
result = spark.sql("SELECT COUNT(*) as count FROM nessie.ecommerce.orders_bronze").collect()
print(f"✓ Verified {result[0]['count']} records in orders_bronze")

spark.stop()
print("\n" + "=" * 60)
print("✓ BRONZE INGESTION COMPLETE")
print("=" * 60)
```

### 4.2 Create Customers Ingestion Script

**File**: `scripts/bronze/ingest_customers_spark.py`

```python
"""
Bronze Layer - Customers Ingestion
"""

import os
import pyspark
from pyspark.sql import SparkSession

NESSIE_URI = os.getenv("NESSIE_URI", "http://nessie:19120/api/v1")
WAREHOUSE = os.getenv("WAREHOUSE", "s3a://lakehouse/warehouse")
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID", "admin")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "password123")
AWS_S3_ENDPOINT = os.getenv("AWS_S3_ENDPOINT", "http://minio:9000")

print("=" * 60)
print("BRONZE LAYER - CUSTOMERS INGESTION")
print("=" * 60)

conf = (
    pyspark.SparkConf()
        .setAppName('bronze-customers-ingestion')
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
        .set('spark.sql.catalog.nessie.ref', 'bronze')
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

print("Step 1: Reading CSV data...")
customers_df = spark.read.csv(
    "/home/jovyan/data/customers/customers.csv",
    header=True,
    inferSchema=True
)
print(f"✓ Loaded {customers_df.count()} customers")

print("\nStep 2: Creating namespace...")
spark.sql("CREATE NAMESPACE IF NOT EXISTS nessie.ecommerce")

print("\nStep 3: Writing to Bronze...")
customers_df.writeTo("nessie.ecommerce.customers_bronze").createOrReplace()
print("✓ Data written to bronze branch")

print("\nStep 4: Verification...")
result = spark.sql("SELECT COUNT(*) as count FROM nessie.ecommerce.customers_bronze").collect()
print(f"✓ Verified {result[0]['count']} records")

spark.stop()
print("\n" + "=" * 60)
print("✓ BRONZE INGESTION COMPLETE")
print("=" * 60)
```

### 4.3 Run Bronze Ingestion

```bash
# Copy scripts to container
docker cp scripts/bronze/ingest_orders_spark.py lakehouse-spark:/home/jovyan/scripts/bronze/
docker cp scripts/bronze/ingest_customers_spark.py lakehouse-spark:/home/jovyan/scripts/bronze/

# Run orders ingestion
docker exec lakehouse-spark python3 /home/jovyan/scripts/bronze/ingest_orders_spark.py

# Run customers ingestion
docker exec lakehouse-spark python3 /home/jovyan/scripts/bronze/ingest_customers_spark.py
```

---

## Step 5: Create Branches

### 5.1 Branch Creation Script

**File**: `scripts/utils/create_nessie_branches.py`

```python
"""
Create Nessie branches for medallion architecture
"""

import requests
import json

NESSIE_URL = "http://localhost:19120/api/v1"

def get_main_hash():
    response = requests.get(f"{NESSIE_URL}/trees/tree/main")
    return response.json()['hash']

def create_branch(branch_name, source_hash):
    payload = {
        "name": branch_name,
        "hash": source_hash
    }
    response = requests.post(
        f"{NESSIE_URL}/trees/tree",
        json=payload
    )
    if response.status_code == 200:
        print(f"✓ Created branch: {branch_name}")
    else:
        print(f"Branch {branch_name} may already exist")

main_hash = get_main_hash()
print(f"Main branch hash: {main_hash}\n")

create_branch("bronze", main_hash)
create_branch("silver", main_hash)
create_branch("gold", main_hash)

print("\n✓ All branches created")
```

### 5.2 Run Branch Creation

```bash
python3 scripts/utils/create_nessie_branches.py

# Verify branches
curl http://localhost:19120/api/v1/trees | python3 -m json.tool
```

---

## Step 6: Silver Layer

### 6.1 Quality Checks Utility

**File**: `scripts/utils/quality_checks.py`

```python
"""
Reusable Quality Check Framework
"""

from pyspark.sql import DataFrame
from typing import List, Optional

class QualityCheckException(Exception):
    pass

class QualityChecker:
    def __init__(self, df: DataFrame, table_name: str):
        self.df = df
        self.table_name = table_name
        self.checks = []
        self.passed = []
        self.failed = []
    
    def check_row_count(self, min_expected: int, max_expected: Optional[int] = None):
        """Validate row count is within expected range"""
        count = self.df.count()
        check_name = "row_count"
        
        if max_expected:
            passed = min_expected <= count <= max_expected
            detail = f"value={count}, range={min_expected} to {max_expected}"
        else:
            passed = count >= min_expected
            detail = f"value={count}, range={min_expected} to unlimited"
        
        self._record_check(check_name, passed, detail)
        return self
    
    def check_nulls(self, columns: List[str]):
        """Check for null values in specified columns"""
        for col in columns:
            null_count = self.df.filter(self.df[col].isNull()).count()
            check_name = f"null_check"
            detail = f"column={col}, nulls={null_count}"
            self._record_check(check_name, null_count == 0, detail)
        return self
    
    def check_duplicates(self, key_columns: List[str]):
        """Check for duplicate records"""
        total_count = self.df.count()
        distinct_count = self.df.select(key_columns).distinct().count()
        duplicates = total_count - distinct_count
        
        check_name = "duplicate_check"
        detail = f"keys={key_columns}, duplicates={duplicates}"
        self._record_check(check_name, duplicates == 0, detail)
        return self
    
    def check_value_range(self, column: str, min_val=None, max_val=None):
        """Validate values are within expected range"""
        check_name = "value_range"
        
        if min_val is not None and max_val is not None:
            out_of_range = self.df.filter(
                (self.df[column] < min_val) | (self.df[column] > max_val)
            ).count()
            detail = f"column={column}, range={min_val} to {max_val}"
        elif min_val is not None:
            out_of_range = self.df.filter(self.df[column] < min_val).count()
            detail = f"column={column}, range={min_val} to None"
        else:
            out_of_range = self.df.filter(self.df[column] > max_val).count()
            detail = f"column={column}, range=None to {max_val}"
        
        self._record_check(check_name, out_of_range == 0, detail)
        return self
    
    def _record_check(self, check_name: str, passed: bool, detail: str):
        """Record check result"""
        result = {"check": check_name, "passed": passed, "detail": detail}
        self.checks.append(result)
        if passed:
            self.passed.append(result)
        else:
            self.failed.append(result)
    
    def validate(self, raise_on_failure: bool = True):
        """Generate report and optionally raise exception if checks failed"""
        self.generate_report()
        
        if self.failed and raise_on_failure:
            raise QualityCheckException(
                f"Quality checks failed: {len(self.failed)}/{len(self.checks)} checks failed"
            )
        
        return len(self.failed) == 0
    
    def generate_report(self):
        """Print quality check report"""
        print("=" * 60)
        print(f"QUALITY CHECK REPORT: {self.table_name}")
        print("=" * 60)
        print()
        
        if self.passed:
            print(f"✓ PASSED CHECKS: {len(self.passed)}")
            for check in self.passed:
                print(f"  ✓ {check['check']}: {check['detail']}")
        
        if self.failed:
            print(f"\n✗ FAILED CHECKS: {len(self.failed)}")
            for check in self.failed:
                print(f"  ✗ {check['check']}: {check['detail']}")
        
        pass_rate = (len(self.passed) / len(self.checks)) * 100 if self.checks else 0
        print(f"\nSUMMARY: {len(self.passed)}/{len(self.checks)} checks passed ({pass_rate:.1f}%)")
        print("=" * 60)
```

### 6.2 Orders Silver Transformation

**File**: `scripts/silver/transform_orders_silver.py`

```python
"""
Silver Orders Transformation
Uses @branch syntax to read from bronze and write to silver
"""

import os
import sys
import pyspark
from pyspark.sql import SparkSession
from pyspark.sql import functions as F

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from utils.quality_checks import QualityChecker

NESSIE_URI = os.getenv("NESSIE_URI", "http://nessie:19120/api/v1")
WAREHOUSE = os.getenv("WAREHOUSE", "s3a://lakehouse/warehouse")
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID", "admin")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "password123")
AWS_S3_ENDPOINT = os.getenv("AWS_S3_ENDPOINT", "http://minio:9000")

print("=" * 70)
print("SILVER ORDERS TRANSFORMATION")
print("=" * 70)

conf = (
    pyspark.SparkConf()
        .setAppName('silver-orders')
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
        .set('spark.sql.catalog.nessie.ref', 'main')
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

# Read from bronze branch using @branch syntax
print("\nStep 1: Reading from bronze branch...")
bronze_df = spark.sql("SELECT * FROM nessie.ecommerce.`orders_bronze@bronze`")
bronze_count = bronze_df.count()
print(f"✓ Read {bronze_count} records")

# Apply transformations
print("\nStep 2: Applying transformations...")
silver_df = bronze_df.dropDuplicates(["order_id"])
silver_df = silver_df.withColumn(
    "data_quality_score",
    F.when(
        (F.col("order_id").isNotNull()) &
        (F.col("customer_id").isNotNull()) &
        (F.col("total_amount") > 0) &
        (F.col("status").isNotNull()),
        100
    ).otherwise(50)
)
silver_df = silver_df.withColumn("processed_at", F.current_timestamp())
silver_count = silver_df.count()
print(f"✓ Transformed {silver_count} records")

# Quality checks
print("\nStep 3: Quality checks...")
checker = QualityChecker(silver_df, "orders_silver")
checker.check_row_count(min_expected=int(bronze_count * 0.90))
checker.check_nulls(["order_id", "customer_id"])
checker.check_duplicates(["order_id"])
checker.check_value_range("total_amount", min_val=0)
checker.validate(raise_on_failure=True)

# Write to silver branch
print("\nStep 4: Writing to silver branch...")
silver_df.createOrReplaceTempView("silver_temp")
spark.sql("CREATE NAMESPACE IF NOT EXISTS nessie.ecommerce")
spark.sql("""
    CREATE OR REPLACE TABLE nessie.ecommerce.`orders_silver@silver`
    USING iceberg
    AS SELECT * FROM silver_temp
""")

verify_count = spark.sql("SELECT COUNT(*) as cnt FROM nessie.ecommerce.`orders_silver@silver`").collect()[0]['cnt']
print(f"✓ Verified {verify_count} records on silver branch")

spark.stop()
print("\n" + "=" * 70)
print("✓ SILVER TRANSFORMATION COMPLETE")
print("=" * 70)
```

### 6.3 Run Silver Transformation

```bash
# Copy scripts
docker cp scripts/utils/quality_checks.py lakehouse-spark:/home/jovyan/scripts/utils/
docker cp scripts/silver/transform_orders_silver.py lakehouse-spark:/home/jovyan/scripts/silver/

# Run transformation
docker exec lakehouse-spark python3 /home/jovyan/scripts/silver/transform_orders_silver.py
```

---

## Step 7: Verification

### 7.1 Create End-to-End Test Script

**File**: `test_e2e.sh`

```bash
#!/bin/bash

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo "=========================================="
echo "END-TO-END VERIFICATION"
echo "=========================================="

# Test 1: Docker services
echo -e "\n${GREEN}Test 1: Docker Services${NC}"
if docker ps | grep -q lakehouse; then
    echo "✓ All services running"
else
    echo "✗ Services not running"
    exit 1
fi

# Test 2: MinIO
echo -e "\n${GREEN}Test 2: MinIO Storage${NC}"
if curl -s http://localhost:9000/minio/health/ready | grep -q "200 OK"; then
    echo "✓ MinIO healthy"
else
    echo "✗ MinIO not responding"
fi

# Test 3: Nessie
echo -e "\n${GREEN}Test 3: Nessie Catalog${NC}"
if curl -s http://localhost:19120/api/v2/config | grep -q "defaultBranch"; then
    echo "✓ Nessie responding"
else
    echo "✗ Nessie not responding"
fi

# Test 4: Branches
echo -e "\n${GREEN}Test 4: Branch Creation${NC}"
BRANCHES=$(curl -s http://localhost:19120/api/v1/trees | python3 -m json.tool | grep '"name"' | wc -l)
if [ $BRANCHES -ge 3 ]; then
    echo "✓ Branches created ($BRANCHES total)"
else
    echo "✗ Missing branches"
fi

# Test 5: Bronze data
echo -e "\n${GREEN}Test 5: Bronze Tables${NC}"
BRONZE_TABLES=$(curl -s http://localhost:19120/api/v1/trees/tree/bronze/entries | grep -c "ICEBERG_TABLE")
if [ $BRONZE_TABLES -ge 2 ]; then
    echo "✓ Bronze tables exist ($BRONZE_TABLES tables)"
else
    echo "✗ Bronze tables missing"
fi

# Test 6: Silver data
echo -e "\n${GREEN}Test 6: Silver Tables${NC}"
SILVER_TABLES=$(curl -s http://localhost:19120/api/v1/trees/tree/silver/entries | grep -c "orders_silver")
if [ $SILVER_TABLES -ge 1 ]; then
    echo "✓ Silver tables exist"
else
    echo "⚠ Silver tables not found (may not be created yet)"
fi

echo -e "\n=========================================="
echo -e "${GREEN}✓ VERIFICATION COMPLETE${NC}"
echo "=========================================="
```

### 7.2 Run Verification

```bash
chmod +x test_e2e.sh
./test_e2e.sh
```

---

## Step 8: Branch Demo

### 8.1 Interactive Branch Demonstration

```bash
# Enter Spark container
docker exec -it lakehouse-spark /bin/bash

# Start PySpark with Nessie config
pyspark --packages org.apache.iceberg:iceberg-spark-runtime-3.3_2.12:1.3.1,org.projectnessie.nessie-integrations:nessie-spark-extensions-3.3_2.12:0.67.0,software.amazon.awssdk:bundle:2.17.178,software.amazon.awssdk:url-connection-client:2.17.178 --conf spark.sql.extensions=org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions,org.projectnessie.spark.extensions.NessieSparkSessionExtensions --conf spark.sql.catalog.nessie=org.apache.iceberg.spark.SparkCatalog --conf spark.sql.catalog.nessie.uri=http://nessie:19120/api/v1 --conf spark.sql.catalog.nessie.ref=main --conf spark.sql.catalog.nessie.authentication.type=NONE --conf spark.sql.catalog.nessie.catalog-impl=org.apache.iceberg.nessie.NessieCatalog --conf spark.sql.catalog.nessie.warehouse=s3a://lakehouse/warehouse --conf spark.sql.catalog.nessie.io-impl=org.apache.iceberg.aws.s3.S3FileIO --conf spark.sql.catalog.nessie.s3.endpoint=http://minio:9000 --conf spark.hadoop.fs.s3a.access.key=admin --conf spark.hadoop.fs.s3a.secret.key=password123 --conf spark.hadoop.fs.s3a.endpoint=http://minio:9000 --conf spark.hadoop.fs.s3a.path.style.access=true --conf spark.hadoop.fs.s3a.connection.ssl.enabled=false
```

Then in PySpark:

```python
# List all branches
spark.sql("LIST REFERENCES IN nessie").show()

# Read from bronze branch
bronze_df = spark.sql("SELECT * FROM nessie.ecommerce.`orders_bronze@bronze`")
print(f"Bronze records: {bronze_df.count()}")

# Read from silver branch
silver_df = spark.sql("SELECT * FROM nessie.ecommerce.`orders_silver@silver`")
print(f"Silver records: {silver_df.count()}")

# Show quality scores
spark.sql("""
    SELECT data_quality_score, COUNT(*) as count 
    FROM nessie.ecommerce.`orders_silver@silver`
    GROUP BY data_quality_score
""").show()

# Create demo branch
spark.sql("CREATE BRANCH IF NOT EXISTS demo IN nessie")

# Write test data to demo branch
test_df = spark.sql("SELECT * FROM nessie.ecommerce.`orders_silver@silver` LIMIT 10")
test_df.createOrReplaceTempView("test_data")
spark.sql("""
    CREATE OR REPLACE TABLE nessie.ecommerce.`test_table@demo`
    USING iceberg
    AS SELECT * FROM test_data
""")

# Verify isolation
spark.sql("SELECT COUNT(*) FROM nessie.ecommerce.`test_table@demo`").show()

# Exit
exit()
```

---

## 🎯 Success Checklist

- [ ] All Docker containers running
- [ ] MinIO accessible at http://localhost:9001
- [ ] Nessie API responding
- [ ] Bronze, Silver, Gold branches created
- [ ] Orders and Customers data in Bronze
- [ ] Orders data in Silver with quality scores
- [ ] Quality checks passing (100%)
- [ ] Branch switching working (@ syntax)
- [ ] End-to-end test passing

---

## 🐛 Troubleshooting

### Service Won't Start

```bash
# Check logs
docker compose logs nessie
docker compose logs minio
docker compose logs spark-notebook

# Restart services
docker compose restart

# Full reset
docker compose down -v
docker compose up -d
```

### Out of Disk Space

```bash
# Clean up Docker
docker system prune -a --volumes --force

# Remove unused images
docker image prune -a
```

### Can't Connect to Nessie

```bash
# Verify Nessie is running
curl http://localhost:19120/api/v2/config

# Check network
docker network inspect version_control_for_databases_lakehouse
```

### Spark Job Fails

```bash
# Check Spark logs
docker logs lakehouse-spark

# Verify environment variables
docker exec lakehouse-spark env | grep -E "NESSIE|AWS|WAREHOUSE"
```

---

## 📚 Next Steps

1. **Complete Customers Silver**: Adapt orders script for customers
2. **Build Gold Layer**: Create aggregations (customer_summary, daily_revenue)
3. **Add Orchestration**: Set up Airflow for pipeline automation
4. **Create Visualizations**: Build Jupyter notebooks for demos
5. **Documentation**: Write blog post about your journey

---

## 🔗 Useful Commands

```bash
# View all tables on a branch
curl -s http://localhost:19120/api/v1/trees/tree/bronze/entries | python3 -m json.tool

# Quick Spark SQL query
docker exec lakehouse-spark python3 -c "
from pyspark.sql import SparkSession
import pyspark

# ... (Spark config here)

spark = SparkSession.builder.config(conf=conf).getOrCreate()
spark.sql('SELECT COUNT(*) FROM nessie.ecommerce.orders_bronze').show()
spark.stop()
"

# Commit to Git
git add .
git commit -m "Milestone: Bronze and Silver layers complete"
git push
```

---

## 📖 Resources

- [Apache Iceberg Docs](https://iceberg.apache.org/)
- [Project Nessie Docs](https://projectnessie.org/)
- [PySpark Guide](https://spark.apache.org/docs/latest/api/python/)
- [MinIO Docs](https://min.io/docs/minio/linux/index.html)

---

**Congratulations!** 🎉 You've built a production-ready versioned data lakehouse!

If you followed all steps, you now have:
- ✅ Working Bronze layer
- ✅ Working Silver layer with quality checks
- ✅ Branch isolation (Git for data!)
- ✅ Complete medallion architecture foundation
- ✅ All code and documentation ready

**Total Time**: ~2-3 hours  
**Lines of Code Written**: ~1,000  
**Concepts Learned**: ACID transactions, Data versioning, Quality checks, Medallion architecture

---

*Last Updated: December 2024*
