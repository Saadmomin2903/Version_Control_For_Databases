# 🏗️ Project Architecture - Complete Understanding

## Overview

This document explains the complete architecture of the Data Lakehouse with Version Control project.

---

## 1. Medallion Architecture (Data Layers)

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│     BRONZE      │ ──► │     SILVER      │ ──► │      GOLD       │
│   (Raw Data)    │     │   (Cleaned)     │     │  (Aggregated)   │
└─────────────────┘     └─────────────────┘     └─────────────────┘
     3.1M rows              3.1M rows            4 aggregate tables
```

| Layer | Purpose | Table(s) | Schema |
|-------|---------|----------|--------|
| **Bronze** | Raw ingestion | `orders_bronze` | Flexible |
| **Silver** | Cleaned, deduplicated | `orders_silver` | Semi-structured |
| **Gold** | Business aggregates | `daily_sales_gold`, `brand_performance_gold`, `customer_stats_gold`, `category_stats_gold` | Strict |

---

## 2. Branches Per Layer

**Each layer has its own dedicated Nessie branch:**

```
┌──────────────────────────────────────────────────────────────────┐
│                                                                  │
│   BRONZE LAYER                     BRONZE BRANCH                 │
│   ────────────                     ─────────────                 │
│   • Raw data ingestion      ───►   • Work happens here           │
│   • Flexible schema                • Table: orders_bronze        │
│   • Accept all data                • Isolated from production    │
│                                                                  │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│   SILVER LAYER                     SILVER BRANCH                 │
│   ────────────                     ─────────────                 │
│   • Cleaned data            ───►   • Work happens here           │
│   • Deduplicated                   • Table: orders_silver        │
│   • Typed schema                   • Isolated from production    │
│                                                                  │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│   GOLD LAYER                       GOLD BRANCH                   │
│   ──────────                       ───────────                   │
│   • Aggregated analytics    ───►   • Work happens here           │
│   • Business metrics               • 4 aggregate tables          │
│   • Strict schema                  • Isolated from production    │
│                                                                  │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│   PRODUCTION                       MAIN BRANCH                   │
│   ──────────                       ───────────                   │
│   • All approved data       ◄───   • MERGED from branches        │
│   • What users query               • Contains validated data     │
│   • Live/Production                • "Source of truth"           │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## 3. Data Flow Workflow

### Step 1: Bronze Layer → Bronze Branch
```
Raw Parquet Files (411M rows)
         │
         ▼
 ┌───────────────────┐
 │   BRONZE BRANCH   │  ← Engineer writes here
 │   orders_bronze   │  ← 3.1M records
 └───────────────────┘
```
**Script:** `ingest_orders_spark.py` with `ref=bronze`

### Step 2: Silver Layer → Silver Branch
```
 BRONZE BRANCH ──► Read ──► Transform ──► SILVER BRANCH
                                          orders_silver
```
**Script:** `transform_orders_silver.py` with `ref=silver`

### Step 3: Gold Layer → Gold Branch
```
 SILVER BRANCH ──► Read ──► Aggregate ──► GOLD BRANCH
                                          4 gold tables
```
**Script:** `build_gold_layer.py` with `ref=gold`

### Step 4: Merge to Main
```
 bronze ─┐
 silver ─┼──► MERGE ──► MAIN (Production)
 gold   ─┘
```

---

## 4. Infrastructure Setup

```
┌─────────────────────────────────────────────────────────────┐
│                     VM1 (140.238.224.207)                   │
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │   Nessie    │  │   Airflow   │  │  Spark      │         │
│  │  (Catalog)  │  │   (DAGs)    │  │  Master     │         │
│  │  :19120     │  │   :8080     │  │             │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                     VM2 (140.245.16.49)                     │
│                                                             │
│              ┌─────────────────────────┐                    │
│              │     Spark Worker        │                    │
│              │   (Executes tasks)      │                    │
│              └─────────────────────────┘                    │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              Oracle Object Storage (S3-compatible)          │
│                                                             │
│     s3a://lakehouse-prod/warehouse/  (Iceberg tables)       │
│     s3a://lakehouse-prod/bronze/     (Raw parquet)          │
└─────────────────────────────────────────────────────────────┘
```

---

## 5. Technologies Used

| Technology | Purpose |
|------------|---------|
| **Apache Iceberg** | Table format with ACID, time travel, schema evolution |
| **Nessie** | Git-like version control for data tables |
| **Apache Spark** | Distributed data processing (2-node cluster) |
| **Apache Airflow** | Pipeline orchestration and scheduling |
| **Oracle Cloud** | VMs and S3-compatible Object Storage |

---

## 6. Key Features

### Time Travel
Query data at any historical point:
```sql
SELECT * FROM table VERSION AS OF <snapshot_id>
```

### Branch Isolation
Test changes without affecting production:
- Work on `silver` branch
- Validate data quality
- Merge to `main` when ready

### WAP Pattern (Write-Audit-Publish)
1. **Write** to branch
2. **Audit** data quality
3. **Publish** (merge) to main

---

## 7. Current Data Status

| Branch | Tables | Records |
|--------|--------|---------|
| **main** | orders_bronze, orders_silver | 3,138,325 |
| **bronze** | orders_bronze | 3,148,802 |
| **silver** | orders_silver | 3,138,325 |
| **gold** | 4 aggregate tables | Computed |

---

## 8. Why This Design?

| Benefit | Explanation |
|---------|-------------|
| **Isolation** | If Bronze fails, Silver/Gold not affected |
| **Rollback** | Undo bad merges easily |
| **Parallel work** | Multiple teams work simultaneously |
| **Audit trail** | Track all changes with history |
| **Testing** | Test on branch before production |
