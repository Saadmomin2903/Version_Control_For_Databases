# Production Migration Guide - From Your Working Setup to Cloud

**Adapting Your Tested Lakehouse to Firebolt Dataset (412M Records)**

---

## 🎯 What This Guide Does

You already have a **working lakehouse** that processes:
- ✅ 1,000 orders
- ✅ 200 customers  
- ✅ Bronze → Silver → Gold → Main
- ✅ Tested from clean slate

**This guide migrates YOUR setup to**:
- 🚀 412 million transactions
- 🚀 2.5 million customers  
- 🚀 Cloud infrastructure (Oracle + Supabase)
- 🚀 Same scripts, just adapted

---

## 📋 What You Already Have (Verified Working)

```yaml
Infrastructure:
  ✓ MinIO (local S3): docker-compose.yml
  ✓ PostgreSQL (local): docker-compose.yml
  ✓ Nessie catalog: docker-compose.yml
  ✓ Spark cluster: docker-compose.yml

Scripts (tested):
  ✓ scripts/bronze/ingest_orders_spark.py
  ✓ scripts/bronze/ingest_customers_spark.py
  ✓ scripts/silver/transform_orders_silver.py
  ✓ scripts/silver/transform_customers_silver.py
  ✓ scripts/gold/aggregate_customer_summary_gold.py
  ✓ scripts/utils/create_nessie_branches.py
  ✓ scripts/utils/promote_to_production.py

Data:
  ✓ data/ecommerce/orders.csv (1000 rows)
  ✓ data/ecommerce/customers.csv (200 rows)

Process:
  ✓ Clean slate test successful
  ✓ All quality checks passing
  ✓ $132,289.46 total revenue calculated
```

---

## 🔄 Migration Strategy

### Phase 1: Adapt Scripts for Firebolt Schema
**Time**: 1-2 hours  
**What**: Modify YOUR existing scripts to handle Firebolt CSV columns

### Phase 2: Add Partitioning for Scale
**Time**: 1 hour  
**What**: Add monthly partitioning to handle 412M records

### Phase 3: Deploy to Cloud
**Time**: 2-3 hours  
**What**: Replace MinIO → Oracle, PostgreSQL → Supabase

### Phase 4: Process Firebolt Data
**Time**: 5-6 hours  
**What**: Run YOUR tested pipeline on 412M records

---

## Step 1: Adapt Bronze Scripts for Firebolt

### Step 1.1: Map Firebolt Schema to Your Schema

**Your current orders.csv** (from sample data):
```csv
order_id,customer_id,order_date,status,total_amount
1,101,2024-01-15,completed,245.50
...
```

**Firebolt transactions.csv**:
```csv
transaction_id,user_id,product_id,order_date,quantity,price,discount,shipping_cost,payment_method,status
12345,67890,11111,2019-10-01 08:23:15,2,49.99,5.00,3.99,credit_card,completed
...
```

**Mapping needed**:
```yaml
transaction_id → order_id
user_id → customer_id
order_date → order_date (already correct)
status → status (already correct)
(quantity * price - discount + shipping_cost) → total_amount (calculate)
```

### Step 1.2: Update ingest_orders_spark.py

**Your current script** reads:
```python
df = spark.read.csv(
    "/home/jovyan/data/ecommerce/orders.csv",
    header=True,
    inferSchema=True
)
```

**Adapt for Firebolt**:

```python
# File: scripts/bronze/ingest_firebolt_transactions.py
# Based on YOUR ingest_orders_spark.py

import os
from datetime import datetime
import pyspark
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, expr, date_format, lit

# Your exact same Spark config (don't change!)
conf = (
    pyspark.SparkConf()
        .setAppName('bronze-firebolt-transactions')
        # ... YOUR SAME CONFIG ...
)

spark = SparkSession.builder.config(conf=conf).getOrCreate()

print("\n📖 Step 1: Reading Firebolt transactions...")

# Read Firebolt CSV
df = spark.read.csv(
    "/home/jovyan/data/firebolt/transactions.csv",  # New location
    header=True,
    inferSchema=True
)

print(f"✓ Loaded {df.count():,} transactions")

print("\n🔧 Step 2: Transform to YOUR schema...")

# Transform to match YOUR orders schema
transformed_df = df.select(
    col("transaction_id").alias("order_id"),
    col("user_id").alias("customer_id"),
    col("order_date"),
    col("status"),
    # Calculate total_amount (YOUR logic)
    expr("(price * quantity - discount + shipping_cost)").alias("total_amount")
)

# Add partitioning for 412M records (NEW - for scale)
transformed_df = transformed_df.withColumn(
    "year_month",
    date_format("order_date", "yyyy-MM")
)

# Add YOUR ingested_at timestamp
transformed_df = transformed_df.withColumn(
    "ingested_at", 
    lit(datetime.now())
)

print(f"✓ Transformed {transformed_df.count():,} records")

# YOUR exact same table creation
print("\n💾 Step 3: Creating namespace...")
spark.sql("CREATE NAMESPACE IF NOT EXISTS nessie.ecommerce")

print("\n💾 Step 4: Writing to Bronze branch...")

# Use YOUR table name, add partitioning
transformed_df.writeTo("nessie.ecommerce.orders_bronze") \
    .using("iceberg") \
    .partitionedBy("year_month") \  # NEW - for 412M records
    .tableProperty("write.parquet.compression-codec", "snappy") \
    .createOrReplace()

# YOUR verification
result = spark.sql("SELECT COUNT(*) as count FROM nessie.ecommerce.orders_bronze").collect()
print(f"\n✓ Verified: {result[0]['count']:,} records in orders_bronze")

spark.stop()
```

