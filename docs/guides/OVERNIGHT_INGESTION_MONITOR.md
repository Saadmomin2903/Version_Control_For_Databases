# Overnight Ingestion Monitoring Guide

## 🌙 What's Running

**Started:** January 27, 2026 at 1:55 AM IST  
**Process:** Full dataset ingestion (May-November 2020)  
**Expected Duration:** 3-4 hours  
**Expected Completion:** ~5:00-6:00 AM IST

---

## 📋 Morning Checklist (When You Wake Up)

### Step 1: Check if Ingestion Completed

```bash
ssh -i ~/.ssh/oracle-vm1.key ubuntu@140.238.224.207 \
  "tail -50 /tmp/ingestion_20260127_015501.log"
```

**Look for:**
- ✅ `✅ Full dataset ingestion complete!`
- ✅ `Total new records: XXX,XXX,XXX`
- ❌ Any `ERROR` or `Exception` messages

---

### Step 2: Verify Record Counts

```bash
ssh -i ~/.ssh/oracle-vm1.key ubuntu@140.238.224.207 \
  "docker exec lakehouse-spark python3 -c '
from pyspark.sql import SparkSession
spark = SparkSession.builder.getOrCreate()
count = spark.sql(\"SELECT COUNT(*) FROM nessie.ecommerce.orders_bronze@bronze\").collect()[0][0]
print(f\"Bronze table count: {count:,} records\")
spark.stop()
'"
```

**Expected:**
- Before: 3,100,000 records (April 2020)
- After: ~370,000,000+ records (April-November 2020)

---

### Step 3: Check S3 Storage Usage

```bash
ssh -i ~/.ssh/oracle-vm1.key ubuntu@140.238.224.207 \
  "docker exec lakehouse-spark aws s3 ls s3://lakehouse-prod/warehouse/ --recursive --summarize | grep 'Total Size'"
```

**Expected:**
- Before: ~10 GB
- After: ~70-80 GB

---

## 🚨 If Ingestion Failed

### Check What Went Wrong

```bash
# View error logs
ssh -i ~/.ssh/oracle-vm1.key ubuntu@140.238.224.207 \
  "grep -i error /tmp/ingestion_20260127_015501.log | tail -20"

# Check if process is still running
ssh -i ~/.ssh/oracle-vm1.key ubuntu@140.238.224.207 \
  "ps aux | grep ingest_full_dataset"
```

### Restart from Failed Month

The script processes month-by-month. If it failed at (for example) August:

```bash
ssh -i ~/.ssh/oracle-vm1.key ubuntu@140.238.224.207 \
  "docker exec lakehouse-spark python3 -c '
from scripts.bronze.ingest_full_dataset import ingest_all_months
# Start from August (month 8) through November (month 11)
ingest_all_months(start_month=8, end_month=11)
'"
```

---

## ✅ If Ingestion Succeeded - Next Steps

### 1. Update Silver Layer (30-60 minutes)

```bash
ssh -i ~/.ssh/oracle-vm1.key ubuntu@140.238.224.207 \
  "docker exec lakehouse-spark python3 /home/jovyan/scripts/silver/build_silver_layer.py"
```

### 2. Update Gold Layer (20-30 minutes)

```bash
ssh -i ~/.ssh/oracle-vm1.key ubuntu@140.238.224.207 \
  "docker exec lakehouse-spark python3 /home/jovyan/scripts/gold/build_gold_layer.py"
```

### 3. Re-run ML Models

**Customer Segmentation:**
```bash
ssh -i ~/.ssh/oracle-vm1.key ubuntu@140.238.224.207 \
  "docker exec lakehouse-spark python3 /home/jovyan/scripts/gold/customer_segmentation_simple.py"
```

**Product Recommendations** (should now work with more data):
```bash
ssh -i ~/.ssh/oracle-vm1.key ubuntu@140.238.224.207 \
  "docker exec lakehouse-spark python3 /home/jovyan/scripts/gold/product_recommendation_iceberg.py"
```

---

## 📊 Expected Results After Full Pipeline

| Metric | Before | After |
|--------|--------|-------|
| Bronze Records | 3.1M | 370M+ |
| Silver Records | 3.1M | 370M+ |
| Customer Segments | 9,786 | ~1.2M |
| Product Recommendations | 0 rules | 500+ rules |
| Storage Used | 10 GB | 70-80 GB |

---

## 🔍 Monitoring During Night (Optional)

If you can't sleep and want to check progress:

```bash
# Watch live progress
ssh -i ~/.ssh/oracle-vm1.key ubuntu@140.238.224.207 \
  "tail -f /tmp/ingestion_20260127_015501.log"
```

Press `Ctrl+C` to exit.

---

## 📞 Emergency Stop

If you need to stop the ingestion for any reason:

```bash
ssh -i ~/.ssh/oracle-vm1.key ubuntu@140.238.224.207 \
  "docker exec lakehouse-spark pkill -f ingest_full_dataset.py"
```

**Note:** Data already written is safe (atomic commits). You can restart later.

---

**Good luck! The script is running smoothly. Check back in the morning! 😴💤**
