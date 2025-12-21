# Production Workflow Guide

## 🎯 Overview

This lakehouse now uses a **production-grade 4-branch architecture**:

```
bronze → silver → gold → main
(raw)   (clean)  (staging) (production)
```

**Key Benefit**: Gold branch acts as a staging environment where you can review and test aggregations before releasing to production.

---

## 📋 Daily Workflow

### Step 1: Run Data Pipeline to Staging

```bash
# 1. Ingest raw data to bronze
docker exec lakehouse-spark python3 /home/jovyan/scripts/bronze/ingest_orders_spark.py
docker exec lakehouse-spark python3 /home/jovyan/scripts/bronze/ingest_customers_spark.py

# 2. Transform to silver (validated data)
docker exec lakehouse-spark python3 /home/jovyan/scripts/silver/transform_orders_silver.py
docker exec lakehouse-spark python3 /home/jovyan/scripts/silver/transform_customers_silver.py

# 3. Aggregate to gold (STAGING - not production yet!)
docker exec lakehouse-spark python3 /home/jovyan/scripts/gold/aggregate_customer_summary_gold.py
```

**Result**: Data is now on the **gold branch** (staging environment)

---

### Step 2: Review Staging Data

Use Jupyter or queries to review gold branch:

```python
# In Jupyter notebook or PySpark
spark.sql("""
    SELECT customer_segment, COUNT(*) as count, SUM(total_revenue) as revenue
    FROM nessie.ecommerce.`customer_summary@gold`
    GROUP BY customer_segment
    ORDER BY revenue DESC
""").show()

# Check top customers
spark.sql("""
    SELECT customer_id, name, total_orders, total_revenue, customer_segment
    FROM nessie.ecommerce.`customer_summary@gold`
    ORDER BY total_revenue DESC
    LIMIT 10
""").show()

# Verify totals
spark.sql("""
    SELECT 
        COUNT(*) as total_customers,
        SUM(total_revenue) as total_revenue,
        AVG(customer_lifetime_value) as avg_clv
    FROM nessie.ecommerce.`customer_summary@gold`
""").show()
```

**Decision Point**: Does the data look correct? Are metrics accurate?

---

### Step 3: Promote to Production (If Approved)

```bash
# Merge gold → main (production release)
python3 scripts/utils/promote_to_production.py
```

**What happens**:
1. Script shows current branch hashes
2. Asks for confirmation
3. Merges gold branch into main
4. Production users now see updated data

**BI tools can now query**:
```sql
SELECT * FROM nessie.ecommerce.customer_summary
-- No @branch syntax = queries main (production)
```

---

## 🔄 If Something Goes Wrong

### Scenario 1: Issues Found During Review (Before Promotion)

**Problem**: You review gold branch and find incorrect data

**Solution**: Just re-run the gold script
```bash
# Fix the issue, then re-run
docker exec lakehouse-spark python3 /home/jovyan/scripts/gold/aggregate_customer_summary_gold.py

# Gold branch is updated
# Main (production) is unchanged
```

**No impact on production!** ✅

---

### Scenario 2: Issues Found After Production Release

**Problem**: You promoted to production, users report issues

**Solution**: Rollback to previous version
```bash
python3 scripts/utils/rollback_production.py

# Shows recent commits:
# 0. abc123... - Promote gold aggregations to production (current)
# 1. def456... - Previous production state
# 2. xyz789... - Even older state

# Select: 1 (to go back to previous)
# Confirms and rolls back

# Production immediately restored to previous good state
```

**Recovery time**: Seconds (no re-processing needed!) ✅

---

## 📊 Branch Comparison at Any Time

```bash
# See what's on each branch
echo "=== BRONZE ===" && curl -s "http://localhost:19120/api/v1/trees/tree/bronze/entries" | python3 -c "import json, sys; [print(e['name']['elements']) for e in json.load(sys.stdin).get('entries', [])]"

echo "=== SILVER ===" && curl -s "http://localhost:19120/api/v1/trees/tree/silver/entries" | python3 -c "import json, sys; [print(e['name']['elements']) for e in json.load(sys.stdin).get('entries', [])]"

echo "=== GOLD (staging) ===" && curl -s "http://localhost:19120/api/v1/trees/tree/gold/entries" | python3 -c "import json, sys; [print(e['name']['elements']) for e in json.load(sys.stdin).get('entries', [])]"

echo "=== MAIN (production) ===" && curl -s "http://localhost:19120/api/v1/trees/tree/main/entries" | python3 -c "import json, sys; [print(e['name']['elements']) for e in json.load(sys.stdin).get('entries', [])]"
```

---

## 🎯 Best Practices

### 1. Always Review Before Promoting
- Check metrics make sense
- Verify customer segments are reasonable
- Compare with previous data for anomalies

### 2. Promote During Maintenance Windows
- Schedule promotions when users won't be impacted
- Communicate changes to stakeholders

### 3. Keep Audit Trail
- Document what was changed
- Note the commit hashes
- Record promotion times

### 4. Test Rollback Procedure
- Practice rollback in development
- Ensure team knows how to recover

---

## 🔐 Access Control Pattern

**Recommended permissions**:

| Role | Bronze | Silver | Gold | Main | Promote | Rollback |
|------|--------|--------|------|------|---------|----------|
| Data Engineer | Write | Write | Write | Read | ✅ | ✅ |
| Data Analyst | Read | Read | Read | Read | ❌ | ❌ |
| DevOps | Read | Read | Read | Read | ✅ | ✅ |
| BI Tools | - | - | - | Read only | - | - |

**Key principle**: Only authorized personnel can promote to production

---

## 📝 Quick Reference

### Query Staging (Gold Branch)
```sql
SELECT * FROM nessie.ecommerce.`customer_summary@ gold`
```

### Query Production (Main Branch)
```sql
SELECT * FROM nessie.ecommerce.customer_summary
-- Or explicitly:
SELECT * FROM nessie.ecommerce.`customer_summary@main`
```

### Promote to Production
```bash
python3 scripts/utils/promote_to_production.py
```

### Rollback Production
```bash
python3 scripts/utils/rollback_production.py
```

---

## 🚀 Benefits of This Workflow

✅ **Safe**: Test before production release  
✅ **Reversible**: Quick rollback if needed  
✅ **Auditable**: Clear separation of stages  
✅ **Flexible**: Can have multiple versions in development  
✅ **Professional**: Industry-standard release management  

---

## 💡 Example Scenario

**Day 1 - 9:00 AM**: Run pipeline to gold
```bash
docker exec lakehouse-spark python3 /home/jovyan/scripts/gold/aggregate_customer_summary_gold.py
```

**Day 1 - 10:00 AM**: Review staging
```sql
-- Analyst reviews gold branch
SELECT * FROM nessie.ecommerce.`customer_summary@gold` WHERE customer_segment = 'Premium'
-- Looks good!
```

**Day 1 - 2:00 PM**: Promote to production
```bash
python3 scripts/utils/promote_to_production.py
-- Confirmed: Merge successful
```

**Day 1 - 3:00 PM**: Issue reported
```
User: "Customer xyz showing wrong revenue"
```

**Day 1 - 3:05 PM**: Rollback
```bash
python3 scripts/utils/rollback_production.py
-- Select: 1 (previous version)
-- Production restored in 30 seconds
```

**Day 2**: Fix issue, re-run to gold, review, promote again

---

**This is production-grade data operations!** 🎉
