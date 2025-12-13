# Quick Start - Run These Commands

**Complete pipeline from zero to working lakehouse in 5 minutes**

---

## Prerequisites

- Docker Desktop installed and running
- Git installed
- Python 3.x installed

---

## Step 1: Clone & Setup (30 seconds)

```bash
git clone https://github.com/Saadmomin2903/Version_Control_For_Databases.git
cd Version_Control_For_Databases
```

---

## Step 2: Start Services (1 minute)

```bash
# Start all Docker containers
docker compose up -d

# Wait for services to be ready
sleep 40

# Verify services are running
docker ps
```

Expected output: 4 containers running (minio, nessie, postgres, spark)

---

## Step 3: Create Branches (10 seconds)

```bash
# Create Nessie branches (bronze, silver, gold)
python3 scripts/utils/create_nessie_branches.py
```

Expected output:
```
✓ Created branch 'bronze'
✓ Created branch 'silver'
✓ Created branch 'gold'
```

---

## Step 4: Create Namespace on Silver Branch (30 seconds)

```bash
# This prevents namespace errors when writing to silver
docker exec lakehouse-spark python3 -c "
from pyspark.sql import SparkSession
import pyspark

conf = (pyspark.SparkConf()
    .setAppName('create-namespace')
    .set('spark.jars.packages', 'org.apache.iceberg:iceberg-spark-runtime-3.3_2.12:1.3.1,org.projectnessie.nessie-integrations:nessie-spark-extensions-3.3_2.12:0.67.0,software.amazon.awssdk:bundle:2.17.178,software.amazon.awssdk:url-connection-client:2.17.178')
    .set('spark.sql.extensions', 'org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions,org.projectnessie.spark.extensions.NessieSparkSessionExtensions')
    .set('spark.sql.catalog.nessie', 'org.apache.iceberg.spark.SparkCatalog')
    .set('spark.sql.catalog.nessie.uri', 'http://nessie:19120/api/v1')
    .set('spark.sql.catalog.nessie.ref', 'silver')
    .set('spark.sql.catalog.nessie.authentication.type', 'NONE')
    .set('spark.sql.catalog.nessie.catalog-impl', 'org.apache.iceberg.nessie.NessieCatalog')
    .set('spark.sql.catalog.nessie.warehouse', 's3a://lakehouse/warehouse')
    .set('spark.sql.catalog.nessie.io-impl', 'org.apache.iceberg.aws.s3.S3FileIO')
    .set('spark.sql.catalog.nessie.s3.endpoint', 'http://minio:9000')
    .set('spark.hadoop.fs.s3a.access.key', 'admin')
    .set('spark.hadoop.fs.s3a.secret.key', 'password123')
    .set('spark.hadoop.fs.s3a.endpoint', 'http://minio:9000')
    .set('spark.hadoop.fs.s3a.path.style.access', 'true')
    .set('spark.hadoop.fs.s3a.connection.ssl.enabled', 'false')
    .set('spark.hadoop.fs.s3a.impl', 'org.apache.hadoop.fs.s3a.S3AFileSystem'))

spark = SparkSession.builder.config(conf=conf).getOrCreate()
spark.sql('CREATE NAMESPACE IF NOT EXISTS nessie.ecommerce')
print('✓ Created namespace on silver branch')
spark.stop()
"
```

---

## Step 5: Bronze Layer - Ingest Raw Data (1 minute)

```bash
# Ingest orders (1000 records)
docker exec lakehouse-spark python3 /home/jovyan/scripts/bronze/ingest_orders_spark.py

# Ingest customers (200 records)
docker exec lakehouse-spark python3 /home/jovyan/scripts/bronze/ingest_customers_spark.py
```

Expected: "✓ Bronze ingestion complete!" for both

---

## Step 6: Silver Layer - Clean & Validate (1 minute)

```bash
# Transform orders (deduplication, quality scoring)
docker exec lakehouse-spark python3 /home/jovyan/scripts/silver/transform_orders_silver.py

# Transform customers (email validation, standardization)
docker exec lakehouse-spark python3 /home/jovyan/scripts/silver/transform_customers_silver.py
```

Expected: "✓ SILVER TRANSFORMATION COMPLETE!" with 100% quality checks passed

---

## Step 7: Gold Layer - Business Aggregations (1 minute)

```bash
# Create customer summary with metrics
docker exec lakehouse-spark python3 /home/jovyan/scripts/gold/aggregate_customer_summary_gold.py
```

Expected output:
```
✅ GOLD LAYER - CUSTOMER SUMMARY COMPLETE!
Total Revenue: $132,289.46
Active Customers: 151
```

