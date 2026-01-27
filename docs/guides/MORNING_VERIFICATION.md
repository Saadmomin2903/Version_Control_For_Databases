# Morning Verification Guide - Jan 27, 2026

## ✅ What Ran Overnight

**Ingestion Process:**
- **Started:** 3:12 AM IST
- **Script:** `ingest_full_dataset.py`
- **Data:** 1,614 parquet files (7.6GB)
- **Date Range:** Dec 2019 - Nov 2020 (14 months)
- **Expected Records:** ~317M (calculated from 196K records/file average)

---

## 🌅 Morning Checklist

### Step 1: Check If Ingestion Completed

```bash
ssh -i ~/.ssh/oracle-vm1.key ubuntu@140.238.224.207 \
  "tail -200 /tmp/ingestion_REAL_*.log"
```

**Look for:**
- ✅ `✅ Full dataset ingestion complete!`
- ✅ `Total new records: XXX,XXX,XXX`
- ✅ `Final Bronze count: XXX,XXX,XXX`

---

### Step 2: Verify Record Count

```bash
ssh -i ~/.ssh/oracle-vm1.key ubuntu@140.238.224.207 \
  "docker exec lakehouse-spark python3 << 'EOF'
from pyspark.sql import SparkSession
from pyspark import SparkConf

conf = SparkConf().setAppName('morning-check')
conf.set('spark.sql.catalog.nessie', 'org.apache.iceberg.spark.SparkCatalog')
conf.set('spark.sql.catalog.nessie.uri', 'http://nessie:19120/api/v1')
conf.set('spark.sql.catalog.nessie.ref', 'bronze')
conf.set('spark.sql.catalog.nessie.catalog-impl', 'org.apache.iceberg.nessie.NessieCatalog')
conf.set('spark.sql.catalog.nessie.warehouse', 's3a://lakehouse-prod/warehouse')

spark = SparkSession.builder.config(conf=conf).getOrCreate()
df = spark.table('nessie.ecommerce.orders_bronze')
count = df.count()
print(f'Bronze table: {count:,} records')
spark.stop()
EOF
"
```

**Expected:** ~317,000,000+ records

---

### Step 3: Check Process Status

```bash
ssh -i ~/.ssh/oracle-vm1.key ubuntu@140.238.224.207 \
  "ps aux | grep ingest_full_dataset"
```

**Expected:** No processes running (completed)

---

## 🚨 If Ingestion Failed

Check the error in the log:

```bash
ssh -i ~/.ssh/oracle-vm1.key ubuntu@140.238.224.207 \
  "grep -i 'error\|exception\|failed' /tmp/ingestion_REAL_*.log | tail -20"
```

Check which month it failed at and restart from that point if needed.

---

## ✅ If Ingestion Succeeded - Next Steps

### 1. Update Silver Layer (~1-2 hours)

```bash
ssh -i ~/.ssh/oracle-vm1.key ubuntu@140.238.224.207 \
  "nohup docker exec lakehouse-spark python3 /home/jovyan/scripts/silver/build_silver_layer.py \
   > /tmp/silver_$(date +%Y%m%d_%H%M%S).log 2>&1 &"
```

### 2. Update Gold Layer (~30-60 minutes)

```bash
ssh -i ~/.ssh/oracle-vm1.key ubuntu@140.238.224.207 \
  "nohup docker exec lakehouse-spark python3 /home/jovyan/scripts/gold/build_gold_layer.py \
   > /tmp/gold_$(date +%Y%m%d_%H%M%S).log 2>&1 &"
```

### 3. Re-run Customer Segmentation

```bash
ssh -i ~/.ssh/oracle-vm1.key ubuntu@140.238.224.207 \
  "docker exec lakehouse-spark python3 /home/jovyan/scripts/gold/customer_segmentation_simple.py"
```

**Expected:** ~1-1.5M customers in segments (up from 9.7K)

### 4. Run Product Recommendations

```bash
ssh -i ~/.ssh/oracle-vm1.key ubuntu@140.238.224.207 \
  "docker exec lakehouse-spark python3 /home/jovyan/scripts/gold/product_recommendation_iceberg.py"
```

**Expected:** 500+ recommendation rules (previously failed with too little data)

---

## 📊 Expected Final Results

| Metric | Before | After |
|--------|--------|-------|
| Bronze Records | 0 | ~317M |
| Silver Records | 0 | ~317M |
| Gold Aggregates | Small | Full |
| Customer Segments | 9.7K | ~1.5M |
| Product Recommendations | 0 | 500+ rules |
| Storage Used | ~10 GB | ~80-100 GB |

---

## 🎯 Day 2 Tasks (After Verification)

Once ingestion is confirmed successful:

1. **Apache Superset** - Create BI dashboards
2. **Update documentation** with new record counts
3. **Test SQL access** via VM3 (Trino) with full dataset
4. **Run Airflow DAG** end-to-end with production data

---

**Good morning! Check these steps when you wake up! ☀️**
