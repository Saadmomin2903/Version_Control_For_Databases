# Production Deployment Guide: Product Recommendation Engine

## 🎯 Overview

Complete guide for deploying a production-ready FPGrowth recommendation engine for 300M+ transaction records.

---

## 🚀 Pre-Deployment Checklist

### Environment Requirements
- [ ] Spark 3.3+ installed
- [ ] Python 3.8+ with PySpark
- [ ] Nessie server accessible
- [ ] S3-compatible storage configured
- [ ] Minimum cluster resources:
  - Driver: 4GB RAM
  - Executors: 6GB RAM each, 4 cores
  - Recommended: 10-20 executors for 300M records

### Data Requirements
- [ ] `orders_silver` table exists and populated
- [ ] Minimum 1M purchase transactions
- [ ] Data quality scores populated
- [ ] Recent data available (last 90 days)
- [ ] Valid customer sessions and product IDs

---

## 📋 Step-by-Step Deployment

### Step 1: Pre-Deployment Validation

Run the validation script to assess data quality:

```bash
# Run validation on VM2
docker exec spark-master python3 /opt/spark/validate_recommendations.py
```

### Step 2: Resource Allocation

**For 300M Records (via spark-submit):**

```bash
spark-submit \
  --master spark://spark-master:7077 \
  --driver-memory 4g \
  --executor-memory 6g \
  --executor-cores 4 \
  --conf spark.sql.shuffle.partitions=400 \
  /opt/spark/product_recommendation_iceberg.py
```

### Step 3: Run Pipeline

You can run it directly via docker exec as we've been doing:

```bash
docker exec spark-master python3 /opt/spark/product_recommendation_iceberg.py
```

### Step 4: Post-Deployment Validation

```bash
docker exec spark-master python3 /opt/spark/validate_recommendations.py
```

---

## 📊 Monitoring & Health Checks

### Daily SQL Checks

```sql
-- 1. Data freshness
SELECT 
    MAX(generated_at) as last_update,
    DATEDIFF(CURRENT_DATE, MAX(generated_at)) as days_old
FROM nessie.ecommerce.product_recommendations;

-- 2. Coverage
SELECT 
    COUNT(DISTINCT product_id) as products_with_recs,
    COUNT(DISTINCT product_id) * 100.0 / (SELECT COUNT(DISTINCT product_id) FROM nessie.ecommerce.orders_silver WHERE event_type='purchase') as coverage_pct
FROM nessie.ecommerce.product_recommendations;
```

---

## 🔧 Troubleshooting

- **No Rules Found**: Lower `minSupport` in the script or check if `MIN_PRODUCT_FREQUENCY` is too high.
- **OOM Errors**: Increase `executor-memory` or reduce `RECENCY_DAYS`.
- **Slow Queries**: Ensure you are querying using the `partition_key` (product_id % 100).