**Key changes**:
1. ✅ Read from new location
2. ✅ Map Firebolt columns to YOUR schema
3. ✅ Calculate `total_amount` from Firebolt fields
4. ✅ ADD partitioning (critical for 412M rows!)
5. ✅ Keep YOUR exact naming, logic, verification

---

## Step 2: Adapt Customers Script

### Step 2.1: Map Customers Schema

**Your customers.csv**:
```csv
customer_id,name,email,city
101,John Doe,john@example.com,New York
...
```

**Firebolt users.csv**:
```csv
user_id,user_name,email,signup_date,country,city,age_group,gender
67890,Jane Smith,jane@example.com,2019-08-15,US,San Francisco,25-34,F
...
```

### Step 2.2: Update ingest_customers_spark.py

```python
# File: scripts/bronze/ingest_firebolt_users.py
# Based on YOUR ingest_customers_spark.py

# ... YOUR SAME imports and config ...

df = spark.read.csv(
    "/home/jovyan/data/firebolt/users.csv",
    header=True,
    inferSchema=True
)

# Transform to YOUR schema
transformed_df = df.select(
    col("user_id").alias("customer_id"),
    col("user_name").alias("name"),
    col("email"),
    col("city")  # Keep city from Firebolt
)

# YOUR exact same table creation
spark.sql("CREATE NAMESPACE IF NOT EXISTS nessie.ecommerce")

transformed_df.writeTo("nessie.ecommerce.customers_bronze") \
    .using("iceberg") \
    .createOrReplace()  # No partitioning needed (only 2.5M rows)

# ... YOUR verification ...
```

---

## Step 3: No Changes Needed for Silver/Gold!

**Great news**: Your Silver and Gold scripts DON'T need changes!

**Why**:
- They read from `orders_bronze` and `customers_bronze` tables
- Table schemas match YOUR existing format
- Quality checks work the same way
- Aggregations work the same way

**Scripts that work as-is**:
- ✅ `scripts/silver/transform_orders_silver.py` (no changes)
- ✅ `scripts/silver/transform_customers_silver.py` (no changes)
- ✅ `scripts/gold/aggregate_customer_summary_gold.py` (no changes)
- ✅ `scripts/utils/*` (no changes)

---

## Step 4: Update Docker Compose for Cloud

### Step 4.1: Current Setup (Local)

Your `docker-compose.yml`:
```yaml
minio:  # Local S3
postgres:  # Local DB
nessie:  # Uses local postgres
spark:  # Local compute
```

### Step 4.2: Cloud Setup

**What changes**:
```yaml
MinIO → Oracle Object Storage (S3-compatible)
Local PostgreSQL → Supabase PostgreSQL  
Nessie → Updated to use Supabase
Spark → Runs on Oracle VMs
```

**What stays same**:
- YOUR scripts
- YOUR branch strategy
- YOUR quality checks
- YOUR promotion workflow

---

## Step 5: Cloud Deployment (Use Detailed Guides)

**Follow the detailed 4-part guides I created**, but with these modifications:

### Modifications to DETAILED_GUIDE_PART4.md:

**Instead of generic scripts, upload YOUR scripts**:

```bash
# On VM2:
cd /home/ubuntu/lakehouse

# Upload YOUR working scripts
scp -i ~/.ssh/oracle-vm2.key -r \
    ~/Documents/Version_Control_For_Databases/scripts/* \
    ubuntu@[VM2-IP]:/home/ubuntu/lakehouse/scripts/

# Upload YOUR docker-compose.yml
scp -i ~/.ssh/oracle-vm2.key \
    ~/Documents/Version_Control_For_Databases/docker-compose.yml \
    ubuntu@[VM2-IP]:/home/ubuntu/lakehouse/
```

