# 🎯 Project Demo Guide: Database Version Control with Data Lakehouse

## Quick Start Commands

### Prerequisites
- SSH access to VM1: `ssh -i ~/.ssh/oracle-vm1.key ubuntu@140.238.224.207`
- All services running (check with commands below)

---

## 🔍 1. Check System Status (30 seconds)

```bash
# SSH into VM1 and check all services
ssh -i ~/.ssh/oracle-vm1.key ubuntu@140.238.224.207 "docker ps --format 'table {{.Names}}\t{{.Status}}'"
```

**Expected Output:**
```
NAMES                STATUS
lakehouse-spark      Up X hours (healthy)
airflow-webserver    Up X hours
airflow-scheduler    Up X hours
nessie               Up X hours
airflow-postgres     Up X hours
```

---

## 🏗️ 2. The Medallion Architecture (2 minutes)

### Show the Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    MEDALLION ARCHITECTURE                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  RAW DATA        BRONZE           SILVER           GOLD         │
│  (Parquet)   →   (Iceberg)    →   (Iceberg)    →   (Iceberg)   │
│                                                                  │
│  411M rows       Ingested         Cleaned          Aggregated   │
│  E-commerce      Raw events       Deduped          Analytics    │
│  Events                           Typed                         │
│                                                                  │
│  ─────────── VERSION CONTROLLED BY NESSIE ───────────          │
│                                                                  │
│            main ←─── silver ←─── bronze ←─── gold              │
│           (prod)    (staging)   (source)   (analytics)         │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🚀 3. Run the Pipeline (5 minutes)

### Option A: Manual Step-by-Step

```bash
# Step 1: Silver Layer Transform
ssh -i ~/.ssh/oracle-vm1.key ubuntu@140.238.224.207 \
  "docker exec lakehouse-spark python3 /home/jovyan/scripts/silver/transform_orders_silver.py"
```

**Expected Output:**
```
✅ Total Records Written: 3,138,325
✓ Verified Table Count: 3,138,325
```

```bash
# Step 2: Gold Layer Aggregations  
ssh -i ~/.ssh/oracle-vm1.key ubuntu@140.238.224.207 \
  "docker exec lakehouse-spark python3 /home/jovyan/scripts/gold/build_gold_layer.py"
```

**Expected Output:**
```
[1/4] Building: daily_sales_gold ✅ Done.
[2/4] Building: brand_performance_gold ✅ Done.
[3/4] Building: customer_stats_gold ✅ Done.
[4/4] Building: category_stats_gold ✅ Done.
✨ GOLD LAYER BUILD COMPLETE
```

### Option B: Airflow DAG (Automated)

1. Open Airflow UI: http://140.238.224.207:8080
2. Login: `admin` / `admin`
3. Find DAG: `medallion_pipeline`
4. Click "Trigger DAG" ▶️

---

## 🔄 4. Demo: Version Control Features (3 minutes)

### 4.1 Show All Branches
```bash
ssh -i ~/.ssh/oracle-vm1.key ubuntu@140.238.224.207 "docker exec lakehouse-spark python3 -c \"
from pyspark.sql import SparkSession
spark = SparkSession.builder.appName('demo').config('spark.jars.packages','org.apache.iceberg:iceberg-spark-runtime-3.3_2.12:1.3.1,org.projectnessie.nessie-integrations:nessie-spark-extensions-3.3_2.12:0.67.0').config('spark.sql.extensions','org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions,org.projectnessie.spark.extensions.NessieSparkSessionExtensions').config('spark.sql.catalog.nessie','org.apache.iceberg.spark.SparkCatalog').config('spark.sql.catalog.nessie.uri','http://172.18.0.2:19120/api/v1').config('spark.sql.catalog.nessie.catalog-impl','org.apache.iceberg.nessie.NessieCatalog').getOrCreate()
spark.sql('LIST REFERENCES IN nessie').show()
spark.stop()
\""
```

