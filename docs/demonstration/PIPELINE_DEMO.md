# 🔄 Complete Pipeline Demo

## Architecture Overview

```
Raw Data (Parquet)          
     │
     ▼
┌─────────────┐
│   BRONZE    │  Raw Iceberg tables (3.1M records)
└─────────────┘
     │
     ▼
┌─────────────┐
│   SILVER    │  Cleaned, deduplicated (3.1M records)
└─────────────┘
     │
     ▼
┌─────────────┐
│    GOLD     │  Business aggregations (4 tables)
└─────────────┘
```

---

## 🎯 Demo Option 1: Airflow UI

1. Open http://140.238.224.207:8080
2. Login: `admin` / `admin`
3. Find DAG: `medallion_architecture_pipeline`
4. Unpause → Click Trigger ▶️
5. Watch tasks execute: Bronze → Silver → Gold

---

## 🎯 Demo Option 2: Manual Commands

### Run Silver Transform
```bash
ssh -i ~/.ssh/oracle-vm1.key ubuntu@140.238.224.207 \
  "docker exec lakehouse-spark python3 /home/jovyan/scripts/silver/transform_orders_silver.py"
```

### Run Gold Aggregations
```bash
ssh -i ~/.ssh/oracle-vm1.key ubuntu@140.238.224.207 \
  "docker exec lakehouse-spark python3 /home/jovyan/scripts/gold/build_gold_layer.py"
```

---

## Expected Output

### Silver:
```
✅ Total Records Written: 3,138,325
```

### Gold:
```
[1/4] Building: daily_sales_gold ✅ Done.
[2/4] Building: brand_performance_gold ✅ Done.
[3/4] Building: customer_stats_gold ✅ Done.
[4/4] Building: category_stats_gold ✅ Done.
✨ GOLD LAYER BUILD COMPLETE
```

---

## 🎤 Presentation Script

> "Let me show you the complete data pipeline in action."
>
> *[Trigger DAG or run commands]*
>
> "We're processing **3 million e-commerce events** through our Medallion architecture:"
> 1. **Bronze** - Raw data ingestion
> 2. **Silver** - Cleaning and deduplication
> 3. **Gold** - Business-ready aggregations
>
> "The entire pipeline is **version controlled** and **auditable**."