---

## Step 8: Verify Complete Pipeline (5 seconds)

```bash
# Check all tables across branches
curl -s "http://localhost:19120/api/v1/trees/tree/bronze/entries" | python3 -c "import json, sys; tables = ['.'.join(e['name']['elements']) for e in json.load(sys.stdin)['entries'] if e['type']=='ICEBERG_TABLE']; print('Bronze:', len(tables), 'tables'); [print('  •', t) for t in tables]"

curl -s "http://localhost:19120/api/v1/trees/tree/silver/entries" | python3 -c "import json, sys; tables = ['.'.join(e['name']['elements']) for e in json.load(sys.stdin)['entries'] if e['type']=='ICEBERG_TABLE']; print('Silver:', len(tables), 'tables'); [print('  •', t) for t in tables]"

curl -s "http://localhost:19120/api/v1/trees/tree/main/entries" | python3 -c "import json, sys; tables = ['.'.join(e['name']['elements']) for e in json.load(sys.stdin)['entries'] if e['type']=='ICEBERG_TABLE']; print('Gold:', len(tables), 'tables'); [print('  •', t) for t in tables]"
```

Expected output:
```
Bronze: 2 tables
  • ecommerce.customers_bronze
  • ecommerce.orders_bronze
Silver: 2 tables
  • ecommerce.customers_silver
  • ecommerce.orders_silver
Gold: 1 tables
  • ecommerce.customer_summary
```

---

## ✅ Success! You Have:

- ✅ Bronze Layer: 1,200 raw records on `bronze` branch
- ✅ Silver Layer: 1,200 validated records on `silver` branch
- ✅ Gold Layer: 200 customer summaries on `main` branch
- ✅ Git-like version control working (branch isolation)
- ✅ Quality checks: 100% pass rate
- ✅ Persistent storage (PostgreSQL backend)

---

## 🔍 Optional: View Data in MinIO

1. Open browser: http://localhost:9001
2. Login: `admin` / `password123`
3. Browse bucket: `lakehouse/warehouse/ecommerce/`
4. See Parquet files for all tables

---

## 🔍 Optional: View Nessie Catalog

```bash
# List all branches
curl http://localhost:19120/api/v1/trees | python3 -m json.tool

# View specific branch
curl http://localhost:19120/api/v1/trees/tree/silver/entries | python3 -m json.tool
```

---

## 🧹 Cleanup (Optional)

```bash
# Stop and remove all containers
docker compose down

# Remove volumes (deletes all data)
docker compose down -v
```

---

## 🔄 Test Persistence (Optional)

```bash
# Restart Nessie to verify data persists
docker restart lakehouse-nessie
sleep 10

# Check branches still exist
curl http://localhost:19120/api/v1/trees | python3 -c "import json, sys; print([b['name'] for b in json.load(sys.stdin)['references']])"
```

Expected: `['bronze', 'gold', 'main', 'silver']` (data persisted!)

---

## 📊 What You Built

**Medallion Architecture:**
- Bronze: Raw data ingestion
- Silver: Data cleaning + quality checks
- Gold: Business-ready aggregations

**Key Features:**
- Git-like branching for data
- ACID transactions (Apache Iceberg)
- Quality validation framework
- Persistent catalog (survives restarts)
- S3-compatible storage (MinIO)

**Business Metrics:**
- 200 customers tracked
- 1,000 orders processed
- $132K+ total revenue
- Customer segmentation (Premium, Gold, Silver, Bronze)

---

## 🚀 Next Steps

1. **Explore Jupyter**: http://localhost:8888 (interactive queries)
2. **Read Documentation**: See `SETUP_GUIDE.md` for detailed explanations
3. **View Journey**: See `plan/complete_journey.md` for full story
4. **Customize**: Modify scripts for your own data

---

## 🐛 Troubleshooting

**Issue: "Nessie ref 'bronze' does not exist"**
```bash
python3 scripts/utils/create_nessie_branches.py
```

**Issue: Services not starting**
```bash
docker compose logs nessie
docker compose logs postgres
```

**Issue: "Namespace 'ecommerce' must exist"**
```bash
# Run Step 4 again (create namespace on silver branch)
```

**Issue: Out of disk space**
```bash
docker system prune -a --volumes --force
```

---

**Total Time: ~5 minutes**  
**Commands to Run: ~10**  
**Result: Complete working lakehouse with Git-like version control!**

---

*Last Updated: December 13, 2024*  
*Status: Production Ready ✅*
