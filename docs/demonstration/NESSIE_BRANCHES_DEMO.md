# 🌿 Nessie Branches Demo

## What is Nessie?

Nessie provides **Git-like version control for data**. Just like Git branches for code, Nessie has branches for data tables.

```
main (production)
  │
  ├── bronze (raw data branch)
  │
  ├── silver (transformed data branch)
  │
  └── gold (analytics branch)
```

---

## 🎯 Demo: View All Branches

### Option 1: Browser (REST API)
Open: http://140.238.224.207:19120/api/v1/trees

### Option 2: Spark SQL
```bash
ssh -i ~/.ssh/oracle-vm1.key ubuntu@140.238.224.207 "docker exec lakehouse-spark python3 -c \"
from pyspark.sql import SparkSession
spark = SparkSession.builder \
    .appName('branches') \
    .config('spark.jars.packages', 'org.apache.iceberg:iceberg-spark-runtime-3.3_2.12:1.3.1,org.projectnessie.nessie-integrations:nessie-spark-extensions-3.3_2.12:0.67.0') \
    .config('spark.sql.extensions', 'org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions,org.projectnessie.spark.extensions.NessieSparkSessionExtensions') \
    .config('spark.sql.catalog.nessie', 'org.apache.iceberg.spark.SparkCatalog') \
    .config('spark.sql.catalog.nessie.uri', 'http://172.18.0.2:19120/api/v1') \
    .config('spark.sql.catalog.nessie.catalog-impl', 'org.apache.iceberg.nessie.NessieCatalog') \
    .getOrCreate()

print('All Nessie Branches:')
spark.sql('LIST REFERENCES IN nessie').show()
spark.stop()
\""
```

### Expected Output:
```
+------+--------+--------------------+
|  type|    name|               hash |
+------+--------+--------------------+
|BRANCH|  bronze|53493ecd33e765fd...|
|BRANCH|    main|cb7893afa0628c89...|
|BRANCH|  silver|eca1affcab4ee8dc...|
|BRANCH|    gold|d029c097a8019824...|
+------+--------+--------------------+
```

---

## 💼 Business Value

| Feature | Benefit |
|---------|---------|
| **Isolation** | Test changes on branch without affecting production |
| **Merge control** | Review data changes before promoting |
| **Rollback** | Switch branches to undo changes |
| **Audit trail** | Complete history of who changed what |

---

## 🎤 Presentation Script

> "We use Nessie for **Git-like version control of data**."
>
> "Just like developers have branches for code, we have branches for data:"
> - `bronze` for raw ingestion
> - `silver` for transformations  
> - `gold` for analytics
> - `main` for production
>
> "Changes can be reviewed and merged, just like a pull request!"
