# 🥉 Bronze Layer: Scalable Raw Ingestion

The Bronze Layer is our "Entry Point" into the Lakehouse. It captures raw data from source systems in its original format while providing the benefits of a managed table format (Iceberg).

---

## 🏛️ Architecture Overview
In this demo, we ingest **66.6 million records** from a retail dataset stored in Parquet files.

- **Source:** Local Parquet files (`/home/jovyan/data/firebolt-raw/`)
- **Format:** [Apache Iceberg](https://iceberg.apache.org/) (High-performance table format)
- **Catalog:** [Project Nessie](https://projectnessie.org/) (Git-like version control for data)
- **Storage:** Oracle Cloud Object Storage (S3-Compatible)

---

## 🚀 The Ingestion Process
We use PySpark to read raw Parquet files, apply minimal transformations (casting timestamps), and write them into the Iceberg table.

### 📜 Key Scripts
| Script | Description |
| :--- | :--- |
| `reset_and_load_demo.py` | Drops existing metadata and performs a clean load of the April 2020 dataset. |
| `force_delete_nessie_table.py` | Fallback utility to directly delete corrupted table entries via Nessie REST API. |

### 🛠️ Spark Configuration
A critical part of the Bronze layer is the `S3FileIO` configuration, which allows Spark to talk directly to Oracle Cloud Object Storage:

```python
conf.set('spark.sql.catalog.nessie.io-impl', 'org.apache.iceberg.aws.s3.S3FileIO')
conf.set('spark.hadoop.fs.s3a.endpoint', 'https://bmcfe6z38foz.compat.objectstorage.ap-mumbai-1.oraclecloud.com')
```

---

## 📊 Demo Statistics
- **Total Records:** 66,589,268
- **Data Period:** April 1, 2020 - April 30, 2020
- **Storage Path:** `s3a://lakehouse-prod/warehouse/ecommerce/orders_bronze`

---

## 🔍 Verification Snapshot
You can verify the Bronze layer by running:

```sql
-- Query via Spark SQL
SELECT count(*) FROM nessie.ecommerce.orders_bronze;

-- Check exact location and metadata
DESCRIBE EXTENDED nessie.ecommerce.orders_bronze;
```

> [!TIP]
> **Why Iceberg for Bronze?**
> Even at the Bronze level, Iceberg provides **Schema Evolution** and **Partition Evolution**. If the source system adds a new column, we can easily adapt without rewriting the entire dataset.

---

## 🛡️ Metadata Integrity
During testing, we encountered an "Invalid S3 URI" issue where metadata was pointing to `/tmp/warehouse`. We resolved this by:
1. Using the Nessie REST API to purge the "ghost" table.
2. Re-creating the table with explicit S3 paths.
3. This ensures that the Bronze layer remains the **Immutable Source of Truth** for our Silver and Gold transformations.