### 4.2 Query Specific Branch
```bash
# Query Gold table on 'gold' branch
ssh -i ~/.ssh/oracle-vm1.key ubuntu@140.238.224.207 "docker exec lakehouse-spark python3 -c \"
from pyspark.sql import SparkSession
spark = SparkSession.builder.appName('demo') \
    .config('spark.jars.packages','org.apache.iceberg:iceberg-spark-runtime-3.3_2.12:1.3.1,org.projectnessie.nessie-integrations:nessie-spark-extensions-3.3_2.12:0.67.0,org.apache.hadoop:hadoop-aws:3.3.1') \
    .config('spark.sql.extensions','org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions,org.projectnessie.spark.extensions.NessieSparkSessionExtensions') \
    .config('spark.sql.catalog.nessie','org.apache.iceberg.spark.SparkCatalog') \
    .config('spark.sql.catalog.nessie.uri','http://172.18.0.2:19120/api/v1') \
    .config('spark.sql.catalog.nessie.ref','gold') \
    .config('spark.sql.catalog.nessie.catalog-impl','org.apache.iceberg.nessie.NessieCatalog') \
    .config('spark.sql.catalog.nessie.warehouse','s3a://lakehouse-prod/warehouse') \
    .config('spark.sql.catalog.nessie.io-impl','org.apache.iceberg.hadoop.HadoopFileIO') \
    .config('spark.hadoop.fs.s3a.access.key','962c9f862226831e4edea90cfcfafb8a8dffcd51') \
    .config('spark.hadoop.fs.s3a.secret.key','sd2rGU918DTmn35E4xJ8EV7BX2XUt7DkqC8v6WDNDUw=') \
    .config('spark.hadoop.fs.s3a.endpoint','https://bmcfe6z38foz.compat.objectstorage.ap-mumbai-1.oraclecloud.com') \
    .config('spark.hadoop.fs.s3a.path.style.access','true') \
    .config('spark.hadoop.fs.s3a.connection.ssl.enabled','true') \
    .getOrCreate()
df = spark.sql('SELECT * FROM nessie.ecommerce.daily_sales_gold LIMIT 5')
df.show(truncate=False)
spark.stop()
\"" 2>&1 | tail -20
```

---

## ⏰ 5. Demo: Time Travel (2 minutes)

### Query Table History
```bash
ssh -i ~/.ssh/oracle-vm1.key ubuntu@140.238.224.207 "docker exec lakehouse-spark python3 -c \"
from pyspark.sql import SparkSession
spark = SparkSession.builder.appName('timetravel') \
    .config('spark.jars.packages','org.apache.iceberg:iceberg-spark-runtime-3.3_2.12:1.3.1,org.projectnessie.nessie-integrations:nessie-spark-extensions-3.3_2.12:0.67.0,org.apache.hadoop:hadoop-aws:3.3.1') \
    .config('spark.sql.extensions','org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions,org.projectnessie.spark.extensions.NessieSparkSessionExtensions') \
    .config('spark.sql.catalog.nessie','org.apache.iceberg.spark.SparkCatalog') \
    .config('spark.sql.catalog.nessie.uri','http://172.18.0.2:19120/api/v1') \
    .config('spark.sql.catalog.nessie.ref','silver') \
    .config('spark.sql.catalog.nessie.catalog-impl','org.apache.iceberg.nessie.NessieCatalog') \
    .config('spark.sql.catalog.nessie.warehouse','s3a://lakehouse-prod/warehouse') \
    .config('spark.sql.catalog.nessie.io-impl','org.apache.iceberg.hadoop.HadoopFileIO') \
    .config('spark.hadoop.fs.s3a.access.key','962c9f862226831e4edea90cfcfafb8a8dffcd51') \
    .config('spark.hadoop.fs.s3a.secret.key','sd2rGU918DTmn35E4xJ8EV7BX2XUt7DkqC8v6WDNDUw=') \
    .config('spark.hadoop.fs.s3a.endpoint','https://bmcfe6z38foz.compat.objectstorage.ap-mumbai-1.oraclecloud.com') \
    .config('spark.hadoop.fs.s3a.path.style.access','true') \
    .config('spark.hadoop.fs.s3a.connection.ssl.enabled','true') \
    .getOrCreate()
spark.sql('SELECT * FROM nessie.ecommerce.orders_silver.history').show()
spark.stop()
\"" 2>&1 | tail -20
```