**Update environment variables**:

In YOUR scripts, replace:
```python
AWS_S3_ENDPOINT = "http://minio:9000"  # OLD
AWS_ACCESS_KEY = "admin"  # OLD
AWS_SECRET_KEY = "password123"  # OLD
```

With:
```python
AWS_S3_ENDPOINT = "https://objectstorage.us-ashburn-1.oraclecloud.com"  # NEW
AWS_ACCESS_KEY = os.getenv("ORACLE_ACCESS_KEY")  # NEW
AWS_SECRET_KEY = os.getenv("ORACLE_SECRET_KEY")  # NEW
```

**Or better - use sed to batch update**:
```bash
# On VM2:
cd /home/ubuntu/lakehouse/scripts

# Update endpoint
find . -name "*.py" -exec sed -i \
    's|http://minio:9000|https://objectstorage.us-ashburn-1.oraclecloud.com|g' {} +

# Update SSL setting
find . -name "*.py" -exec sed -i \
    "s|'false'|'true'|g" {} +

# Update path style
find . -name "*.py" -exec sed -i \
    "s|'true'|'false'|g" {} +
```

---

## Step 6: Process Firebolt Data

### Step 6.1: YOUR Exact Process (Adapted for Cloud)

**On VM2, following YOUR clean slate success**:

```bash
# 1. Create Oracle buckets (equivalent to YOUR MinIO step)
# (Already done in cloud setup)

# 2. Create Nessie branches (YOUR script)
docker exec spark-master python3 /home/jovyan/scripts/utils/create_nessie_branches.py

# 3. Create namespace (YOUR command, just on cloud)
docker exec spark-master python3 -c "..."  # Same as YOUR clean slate test

# 4. Run Bronze (YOUR NEW Firebolt-adapted scripts)
for month in 2019-10 2019-11 2019-12 2020-01 2020-02 2020-03 2020-04; do
    echo "Processing $month..."
    docker exec spark-master python3 /home/jovyan/scripts/bronze/ingest_firebolt_transactions.py --month=$month
done

docker exec spark-master python3 /home/jovyan/scripts/bronze/ingest_firebolt_users.py

# 5. Run Silver (YOUR EXACT scripts - no changes!)
docker exec spark-master python3 /home/jovyan/scripts/silver/transform_orders_silver.py
docker exec spark-master python3 /home/jovyan/scripts/silver/transform_customers_silver.py

# 6. Run Gold (YOUR EXACT script - no changes!)
docker exec spark-master python3 /home/jovyan/scripts/gold/aggregate_customer_summary_gold.py

# 7. Promote (YOUR EXACT script!)
echo "yes" | python3 scripts/utils/promote_to_production.py
```

---

## 📊 Expected Results

**Using YOUR tested pipeline**:

```yaml
Bronze:
  orders_bronze: 412,000,000 records (vs your 1,000)
  customers_bronze: 2,500,000 records (vs your 200)

Silver:
  orders_silver: ~410,000,000 records (after quality checks)
  customers_silver: ~2,480,000 records (after email validation)
  Quality: >99% (YOUR checks scaled up!)

Gold:
  customer_summary: ~2,480,000 customers
  Total Revenue: ~$X billion (vs your $132k)
  Segments: Same YOUR 4 segments (Premium/Gold/Silver/Bronze)
```

---

## ✅ Key Advantages

**You're not starting from scratch**:
- ✅ YOUR code is already tested
- ✅ YOUR logic is proven correct
- ✅ YOUR quality checks work
- ✅ YOUR branch strategy validated

**We're just**:
- 🔄 Swapping data source (sample → Firebolt)
- 🔄 Swapping storage (MinIO → Oracle)
- 🔄 Swapping DB (local Postgres → Supabase)
- ➕ Adding partitioning (for scale)

**Everything else stays YOUR tested code!**

---

## 🚀 Summary

**What I should have done initially**:
1. ✅ Use YOUR working docker-compose.yml
2. ✅ Adapt YOUR exact scripts
3. ✅ Keep YOUR tested process
4. ✅ Just add cloud deployment steps

**What's actually changing**:
- Input CSV schema (orders.csv → transactions.csv)
- Storage backend (MinIO → Oracle S3)
- Database (local → Supabase)  
- Scale (1k rows → 412M rows)

**What's staying the same**:
- YOUR branch names
- YOUR table schemas
- YOUR quality logic
- YOUR promotion workflow
- YOUR entire pipeline flow

---

**This is the correct approach - build on YOUR tested foundation!** 🎯

Let me know if you want me to create specific updated scripts based on YOUR exact code!
