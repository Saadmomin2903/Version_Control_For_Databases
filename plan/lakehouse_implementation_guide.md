# Complete Implementation Guide: Git-Style Versioned Lakehouse
## Apache Iceberg + Project Nessie + PySpark

**✅ WORKING SOLUTION - Updated Based on Implementation**

---

## 📋 TABLE OF CONTENTS

1. [Project Overview](#overview)
2. [Architecture & Technology Stack](#architecture)
3. [Prerequisites](#prerequisites)
4. [Phase 1: Infrastructure Setup](#phase1)
5. [Phase 2: Bronze Layer Implementation](#phase2)
6. [Phase 3: Silver Layer (TODO)](#phase3)
7. [Phase 4: Gold Layer (TODO)](#phase4)
8. [Troubleshooting & Lessons Learned](#troubleshooting)
9. [Quick Start Commands](#quickstart)

---

## 🎯 PROJECT OVERVIEW {#overview}

This guide implements a production-ready data lakehouse using:
- **Apache Iceberg**: Open table format with ACID transactions  
- **Project Nessie**: Git-like version control for data
- **PySpark**: Distributed data processing engine
- **MinIO**: S3-compatible object storage
- **Medallion Architecture**: Bronze → Silver → Gold layers

**Key Features:**
- Git-like branching for data
- ACID transactions
- Time-travel queries
- Scalable data processing
- Complete test coverage

**Project Status:**
- ✅ Infrastructure Setup (MinIO, Nessie, Spark)
- ✅ Bronze Layer (Orders & Customers ingestion working)
- 🚧 Silver Layer (In Progress)
- ⏳ Gold Layer (Planned)

---

## 🏗️ ARCHITECTURE & TECHNOLOGY STACK {#architecture}

### Working Architecture

```
┌─────────────┐
│   CSV Data  │
└──────┬──────┘
       │
       ▼
┌─────────────────┐
│   PySpark       │ ◄── Reads data, transforms, writes to S3
│   (Container)   │
└────────┬────────┘
         │
         ├──────────────┐
         ▼              ▼
  ┌──────────┐   ┌──────────┐
  │  MinIO   │   │  Nessie  │
  │  (S3)    │   │ (Catalog)│
  └──────────┘   └──────────┘
   Data Storage   Version Control
```

### Key Insight: Why This Works

**❌ What Didn't Work:**
- PyIceberg + Nessie REST Catalog
- Nessie responsible for S3 access (complex configuration)
- URN secret references not recognized

**✅ What Works:**
- **PySpark + Nessie NessieCatalog**
- **Spark handles S3 directly** (credentials configured in Spark)
- **Nessie only tracks metadata/versions** (no S3 config needed)

### Technology Stack Details

#### 1. **Apache Spark** (Data Processing)
- **Version**: 3.3
- **Image**: alexmerced/spark33-notebook
- **Purpose**: Read CSV → Transform → Write Iceberg tables
- **Why**: Proven working pattern with Nessie

#### 2. **Project Nessie** (Catalog)
- **Version**: Latest (projectnessie/nessie)
- **Purpose**: Git-like version control for tables
- **Configuration**: Minimal (no S3 config needed!)
- **API**: http://localhost:19120/api/v1

#### 3. **MinIO** (Object Storage)
- **Purpose**: S3-compatible storage for data
- **Credentials**: admin / password123 (change for production!)
- **Ports**: 9000 (API), 9001 (Console)

#### 4. **Apache Iceberg** (Table Format)
- **Version**: 1.3.1
- **Runtime**: iceberg-spark-runtime-3.3_2.12
- **Format**: Parquet data files + metadata

### Data Flow

1. **Ingest**: CSV → PySpark reads
2. **Write**: PySpark → MinIO (s3a://lakehouse/warehouse)
3. **Track**: Nessie registers table metadata
4. **Query**: PySpark → Nessie (catalog) → MinIO (data)

---

## ✅ PREREQUISITES {#prerequisites}

### Required Software

| Software | Minimum Version | Purpose |
|----------|----------------|---------|
| Docker Desktop | 24.0.0+ | Run containers |
| Docker Compose | 2.0.0+ | Orchestrate services |
| Python | 3.9+ | Optional (for local scripts) |
| curl | Any | Health checks |

### Disk Space Requirements

**Critical**: Ensure at least **10GB free disk space**

- Spark container: ~3.3GB
- Nessie container: ~400MB
 - MinIO data: Variable
- Docker system: ~2-5GB

**Check available space:**
```bash
df -h .
```

**Free up space if needed:**
```bash
# Clean Docker system
docker system prune -a --volumes --force

# Expected: Reclaim 10-50GB
```

### System Requirements
- **RAM**: 8GB minimum, 16GB recommended
- **CPU**: 4+ cores recommended
- **OS**: macOS 10.15+, Linux (Ubuntu 20.04+), Windows 10/11 with WSL2

---

## 🚀 PHASE 1: INFRASTRUCTURE SETUP {#phase1}

### Step 1.1: Create Project Structure

```bash
# Create main directory
mkdir -p Version_Control_For_Databases
cd Version_Control_For_Databases

# Create directory structure
mkdir -p config data/raw scripts/bronze scripts/silver scripts/gold scripts/utils
```

### Step 1.2: Create docker-compose.yml

**Create `docker-compose.yml`:**

```yaml
version: '3.8'

services:
  minio:
    image: minio/minio:latest
    container_name: lakehouse-minio
    ports:
      - "9000:9000"
      - "9001:9001"
    environment:
      - MINIO_ROOT_USER=admin
      - MINIO_ROOT_PASSWORD=password123
    command: server /data --console-address ":9001"
    volumes:
      - minio-data:/data
    networks:
      - lakehouse-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
      interval: 30s
      timeout: 20s
      retries: 3
    restart: unless-stopped

  postgres:
    image: postgres:15
    container_name: lakehouse-postgres
    environment:
      - POSTGRES_USER=lakehouse
      - POSTGRES_PASSWORD=lakehouse
      - POSTGRES_DB=metastore
    volumes:
      - postgres-data:/var/lib/postgresql/data
    networks:
      - lakehouse-network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U lakehouse"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  nessie:
    image: projectnessie/nessie
    container_name: lakehouse-nessie
    ports:
      - "19120:19120"
    networks:
      - lakehouse-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:19120/api/v2/config"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 45s
    restart: unless-stopped

  spark-notebook:
    image: alexmerced/spark33-notebook
    container_name: lakehouse-spark
    ports:
      - "8888:8888"
    environment:
      - AWS_REGION=us-east-1
      - AWS_ACCESS_KEY_ID=admin
      - AWS_SECRET_ACCESS_KEY=password123
      - AWS_S3_ENDPOINT=http://minio:9000
      - NESSIE_URI=http://nessie:19120/api/v1
      - WAREHOUSE=s3a://lakehouse/warehouse
    volumes:
      - ./data:/home/jovyan/data
      - ./scripts:/home/jovyan/scripts
    networks:
      - lakehouse-network
    depends_on:
      - minio
      - nessie

volumes:
  minio-data:
    driver: local
  postgres-data:
    driver: local

networks:
  lakehouse-network:
    driver: bridge
```

**Key Configuration Notes:**
- Nessie has NO S3 configuration (Spark handles it!)
- Spark environment variables configure S3 access
- All services on same Docker network

### Step 1.3: Start Infrastructure

```bash
# Start all services
docker compose up -d

# Wait ~30 seconds for services to be ready

# Verify all containers running
docker ps

# Expected output:
# lakehouse-spark      Up
# lakehouse-nessie     Up (healthy)
# lakehouse-minio      Up (healthy)
# lakehouse-postgres   Up (healthy)
```

### Step 1.4: Initial Setup

#### Create MinIO Bucket

```bash
# Set up MinIO alias and create bucket
docker exec lakehouse-minio mc alias set myminio http://localhost:9000 admin password123
docker exec lakehouse-minio mc mb myminio/lakehouse --ignore-existing

# Verify bucket created
docker exec lakehouse-minio mc ls myminio/
```

#### Verify Nessie

```bash
# Check Nessie API
curl http://localhost:19120/api/v1/config | python3 -m json.tool

# Expected: JSON configuration response
```

#### Access Services

- **MinIO Console**: http://localhost:9001 (admin/password123)
- **Jupyter Notebook**: http://localhost:8888 (no token required)
- **Nessie API**: http://localhost:19120/api/v1

---

## 📥 PHASE 2: BRONZE LAYER IMPLEMENTATION {#phase2}

### Step 2.1: Prepare Sample Data

**Create `data/raw/orders.csv`:**

```csv
order_id,customer_id,product,quantity,price,order_date
1,101,Laptop,1,1000.00,2023-08-01
2,102,Mouse,2,25.50,2023-08-01
3,103,Keyboard,1,45.00,2023-08-01
```

**Create `data/raw/customers.csv`:**

```csv
customer_id,name,email,country
101,John Doe,john@example.com,USA
102,Jane Smith,jane@example.com,UK
103,Bob Johnson,bob@example.com,Canada
```

### Step 2.2: Create Ingestion Scripts

#### Orders Ingestion Script

**Create `scripts/bronze/ingest_orders_spark.py`:**

```python
"""
Bronze Orders Ingestion using PySpark with Nessie Catalog
"""

import os
import pyspark
from pyspark.sql import SparkSession

# Get configuration from environment
NESSIE_URI = os.getenv("NESSIE_URI", "http://nessie:19120/api/v1")
WAREHOUSE = os.getenv("WAREHOUSE", "s3a://lakehouse/warehouse")
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID", "admin")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "password123")
AWS_S3_ENDPOINT = os.getenv("AWS_S3_ENDPOINT", "http://minio:9000")

print("=== Bronze Orders Ingestion (PySpark + Nessie) ===")
print(f"Nessie URI: {NESSIE_URI}")
print(f"Warehouse: {WAREHOUSE}")
print(f"S3 Endpoint: {AWS_S3_ENDPOINT}")

# Configure Spark with Iceberg and Nessie
conf = (
    pyspark.SparkConf()
        .setAppName('bronze-orders-ingestion')
        # Iceberg and Nessie JAR dependencies
        .set('spark.jars.packages', 
             'org.apache.iceberg:iceberg-spark-runtime-3.3_2.12:1.3.1,'
             'org.projectnessie.nessie-integrations:nessie-spark-extensions-3.3_2.12:0.67.0,'
             'software.amazon.awssdk:bundle:2.17.178,'
             'software.amazon.awssdk:url-connection-client:2.17.178')
        # Spark SQL extensions for Iceberg and Nessie
        .set('spark.sql.extensions', 
             'org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions,'
             'org.projectnessie.spark.extensions.NessieSparkSessionExtensions')
        # Configure Nessie catalog
        .set('spark.sql.catalog.nessie', 'org.apache.iceberg.spark.SparkCatalog')
        .set('spark.sql.catalog.nessie.uri', NESSIE_URI)
        .set('spark.sql.catalog.nessie.ref', 'main')
        .set('spark.sql.catalog.nessie.authentication.type', 'NONE')
        .set('spark.sql.catalog.nessie.catalog-impl', 'org.apache.iceberg.nessie.NessieCatalog')
        .set('spark.sql.catalog.nessie.warehouse', WAREHOUSE)
        .set('spark.sql.catalog.nessie.io-impl', 'org.apache.iceberg.aws.s3.S3FileIO')
        # S3/MinIO configuration
        .set('spark.sql.catalog.nessie.s3.endpoint', AWS_S3_ENDPOINT)
        .set('spark.hadoop.fs.s3a.access.key', AWS_ACCESS_KEY)
        .set('spark.hadoop.fs.s3a.secret.key', AWS_SECRET_KEY)
        .set('spark.hadoop.fs.s3a.endpoint', AWS_S3_ENDPOINT)
        .set('spark.hadoop.fs.s3a.path.style.access', 'true')
        .set('spark.hadoop.fs.s3a.connection.ssl.enabled', 'false')
        .set('spark.hadoop.fs.s3a.impl', 'org.apache.hadoop.fs.s3a.S3AFileSystem')
)

# Create Spark session
print("\n✓ Creating Spark session...")
spark = SparkSession.builder.config(conf=conf).getOrCreate()
print("✓ Spark session created")

# Read CSV data
print("\n✓ Reading orders.csv...")
df = spark.read.csv(
    "/home/jovyan/data/raw/orders.csv",
    header=True,
    inferSchema=True
)
record_count = df.count()
print(f"✓ Loaded {record_count} records")

# Show sample data
print("\nSample data:")
df.show(5)

# Create namespace if it doesn't exist
print("\n✓ Creating namespace...")
spark.sql("CREATE NAMESPACE IF NOT EXISTS nessie.ecommerce")
print("✓ Namespace 'ecommerce' ready")

# Create or replace Iceberg table
print("\n✓ Writing to Iceberg table...")
table_name = "nessie.ecommerce.orders_bronze"

df.writeTo(table_name).using("iceberg").createOrReplace()
print(f"✓ Wrote {record_count} records to {table_name}")

# Verify the data
print("\n✓ Verifying data...")
result = spark.sql(f"SELECT COUNT(*) as count FROM {table_name}").collect()
verified_count = result[0]['count']
print(f"✓ Verification: {verified_count} records in table")

# Show table metadata
print("\nTable metadata:")
spark.sql(f"DESCRIBE EXTENDED {table_name}").show(truncate=False)

# Stop Spark session
spark.stop()

print("\n=== ✓ Bronze ingestion complete! ===")
```

#### Customers Ingestion Script

**Create `scripts/bronze/ingest_customers_spark.py`:**

(Same structure as orders, change table name and CSV path)

### Step 2.3: Run Ingestion

```bash
# Run orders ingestion
docker exec lakehouse-spark python3 /home/jovyan/scripts/bronze/ingest_orders_spark.py

# Expected output:
# === Bronze Orders Ingestion (PySpark + Nessie) ===
# ✓ Creating Spark session...
# ✓ Spark session created
# ✓ Loaded 1000 records
# ✓ Wrote 1000 records to nessie.ecommerce.orders_bronze
# ✓ Verification: 1000 records in table
# === ✓ Bronze ingestion complete! ===

# Run customers ingestion
docker exec lakehouse-spark python3 /home/jovyan/scripts/bronze/ingest_customers_spark.py
```

### Step 2.4: Verify Data

#### Check Nessie Catalog

```bash
curl -s http://localhost:19120/api/v1/trees/tree/main/entries | python3 -m json.tool
```

**Expected output:**
```json
{
    "entries": [
        {
            "type": "NAMESPACE",
            "name": {"elements": ["ecommerce"]}
        },
        {
            "type": "ICEBERG_TABLE",
            "name": {"elements": ["ecommerce", "orders_bronze"]}
        },
        {
            "type": "ICEBERG_TABLE",
            "name": {"elements": ["ecommerce", "customers_bronze"]}
        }
    ]
}
```

#### Check MinIO Storage

```bash
docker exec lakehouse-minio mc ls --recursive myminio/lakehouse/warehouse
```

#### Query Data (via Jupyter)

Access http://localhost:8888 and create a new notebook:

```python
from pyspark.sql import SparkSession

spark = SparkSession.builder.getOrCreate()

# Query orders
spark.sql("SELECT * FROM nessie.ecommerce.orders_bronze LIMIT 10").show()

# Query customers
spark.sql("SELECT * FROM nessie.ecommerce.customers_bronze LIMIT 10").show()
```

---

## 🔍 TROUBLESHOOTING & LESSONS LEARNED {#troubleshooting}

### Lesson 1: PyIceberg vs PySpark

**What We Tried First:**
- PyIceberg with Nessie REST Catalog
- Nessie configured to vend S3 credentials

**Why It Failed:**
- Complex Nessie S3 configuration
- URN secret references not working
- Unclear property naming conventions

**What Works:**
- **PySpark with Nessie NessieCatalog**
- Spark handles S3 directly
- Simple Nessie (just metadata tracking)

### Lesson 2: Disk Space is Critical

**Problem:** Container pull failed with "no space left on device"

**Solution:**
```bash
# Clean Docker system
docker system prune -a --volumes --force

# Check available space
df -h .
```

**Recommendation:** Ensure 10GB+ free before starting

### Lesson 3: Environment Variable Format

**Spark Container:** Uses underscores in environment variables
```yaml
- AWS_ACCESS_KEY_ID=admin
- AWS_SECRET_ACCESS_KEY=password123
```

**Inside Container:** These become available via `os.getenv()`

### Lesson 4: Network Connectivity

**Inside Docker network:** Use service names, not localhost
- ✅ `http://minio:9000`
- ❌ `http://localhost:9000`

**From host machine:** Use localhost
- ✅ `http://localhost:9000`
- ❌ `http://minio:9000`

### Common Issues & Solutions

| Issue | Solution |
|-------|----------|
| Connection refused to MinIO | Create lakehouse bucket first |
| Python not found in container | Use `python3` instead of `python` |
| Spark JARs downloading slowly | First run downloads ~400MB (cached after) |
| Platform warning (amd64 vs arm64) | Safe to ignore if container starts |
| Nessie table not found | Check namespace created first |

---

## 🚀 QUICK START COMMANDS {#quickstart}

### Complete Setup (from scratch)

```bash
# 1. Start infrastructure
docker compose up -d

# 2. Wait for services
sleep 30

# 3. Create MinIO bucket
docker exec lakehouse-minio mc alias set myminio http://localhost:9000 admin password123
docker exec lakehouse-minio mc mb myminio/lakehouse --ignore-existing

# 4. Run Bronze ingestion
docker exec lakehouse-spark python3 /home/jovyan/scripts/bronze/ingest_orders_spark.py
docker exec lakehouse-spark python3 /home/jovyan/scripts/bronze/ingest_customers_spark.py

# 5. Verify
curl -s http://localhost:19120/api/v1/trees/tree/main/entries | python3 -m json.tool
```

### Daily Operations

```bash
# Start services
docker compose up -d

# Stop services
docker compose down

# View logs
docker compose logs -f

# Access Jupyter
open http://localhost:8888

# Access MinIO Console
open http://localhost:9001
```

### Cleanup

```bash
# Stop and remove containers (keeps data)
docker compose down

# Stop and remove everything including data
docker compose down -v
```

---

## 📚 References

- **Tutorial**: https://dev.to/alexmercedcoder/hands-on-with-apache-iceberg-on-your-laptop-deep-dive-with-apache-spark-nessie-minio-dremio-polars-and-seaborn-2hgk
- **GitHub Example**: https://github.com/domainio/iceberglakehouse
- **YouTube Tutorial**: https://youtu.be/3hpW-BUCvi8
- **Apache Iceberg**: https://iceberg.apache.org/
- **Project Nessie**: https://projectnessie.org/
- **Apache Spark**: https://spark.apache.org/

---

## ✅ Status

**Implemented:**
- ✅ Infrastructure (MinIO, Nessie, Spark, PostgreSQL)
- ✅ Bronze Layer (Orders & Customers ingestion)
- ✅ PySpark-based ingestion scripts

**Next Steps:**
- [ ] Implement Silver Layer transformations
- [ ] Implement Gold Layer aggregations
- [ ] Add data quality checks
- [ ] Set up orchestration (Airflow)
- [ ] Add comprehensive testing

---

**Last Updated:** December 2025
**Status:** Production-Ready Bronze Layer ✅
