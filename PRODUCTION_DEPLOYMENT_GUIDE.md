# Production Deployment Guide - Brazilian E-Commerce Dataset

**Complete Step-by-Step Guide from Local to Production Cloud**

---

## 📚 Table of Contents

- [Overview](#overview)
- [Phase 1: Dataset Preparation (Local)](#phase-1-dataset-preparation-local)
- [Phase 2: Oracle Cloud Account Setup](#phase-2-oracle-cloud-account-setup)
- [Phase 3: Supabase Setup](#phase-3-supabase-setup)
- [Phase 4: VM1 Deployment (Airflow + Nessie)](#phase-4-vm1-deployment-airflow--nessie)
- [Phase 5: VM2 Deployment (Spark)](#phase-5-vm2-deployment-spark)
- [Phase 6: Data Migration](#phase-6-data-migration)
- [Phase 7: Production Pipeline Testing](#phase-7-production-pipeline-testing)
- [Phase 8: Monitoring Setup](#phase-8-monitoring-setup)
- [Appendix: Troubleshooting](#appendix-troubleshooting)

---

## Overview

**What You'll Build**:
- Production lakehouse processing 100k+ real e-commerce orders
- Zero-cost cloud infrastructure ($0/month)
- Automated orchestration with Airflow
- Full monitoring with Grafana

**Timeline**: ~3 weeks (1-2 hours/day)

**Prerequisites**:
- Your current local setup (working)
- Gmail account (for Oracle, Supabase, Grafana)
- GitHub account
- Credit card (for verification only, $0 charged)

---

## Phase 1: Dataset Preparation (Local)

**Time**: 2-3 hours  
**Goal**: Download, explore, and adapt scripts for Brazilian E-Commerce dataset

### Step 1.1: Download Dataset

```bash
# Create dataset directory
cd ~/Documents/Version_Control_For_Databases
mkdir -p data/brazilian-ecommerce
cd data/brazilian-ecommerce

# Download from Kaggle (requires Kaggle account)
# Option A: Manual download
# 1. Go to: https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce
# 2. Click "Download" (requires Kaggle login)
# 3. Extract to data/brazilian-ecommerce/

# Option B: Using Kaggle CLI (recommended)
pip install kaggle

# Setup Kaggle credentials
# 1. Go to: https://www.kaggle.com/settings
# 2. Click "Create New API Token"
# 3. Save kaggle.json to ~/.kaggle/

mkdir -p ~/.kaggle
# Copy your downloaded kaggle.json to ~/.kaggle/
chmod 600 ~/.kaggle/kaggle.json

# Download dataset
kaggle datasets download -d olistbr/brazilian-ecommerce --unzip -p .

# Verify files
ls -lh
```

**Expected Files**:
```
olist_customers_dataset.csv          (99,441 rows)
olist_orders_dataset.csv             (99,441 rows)
olist_order_items_dataset.csv        (112,650 rows)
olist_order_payments_dataset.csv     (103,886 rows)
olist_order_reviews_dataset.csv      (99,224 rows)
olist_products_dataset.csv           (32,951 rows)
olist_sellers_dataset.csv            (3,095 rows)
olist_geolocation_dataset.csv        (1,000,163 rows)
product_category_name_translation.csv (71 rows)
```

### Step 1.2: Explore Dataset Schema

```bash
# Quick exploration
head -5 olist_orders_dataset.csv
head -5 olist_customers_dataset.csv
head -5 olist_order_items_dataset.csv

# Count records
wc -l *.csv
```

**Key Tables**:

**Orders** (`olist_orders_dataset.csv`):
```csv
order_id,customer_id,order_status,order_purchase_timestamp,order_approved_at,order_delivered_carrier_date,order_delivered_customer_date,order_estimated_delivery_date
e481f51cbdc54678b7cc49136f2d6af7,9ef432eb6251297304e76186b10a928d,delivered,2017-10-02 10:56:33,2017-10-02 11:07:15,2017-10-04 19:55:00,2017-10-10 21:25:13,2017-10-18 00:00:00
```

**Customers** (`olist_customers_dataset.csv`):
```csv
customer_id,customer_unique_id,customer_zip_code_prefix,customer_city,customer_state
06b8999e2fba1a1fbc88172c00ba8bc7,861eff4711a542e4b93843c6dd7febb0,14409,franca,SP
```

**Order Items** (`olist_order_items_dataset.csv`):
```csv
order_id,order_item_id,product_id,seller_id,shipping_limit_date,price,freight_value
00010242fe8c5a6d1ba2dd792cb16214,1,4244733e06e7ecb4970a6e2683c13e61,48436dade18ac8b2bce089ec2a041202,2017-09-19 09:45:35,58.90,13.29
```

### Step 1.3: Create Schema Mapping Document

Create `data/brazilian-ecommerce/SCHEMA_MAPPING.md`:

```bash
cat > data/brazilian-ecommerce/SCHEMA_MAPPING.md << 'EOF'
# Brazilian E-Commerce Schema Mapping

## Current Schema → New Schema

### Orders Table
| Brazilian E-Commerce | Our Current Schema | Transformation |
|---------------------|-------------------|----------------|
| order_id | order_id | Direct mapping |
| customer_id | customer_id | Direct mapping |
| order_purchase_timestamp | order_date | Convert to date |
| order_status | status | Direct mapping |
| (calculated from items) | total_amount | SUM(price + freight_value) |

### Customers Table
| Brazilian E-Commerce | Our Current Schema | Transformation |
|---------------------|-------------------|----------------|
| customer_unique_id | customer_id | Direct mapping |
| customer_id | (ignore) | Order-specific ID |
| customer_city | name | Use city as placeholder |
| customer_state | (new field) | Add state column |
| customer_zip_code_prefix | (new field) | Add zip column |

### New Fields to Add
- customer_state (string)
- customer_city (string)
- customer_zip_code (int)
- order_delivered_date (timestamp)
- order_estimated_delivery_date (timestamp)
- shipping_cost (decimal)
EOF
```

### Step 1.4: Adapt Bronze Scripts for New Schema

**Create new ingestion script** for orders:

```bash
cat > scripts/bronze/ingest_brazilian_orders.py << 'EOF'
#!/usr/bin/env python3
"""
Bronze Layer - Brazilian E-Commerce Orders Ingestion
Reads raw CSV from Olist dataset and writes to Iceberg on bronze branch
"""

import os
import sys
from datetime import datetime
import pyspark
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, to_timestamp, lit

# Environment variables
NESSIE_URI = os.getenv("NESSIE_URI", "http://nessie:19120/api/v1")
WAREHOUSE = os.getenv("WAREHOUSE", "s3a://lakehouse/warehouse")
AWS_S3_ENDPOINT = os.getenv("AWS_S3_ENDPOINT", "http://minio:9000")
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID", "admin")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "password123")

print("=" * 70)
print("BRONZE LAYER - BRAZILIAN E-COMMERCE ORDERS INGESTION")
print("=" * 70)

# Spark configuration
conf = (
    pyspark.SparkConf()
        .setAppName('bronze-brazilian-orders')
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
        .set('spark.hadoop.fs.s3a.impl', 'org.apache.hadoop.fs.s3a.S3AFileSystem'))

spark = SparkSession.builder.config(conf=conf).getOrCreate()

print("\n📖 Step 1: Reading Brazilian orders CSV...")

# Read orders
orders_df = spark.read.csv(
    "/home/jovyan/data/brazilian-ecommerce/olist_orders_dataset.csv",
    header=True,
    inferSchema=True
)

# Read order items (to get total amount)
items_df = spark.read.csv(
    "/home/jovyan/data/brazilian-ecommerce/olist_order_items_dataset.csv",
    header=True,
    inferSchema=True
)

print(f"✓ Loaded {orders_df.count():,} orders")
print(f"✓ Loaded {items_df.count():,} order items")

print("\n🔧 Step 2: Transforming to match our schema...")

# Calculate total amount per order
from pyspark.sql.functions import sum as _sum
order_totals = items_df.groupBy("order_id").agg(
    _sum(col("price") + col("freight_value")).alias("total_amount")
)

# Join and transform
bronze_df = orders_df.join(order_totals, "order_id", "left") \
    .select(
        col("order_id"),
        col("customer_id"),
        to_timestamp("order_purchase_timestamp").alias("order_date"),
        col("order_status").alias("status"),
        col("total_amount"),
        to_timestamp("order_delivered_customer_date").alias("delivered_date"),
        to_timestamp("order_estimated_delivery_date").alias("estimated_delivery_date")
    )

# Add metadata
bronze_df = bronze_df.withColumn("ingested_at", lit(datetime.now()))
bronze_df = bronze_df.withColumn("source", lit("olist_brazilian_ecommerce"))

print(f"✓ Transformed {bronze_df.count():,} records")

print("\n💾 Step 3: Creating namespace...")
spark.sql("CREATE NAMESPACE IF NOT EXISTS nessie.ecommerce")
print("✓ Namespace verified")

print("\n💾 Step 4: Writing to Bronze branch...")
table_name = "nessie.ecommerce.orders_bronze"

bronze_df.writeTo(table_name).using("iceberg").createOrReplace()
print(f"✓ Table created: {table_name}")

# Verify
result = spark.sql(f"SELECT COUNT(*) as count FROM {table_name}").collect()
count = result[0]['count']

print(f"\n✓ Verified: {count:,} records in orders_bronze")

print("\n" + "=" * 70)
print("✅ BRONZE INGESTION COMPLETE")
print("=" * 70)
print(f"\nSummary:")
print(f"  📥 Input:  {orders_df.count():,} orders from CSV")
print(f"  📤 Output: {count:,} records in bronze branch")
print(f"  🗄️  Table:  {table_name}")
print("=" * 70)

spark.stop()
EOF

chmod +x scripts/bronze/ingest_brazilian_orders.py
```

**Create customers ingestion**:

```bash
cat > scripts/bronze/ingest_brazilian_customers.py << 'EOF'
#!/usr/bin/env python3
"""
Bronze Layer - Brazilian E-Commerce Customers Ingestion
"""

import os
import sys
from datetime import datetime
import pyspark
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, lit, concat_ws, coalesce

# Environment variables (same as before)
NESSIE_URI = os.getenv("NESSIE_URI", "http://nessie:19120/api/v1")
WAREHOUSE = os.getenv("WAREHOUSE", "s3a://lakehouse/warehouse")
AWS_S3_ENDPOINT = os.getenv("AWS_S3_ENDPOINT", "http://minio:9000")
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID", "admin")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "password123")

print("=" * 70)
print("BRONZE LAYER - BRAZILIAN E-COMMERCE CUSTOMERS INGESTION")
print("=" * 70)

# Spark config (same as orders script)
conf = (
    pyspark.SparkConf()
        .setAppName('bronze-brazilian-customers')
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
        .set('spark.hadoop.fs.s3a.impl', 'org.apache.hadoop.fs.s3a.S3AFileSystem'))

spark = SparkSession.builder.config(conf=conf).getOrCreate()

print("\n📖 Step 1: Reading Brazilian customers CSV...")

customers_df = spark.read.csv(
    "/home/jovyan/data/brazilian-ecommerce/olist_customers_dataset.csv",
    header=True,
    inferSchema=True
)

print(f"✓ Loaded {customers_df.count():,} customers")

print("\n🔧 Step 2: Transforming to match our schema...")

# Transform to our schema
bronze_df = customers_df.select(
    col("customer_unique_id").alias("customer_id"),
    concat_ws(", ", col("customer_city"), col("customer_state")).alias("name"),
    coalesce(col("customer_zip_code_prefix"), lit(0)).alias("zip_code"),
    col("customer_city"),
    col("customer_state"),
    lit(True).alias("is_active")  # Assume all active
)

# Add metadata
bronze_df = bronze_df.withColumn("ingested_at", lit(datetime.now()))
bronze_df = bronze_df.withColumn("source", lit("olist_brazilian_ecommerce"))

print(f"✓ Transformed {bronze_df.count():,} records")

print("\n💾 Step 3: Creating namespace...")
spark.sql("CREATE NAMESPACE IF NOT EXISTS nessie.ecommerce")
print("✓ Namespace verified")

print("\n💾 Step 4: Writing to Bronze branch...")
table_name = "nessie.ecommerce.customers_bronze"

bronze_df.writeTo(table_name).using("iceberg").createOrReplace()
print(f"✓ Table created: {table_name}")

# Verify
result = spark.sql(f"SELECT COUNT(*) as count FROM {table_name}").collect()
count = result[0]['count']

print(f"\n✓ Verified: {count:,} records in customers_bronze")

print("\n" + "=" * 70)
print("✅ BRONZE INGESTION COMPLETE")
print("=" * 70)
print(f"\nSummary:")
print(f"  📥 Input:  {customers_df.count():,} customers from CSV")
print(f"  📤 Output: {count:,} records in bronze branch")
print(f"  🗄️  Table:  {table_name}")
print("=" * 70)

spark.stop()
EOF

chmod +x scripts/bronze/ingest_brazilian_customers.py
```

### Step 1.5: Test Locally with Sample Data

```bash
# Create sample (first 1000 rows for testing)
head -1001 data/brazilian-ecommerce/olist_orders_dataset.csv > data/brazilian-ecommerce/sample_orders.csv
head -1001 data/brazilian-ecommerce/olist_order_items_dataset.csv > data/brazilian-ecommerce/sample_items.csv
head -1001 data/brazilian-ecommerce/olist_customers_dataset.csv > data/brazilian-ecommerce/sample_customers.csv

# Update scripts to use sample data temporarily
# (modify the CSV paths in the scripts above to point to sample_*.csv)

# Test ingestion
docker exec lakehouse-spark python3 /home/jovyan/scripts/bronze/ingest_brazilian_orders.py
docker exec lakehouse-spark python3 /home/jovyan/scripts/bronze/ingest_brazilian_customers.py

# Verify
curl -s "http://localhost:19120/api/v1/trees/tree/bronze/entries" | \
  python3 -c "import json, sys; print('Bronze tables:', [e['name']['elements'] for e in json.load(sys.stdin)['entries']])"
```

**✅ Phase 1 Complete!** You now have:
- Brazilian E-Commerce dataset downloaded
- Schema mapped to your existing structure
- New ingestion scripts created and tested locally

---

## Phase 2: Oracle Cloud Account Setup

**Time**: 1-2 hours  
**Goal**: Create Oracle Cloud account and provision free resources

### Step 2.1: Create Oracle Cloud Account

```bash
# 1. Go to Oracle Cloud Free Tier signup
open https://www.oracle.com/cloud/free/

# 2. Click "Start for free"
# 3. Fill out form:
#    - Country: [Your country]
#    - Cloud Account Name: lakehouse-prod (or any unique name)
#    - Home Region: Choose closest (e.g., US East - Ashburn)
#    - Email: your-email@gmail.com
```

**Important**:
- ⚠️ Requires credit card for verification (no charge)
- ✅ Always Free resources never expire
- 📧 Verification email arrives in 2-3 minutes

**After verification**:
```
1. Check email for "Welcome to Oracle Cloud"
2. Click activation link
3. Set password (save in password manager!)
4. Complete phone verification
5. Login to Oracle Cloud Console
```

### Step 2.2: Create Virtual Cloud Network (VCN)

```bash
# In Oracle Cloud Console:
# 1. Click ≡ menu → Networking → Virtual Cloud Networks
# 2. Select your Compartment (typically "root" or your name)
# 3. Click "Start VCN Wizard"
```

**VCN Wizard Settings**:
```yaml
Configuration:
  - Select: "Create VCN with Internet Connectivity"
  - Click "Start VCN Wizard"

Basic Information:
  VCN Name: lakehouse-vcn
  Compartment: [root]
  
VCN CIDR Blocks:
  VCN CIDR Block: 10.0.0.0/16
  
Subnets:
  Public Subnet CIDR: 10.0.0.0/24
  Private Subnet CIDR: 10.0.1.0/24
  
DNS:
  Use DNS hostnames: ✓ checked
```

**Click "Next" → "Create"** (takes ~30 seconds)

### Step 2.3: Create Security List Rules

```bash
# After VCN created:
# Click "View VCN" → Security Lists → "Default Security List"
# Click "Add Ingress Rules"
```

**Add the following ingress rules**:

**Rule 1: SSH**
```yaml
Source CIDR: 0.0.0.0/0
IP Protocol: TCP
Destination Port: 22
Description: SSH access
```

**Rule 2: Airflow**
```yaml
Source CIDR: 0.0.0.0/0
IP Protocol: TCP
Destination Port: 8080
Description: Airflow Web UI
```

**Rule 3: Nessie**
```yaml
Source CIDR: 0.0.0.0/0
IP Protocol: TCP
Destination Port: 19120
Description: Nessie API
```

**Rule 4: Spark UI**
```yaml
Source CIDR: 0.0.0.0/0
IP Protocol: TCP
Destination Port: 8081
Description: Spark Master UI
```

**Rule 5: Jupyter**
```yaml
Source CIDR: 0.0.0.0/0
IP Protocol: TCP
Destination Port: 8888
Description: Jupyter Notebook
```

**Click "Add Ingress Rules"** for each

### Step 2.4: Create VM1 (Airflow + Nessie)

```bash
# Oracle Console: ≡ → Compute → Instances → Create Instance
```

**VM1 Configuration**:
```yaml
Name: airflow-nessie

Placement:
  Availability Domain: AD-1 (or any available)
  
Image and Shape:
  Image: Canonical Ubuntu 22.04 (ARM64)
  Shape: VM.Standard.A1.Flex
    OCPU: 2
    Memory: 12 GB
  
Networking:
  VCN: lakehouse-vcn
  Subnet: Public Subnet
  Assign public IP: YES
  
Add SSH Keys:
  ✓ Generate a key pair for me
  [Click "Save Private Key" - IMPORTANT!]
  [Save as: ~/.ssh/oracle-vm1.key]

Boot Volume:
  Size: 50 GB
  
Advanced Options:
  Cloud-init script: [leave empty for now]
```

**Click "Create"** (takes 1-2 minutes)

**Save the credentials**:
```bash
# After VM created, note down:
Public IP: [copy from console]
Private IP: [copy from console]
Username: ubuntu

# Set permissions on SSH key
chmod 600 ~/.ssh/oracle-vm1.key

# Test SSH
ssh -i ~/.ssh/oracle-vm1.key ubuntu@[PUBLIC-IP]
```

### Step 2.5: Create VM2 (Spark Cluster)

**Repeat Step 2.4 with these changes**:
```yaml
Name: spark-cluster

Shape: VM.Standard.A1.Flex
  OCPU: 2
  Memory: 12 GB
  
SSH Keys:
  [Generate new key pair]
  [Save as: ~/.ssh/oracle-vm2.key]
```

**Save credentials**:
```bash
chmod 600 ~/.ssh/oracle-vm2.key

# Test SSH
ssh -i ~/.ssh/oracle-vm2.key ubuntu@[VM2-PUBLIC-IP]
```

### Step 2.6: Create Object Storage Bucket

```bash
# Oracle Console: ≡ → Storage → Buckets → Create Bucket
```

**Bucket Settings**:
```yaml
Bucket Name: lakehouse-prod
Compartment: [root]
Tier: Standard
Enable Object Versioning: ✓
Enable Auto-Tiering: ✗ (keep unchecked)
Encryption: Encrypt using Oracle-managed keys
```

**Click "Create"**

### Step 2.7: Generate S3-Compatible API Keys

```bash
# Oracle Console: Click Profile Icon (top right) → User Settings
# Scroll to "Customer Secret Keys" → "Generate Secret Key"
```

**Create Key**:
```yaml
Name: lakehouse-s3-access
[Click "Generate Secret Key"]
```

**⚠️ CRITICAL - Copy immediately (shown only once!)**:
```bash
Access Key: [copy - looks like: 1234567890abcdef...]
Secret Key: [copy - looks like: XyZ123...]
```

**Save to file**:
```bash
cat > ~/oracle-credentials.txt << EOF
ORACLE_ACCESS_KEY=[paste access key]
ORACLE_SECRET_KEY=[paste secret key]
ORACLE_NAMESPACE=[your namespace - shown in bucket details]
ORACLE_REGION=us-ashburn-1
ORACLE_ENDPOINT=https://objectstorage.us-ashburn-1.oraclecloud.com
EOF

chmod 600 ~/oracle-credentials.txt
```

**✅ Phase 2 Complete!** You now have:
- Oracle Cloud account created
- 2 VMs running (Airflow + Spark)
- Object storage bucket ready
- S3-compatible credentials

---

## Phase 3: Supabase Setup

**Time**: 15-20 minutes  
**Goal**: Create PostgreSQL database for Nessie metadata

### Step 3.1: Create Supabase Account

```bash
# Open Supabase
open https://supabase.com/

# Click "Start your project"
# Sign up with GitHub or email
```

### Step 3.2: Create Project

**Project Settings**:
```yaml
Organization: [Create new] "Lakehouse Production"
Project Name: nessie-metadata
Database Password: [Generate strong password - SAVE IT!]
Region: East US (closest to Oracle US-Ashburn)
Pricing Plan: Free
```

**Click "Create new project"** (takes ~2 minutes)

### Step 3.3: Get Connection Details

```bash
# After project created:
# Click "Settings" (⚙️ icon) → "Database"
```

**Copy these values**:
```bash
cat > ~/supabase-credentials.txt << EOF
SUPABASE_HOST=db.xxxxxxxxxxxxx.supabase.co
SUPABASE_PORT=5432
SUPABASE_DATABASE=postgres
SUPABASE_USER=postgres
SUPABASE_PASSWORD=[your password]
SUPABASE_CONNECTION_STRING=postgresql://postgres:[password]@db.xxxxx.supabase.co:5432/postgres?sslmode=require
EOF

chmod 600 ~/supabase-credentials.txt
```

### Step 3.4: Test Connection

```bash
# Install PostgreSQL client (if not installed)
brew install postgresql@15  # macOS
# or
sudo apt install postgresql-client  # Ubuntu/Linux

# Test connection
psql "postgresql://postgres:[password]@db.xxxxx.supabase.co:5432/postgres?sslmode=require"

# Should see:
# postgres=>
```

**Run test query**:
```sql
\l  -- List databases
\dt -- List tables (empty for now)
\q  -- Quit
```

**✅ Phase 3 Complete!** You now have:
- Supabase PostgreSQL database
- Connection credentials saved
- Connection tested successfully

---

*[Continue to Phase 4 in next file due to length...]*

**📝 Status**: Phases 1-3 documented (Dataset + Oracle + Supabase)  
**⏭️ Next**: Phase 4-8 (VM deployment, migration, testing, monitoring)

Would you like me to continue with Phases 4-8 in a second document?