---

---

## 📊 6. Demo: SQL Analytics (Consumption Layer) (3 minutes)

### Interactive SQL via CLI (VM3)
Demonstrate standard SQL access to the data:

```bash
ssh -i key3/oracle-vm3.key ubuntu@161.118.185.218 \
  "docker exec lakehouse-thrift /opt/spark/bin/beeline -u jdbc:hive2://localhost:10000 -n admin -p admin -e \"SELECT count(*) as total_rows FROM nessie.ecommerce.orders_silver\""
```
*Expected Result: 3.1M+ rows returned via JDBC driver.*

---

## 🌍 7. Web UIs Available

| Service | URL | Credentials |
|---------|-----|-------------|
| **Airflow** | http://140.238.224.207:8080 | admin / admin |
| **Spark Master** | http://140.238.224.207:8080 | (no login) |
| **Nessie API** | http://140.238.224.207:19120/api/v1 | REST API |
| **SQL Engine** | `jdbc:hive2://161.118.185.218:10000` | (JDBC) |

---

## 🎤 Demo Script for Presentation

### Opening (1 min)
> "Today I'll demonstrate a data lakehouse with version control - like Git for databases. 
> We're processing 411 million e-commerce events through a medallion architecture."

### Demo Flow (10 min)
1. **Show Architecture** - Explain Bronze/Silver/Gold layers
2. **Run Pipeline** - Execute Silver transform (show 3M records)
3. **Show Gold Tables** - Query daily_sales_gold 
4. **Version Control** - List branches, show commit history
5. **Time Travel** - Query table at previous snapshot
6. **SQL Consumption** - Connect via JDBC (Simulate Tableau/BI)

### Closing (1 min)
> "This enables data teams to treat data as code - with branches, commits, 
> and the ability to roll back bad data changes. Production quality, Git-like workflows."

---

## 🔧 Troubleshooting

### If Spark jobs hang
```bash
# Restart the worker on VM2
ssh -i ~/.ssh/oracle-vm2.key ubuntu@140.245.16.49 "docker restart spark-worker"
```

### If services are down
```bash
# Restart all services on VM1
ssh -i ~/.ssh/oracle-vm1.key ubuntu@140.238.224.207 \
  "cd ~/Version_Control_For_Databases && docker-compose up -d"
```

---

## 📁 Project Structure

```
Version_Control_For_Databases/
├── scripts/
│   ├── bronze/ingest_orders_spark.py    # Raw → Bronze
│   ├── silver/transform_orders_silver.py # Bronze → Silver
│   ├── silver/merge_silver.py            # Merge to main
│   └── gold/build_gold_layer.py          # Silver → Gold
├── airflow/dags/
│   └── medallion_pipeline.py             # Orchestration DAG
├── docker-compose.yml                     # VM1 services
└── docs/
    └── PROJECT_DEMO_GUIDE.md             # This file
```

---

## ✅ Key Talking Points

1. **411 Million Records** - Real-world scale e-commerce data
2. **Medallion Architecture** - Industry standard (Bronze/Silver/Gold)
3. **Apache Iceberg** - Modern table format with ACID transactions
4. **Nessie Catalog** - Git-like version control for data
5. **Time Travel** - Query data at any point in history
6. **Distributed Processing** - 2-node Spark cluster
7. **Apache Airflow** - Production orchestration
8. **Oracle Cloud** - Enterprise infrastructure
