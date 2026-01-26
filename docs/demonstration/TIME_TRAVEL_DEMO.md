# 🕰️ Time Travel Demo

## What is Time Travel?

Time Travel allows you to query data **as it existed at any point in the past**. Every write creates a snapshot.

```
Timeline:
────────────────────────────────────────────────────►
   Snapshot 1      Snapshot 2      Snapshot 3
   (Jan 20)        (Jan 23)        (Jan 26)
   1M records      2M records      3.1M records
```

---

## 💼 Business Value

| Use Case | Example |
|----------|---------|
| **Data Recovery** | Bad data loaded? Roll back instantly |
| **Audit Compliance** | Show data as it was on Dec 31 for auditors |
| **Debug Issues** | Compare today vs yesterday |
| **ML Reproducibility** | Retrain with exact historical data |

---

## 🎯 Demo Commands

### Step 1: Show Table History
```bash
ssh -i ~/.ssh/oracle-vm1.key ubuntu@140.238.224.207 "docker exec lakehouse-spark python3 -c \"
from pyspark.sql import SparkSession
spark = SparkSession.builder \
    .appName('time_travel') \
    .config('spark.jars.packages', 'org.apache.iceberg:iceberg-spark-runtime-3.3_2.12:1.3.1,org.projectnessie.nessie-integrations:nessie-spark-extensions-3.3_2.12:0.67.0,org.apache.hadoop:hadoop-aws:3.3.1') \
    .config('spark.sql.extensions', 'org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions,org.projectnessie.spark.extensions.NessieSparkSessionExtensions') \
    .config('spark.sql.catalog.nessie', 'org.apache.iceberg.spark.SparkCatalog') \
    .config('spark.sql.catalog.nessie.uri', 'http://172.18.0.2:19120/api/v1') \
    .config('spark.sql.catalog.nessie.ref', 'silver') \
    .config('spark.sql.catalog.nessie.catalog-impl', 'org.apache.iceberg.nessie.NessieCatalog') \
    .config('spark.sql.catalog.nessie.warehouse', 's3a://lakehouse-prod/warehouse') \
    .config('spark.sql.catalog.nessie.io-impl', 'org.apache.iceberg.hadoop.HadoopFileIO') \
    .config('spark.hadoop.fs.s3a.endpoint', 'https://bmcfe6z38foz.compat.objectstorage.ap-mumbai-1.oraclecloud.com') \
    .config('spark.hadoop.fs.s3a.access.key', '962c9f862226831e4edea90cfcfafb8a8dffcd51') \
    .config('spark.hadoop.fs.s3a.secret.key', 'sd2rGU918DTmn35E4xJ8EV7BX2XUt7DkqC8v6WDNDUw=') \
    .config('spark.hadoop.fs.s3a.path.style.access', 'true') \
    .config('spark.hadoop.fs.s3a.impl', 'org.apache.hadoop.fs.s3a.S3AFileSystem') \
    .config('spark.hadoop.fs.s3a.connection.ssl.enabled', 'true') \
    .getOrCreate()

print('Table Snapshots:')
spark.sql('SELECT snapshot_id, committed_at, operation FROM nessie.ecommerce.orders_silver.snapshots').show()
spark.stop()
\""
```

### Expected Output:
```
+-------------------+-----------------------+---------+
|snapshot_id        |committed_at           |operation|
+-------------------+-----------------------+---------+
|6780090446736386101|2026-01-26 07:47:29.75 |append   |
|5723709213822143610|2026-01-26 08:07:39.605|append   |
|1478049952168529265|2026-01-26 08:26:25.06 |append   |
+-------------------+-----------------------+---------+
```

---

## 🎤 Presentation Script

> "One of the most powerful features is **Time Travel**. Every data change creates a snapshot."
>
> *[Show snapshots]*
>
> "Here are 3 snapshots. I can query **any historical version** instantly."
>
> "If bad data is loaded, we **rollback in seconds**. For compliance, we show **exactly** what existed on any date."

---

## SQL Syntax Reference

```sql
-- Query current data
SELECT * FROM table_name

-- Query specific snapshot
SELECT * FROM table_name VERSION AS OF <snapshot_id>

-- Query as of timestamp
SELECT * FROM table_name TIMESTAMP AS OF '2026-01-25 10:00:00'

-- Show all snapshots
SELECT * FROM table_name.snapshots
```
