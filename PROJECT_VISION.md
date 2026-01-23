# Production Lakehouse - Project Vision & Goals

**Project**: Version Control for Databases  
**Status**: Building industry-grade data lakehouse  
**Date**: 2026-01-23

---

## 🎯 What We're Building

A **production-grade data lakehouse** with Git-like version control that demonstrates:
- Industry-standard data engineering practices
- Advanced Iceberg + Nessie capabilities
- Resume-worthy architecture

---

## 📊 Current Assets

| Asset | Status | Details |
|-------|--------|---------|
| VM1 (Master) | ✅ Running | 140.238.224.207 - Nessie, Spark, Jupyter |
| VM2 (Worker) | ✅ Running | 140.245.16.49 - Spark Worker |
| Oracle Storage | ✅ 7.6GB | 411M e-commerce records |
| Nessie Catalog | ✅ Running | Branches: main, dev |
| PostgreSQL | ✅ Running | Nessie metadata store |

---

## 🏗️ Phase 1: Correctness (Foundations)

### ✅ Iceberg + Nessie as Single Source of Truth
- [ ] Nessie REST catalog properly configured
- [ ] Warehouse on Oracle S3
- [ ] Branch-aware Spark jobs (`spark.sql.catalog.ref=bronze|silver|main`)
- [ ] Every write = versioned commit

### ✅ Medallion = Separate Schemas
```
nessie.ecommerce_bronze.orders
nessie.ecommerce_silver.orders  
nessie.ecommerce_gold.orders
```
- Each schema on its own Nessie branch
- Each with own quality rules

### ✅ Enforce WAP (Write-Audit-Publish) Strictly
```
layer_branch → temp_table_branch → audit → merge
```
- No direct writes to `silver` or `main`
- This puts us ahead of 80% of teams

---

## 🚀 Phase 2: Performance (Advanced)

### 🔥 Hidden Partitioning (Iceberg-Style)
```sql
PARTITIONED BY (
  days(event_time),
  bucket(16, user_id)
)
```
**Benefits**:
- Prevents small files
- Avoids partition explosion
- Works with schema evolution

### 🔥 Selective Bucketing
Use for:
- Heavy joins (fact ↔ dimension)
- Customer/product analytics

```sql
PARTITIONED BY (
  days(event_time),
  bucket(16, user_id)
)
```

### 🔥 Sort Orders (Z-Ordering)
Define sort on:
- `event_time`
- `user_id`
- `product_id`

**Improves**: Range scans, BI dashboards, ML feature extraction

---

## 💎 Phase 3: Governance (Industry Rare)

### Data Contracts per Layer
| Layer | Contract |
|-------|----------|
| Bronze | Schema flexible |
| Silver | Schema enforced |
| Gold | Breaking changes forbidden |

- Schema validation before merge
- Reject merge if contract breaks
- This is **Data CI/CD**

### Data Rollback as First-Class Feature
- Rollback silver to previous commit
- Re-run gold from old snapshot
- Reproduce old dashboards
- **Audit + compliance gold**

### Time-Travel Debugging
```python
# Why did revenue drop on Jan 10?
# 1. Checkout Nessie commit from Jan 9
# 2. Query gold.orders
# 3. Compare with Jan 11 commit
```
**No recompute. No guessing. Data forensics.**

---

## 🧪 Phase 4: Industry WOW

### Parallel Feature Engineering
```
main
 ├── feature_experiment_v1
 ├── feature_experiment_v2
 └── promo_model_branch
```
- Same base data, different transformations
- Merge only best result
- Very few orgs support this cleanly

### Commit-Level Metrics
Track per Nessie commit:
- Row counts
- Null percentages
- Distribution drift
- SLA timings

### Automatic File Compaction
- Small-file detection
- Scheduled `rewrite_data_files`
- Run on Silver/Gold only
- Shows production maturity

---

## 🛠️ Target Technology Stack

```
┌─────────────────────────────────────────────────────────────┐
│                    ORCHESTRATION                            │
│                    Apache Airflow                           │
│          DAG-based Bronze → Silver → Gold                   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    VERSION CONTROL                          │
│                    Project Nessie                           │
│            Branch: main | bronze | silver                   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    TABLE FORMAT                             │
│                   Apache Iceberg                            │
│     Partitioned by: days(event_time), bucket(16, user_id)  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      COMPUTE                                │
│              Spark Cluster (VM1 + VM2)                      │
│                    + Polars                                 │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   DATA QUALITY                              │
│                Great Expectations                           │
│        Validate at Silver merge, Gold merge                 │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   QUERY ENGINE                              │
│                      Trino                                  │
│        Ad-hoc queries, BI tools, QA audits                  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    METADATA                                 │
│              OpenMetadata / DataHub                         │
│         Lineage, Ownership, Tags (PII, etc.)               │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  OBSERVABILITY                              │
│              Prometheus + Grafana                           │
│       DAG duration, failures, data volume                   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   ALERTING                                  │
│                     Slack                                   │
│        Failure alerts, merge rejections                     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      BI                                     │
│               Apache Superset                               │
│         Connected to Trino → Gold layer                     │
└─────────────────────────────────────────────────────────────┘
```

---

## 📋 Services Summary

| Category | Service | Purpose |
|----------|---------|---------|
| Orchestration | Airflow | DAG-based workflows |
| Versioning | Nessie | Git-like data control |
| Table Format | Iceberg | ACID, time-travel |
| Compute | Spark + Polars | Distributed processing |
| Quality | Great Expectations | Data validation |
| Query | Trino | Ad-hoc SQL |
| Metadata | OpenMetadata | Lineage, governance |
| Monitoring | Prometheus + Grafana | Observability |
| Alerting | Slack | Notifications |
| BI | Superset | Dashboards |
| Storage | Oracle S3 | Object storage |

---

## ❌ What NOT to Add (Yet)

- Kafka (no real streaming use case)
- Flink (overkill)
- Too many BI tools
- Custom UI (waste of time)

---

## 🏆 End Goal

If we implement **70% of this**, we're showing **platform thinking**, not just tools.

**Resume Impact**:
- "Built production-grade data lakehouse with Git-like version control"
- "Implemented Write-Audit-Publish pattern for data CI/CD"
- "411M records with partitioning, time-travel, and data contracts"

---

## 📅 Implementation Order

1. **Spark Cluster** - VM1 master + VM2 worker
2. **Bronze Layer** - With partitioning
3. **Silver Layer** - With quality checks
4. **Gold Layer** - With aggregations
5. **WAP Demo** - Branch → Audit → Merge
6. **Airflow** - Orchestrate pipelines
7. **Monitoring** - Prometheus + Grafana
8. **BI** - Superset dashboards
