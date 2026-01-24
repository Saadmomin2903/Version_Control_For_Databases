# Dataset Migration Guide - Quick Reference

**Switching from Brazilian E-Commerce (100k) to Firebolt (412M records)**

---

## 🔄 Key Changes Summary

| Aspect | Before (Brazilian) | After (Firebolt) |
|--------|-------------------|------------------|
| **Dataset** | Brazilian E-Commerce | Firebolt E-Commerce |
| **Records** | 100,000 | 412,000,000 |
| **Size** | 50 MB | 52 GB (compressed: 21 GB) |
| **Time Range** | Snapshot | 7 months (Oct 2019 - Apr 2020) |
| **Tables** | 2 | 4 |
| **Download Source** | Kaggle | AWS S3 (public) |
| **Processing Strategy** | All at once | Incremental (month-by-month) |
| **Storage** | Simple | Partitioned by month |
| **Processing Time** | ~5 minutes | ~6 hours total |

---

## 📋 Updated Guides

### **Use These New Guides**:
1. ✅ **`FIREBOLT_DEPLOYMENT_GUIDE.md`** - Complete deployment for 412M records
2. ✅ **`TEAM_PROJECT_PLAN.md`** - Already updated for Firebolt
3. ✅ **`CLOUD_MIGRATION_PLAN.md`** - Infrastructure (no changes needed)

### **Previous Guides** (Keep for reference):
- ⚠️ `PRODUCTION_DEPLOYMENT_GUIDE.md` - Infrastructure steps still valid
- ⚠️ `PRODUCTION_DEPLOYMENT_GUIDE_PART2.md` - VM setup still valid
- 📦 Use for infrastructure, update for data processing

---

## 🚀 Quick Start with Firebolt

### Step 1: Download Sample (Testing)
```bash
mkdir -p data/firebolt-sample
cd data/firebolt-sample

# Get 1 month sample (~6 GB)
aws s3 cp s3://firebolt-publishing-public/samples/e_commerce/transactions_oct2019.csv.gz . --no-sign-request
aws s3 cp s3://firebolt-publishing-public/samples/e_commerce/users_oct2019.csv.gz . --no-sign-request
aws s3 cp s3://firebolt-publishing-public/samples/e_commerce/products.csv.gz . --no-sign-request
aws s3 cp s3://firebolt-publishing-public/samples/e_commerce/sessions_oct2019.csv.gz . --no-sign-request

gunzip *.gz
```

### Step 2: Use Updated Scripts
```bash
# New bronze script for Firebolt
scripts/bronze/ingest_firebolt_transactions.py  # ✅ Use this
# vs
scripts/bronze/ingest_brazilian_orders.py       # ❌ Old

# Schema differences handled automatically
```

### Step 3: Partitioning (CRITICAL!)
```python
# All Firebolt scripts MUST include:
.partitionedBy("year_month")

# Without partitioning:
# - 412M records in one partition = ❌ SLOW
# - Storage inefficient
# - Queries scan entire dataset

# With monthly partitioning:
# - 7 partitions × ~60M records = ✅ FAST
# - Query only relevant months
# - Storage efficient
```

### Step 4: Incremental Processing
```bash
# Process month-by-month to stay under 20 GB:
for month in 2019-10 2019-11 2019-12 2020-01 2020-02 2020-03 2020-04; do
    # 1. Ingest month
    ingest_month.py --month=$month
    
    # 2. Transform
    transform_month.py --month=$month
    
    # 3. Delete source CSV (free up space)
    delete_source.sh $month
done

# Total storage never exceeds 15 GB ✅
```

---

## 🔧 Script Updates Needed

### Bronze Layer
```python
# OLD (Brazilian):
df = spark.read.csv("data/brazilian-ecommerce/olist_orders_dataset.csv")

# NEW (Firebolt):
df = spark.read.csv("oci://lakehouse-prod/raw/firebolt/transactions_2019-10.csv")
# Add partitioning:
.partitionedBy("year_month")
```

### Silver Layer
```python
# No major changes - same quality checks!
# Just more data to process
```

### Gold Layer
```python
# Same aggregation logic
# But now across 7 months of data
# Results will be more statistically significant
```

---

## 💾 Storage Management

### Oracle Free Tier (20 GB limit)

**Strategy to stay under limit**:

```yaml
Month 1: Process October 2019
  Raw CSV: 6 GB
  Bronze Parquet: 1 GB
  Silver Parquet: 800 MB
  Total: ~8 GB ✅
  
Month 2: Process November 2019
  Delete Oct CSV: -6 GB
  New CSV: +6 GB
  New Bronze: +1 GB
  New Silver: +800 MB
  Total: ~10 GB ✅
  
Month 7: Process April 2020 (last month)
  Delete previous CSV: -6 GB
  Final state:
    Bronze (7 months): 7 GB
    Silver (7 months): 6 GB
    Gold (aggregated): 500 MB
  Total: 13.5 GB ✅
```

---

## 📊 Enhanced ML Features

### New Features Available (from Firebolt)

```python
# Session-based features (not in Brazilian dataset):
session_features = {
    'avg_session_duration': ...,
    'pages_per_session': ...,
    'bounce_rate': ...,
    'conversion_rate': ...,
    'device_preference': ...,
    'traffic_source_performance': ...
}

# Time-series features (7 months of data):
temporal_features = {
    'purchase_frequency_trend': ...,
    'seasonal_pattern': ...,
    'growth_rate': ...,
    'churn_prediction_confidence': ...  # More data = better predictions!
}

# Product features:
product_features = {
    'cross_sell_affinity': ...,
    'category_switching': ...,
    'brand_loyalty': ...
}
```

### Improved ML Model Accuracy

```yaml
Brazilian (100k records):
  Churn Model AUC: ~0.75 (limited data)
  Segmentation: Basic 3-4 clusters
  Recommendations: Cold start issues
  
Firebolt (412M records):
  Churn Model AUC: > 0.82 ✅ (more training data!)
  Segmentation: Rich 5-6 clusters
  Recommendations: High coverage (85%+)
  Session analysis: Conversion optimization
```

---

## ✅ Migration Checklist

### Before Migration
- [ ] Read `FIREBOLT_DEPLOYMENT_GUIDE.md` completely
- [ ] Test with 1-month sample locally
- [ ] Verify partitioning works
- [ ] Understand incremental strategy

### During Migration
- [ ] Download Firebolt dataset (or monthly files)
- [ ] Update bronze scripts with partitioning
- [ ] Process incrementally (month-by-month)
- [ ] Monitor storage usage
- [ ] Delete source files after processing

### After Migration
- [ ] Verify all 7 months processed
- [ ] Check partition distribution
- [ ] Run quality checks
- [ ] Train ML models on full dataset
- [ ] Update dashboards with new metrics

---

## 🎯 Expected Outcomes

### Week 1: Testing with Sample
- ✅ 1 month processed (~60M records)
- ✅ Pipeline validated
- ✅ Performance benchmarked

### Week 2: Full Dataset Processing
- ✅ All 7 months loaded (412M records)
- ✅ Storage optimized (~13.5 GB)
- ✅ Bronze + Silver complete

### Week 3: ML & Gold Layer
- ✅ 3 ML models trained
- ✅ Gold aggregations complete
- ✅ Better than Brazilian dataset models!

### Week 4: Production
- ✅ Production deployment
- ✅ Dashboards live
- ✅ Team presentation ready

---

## 📞 Support

**Questions about migration?**
- Check `FIREBOLT_DEPLOYMENT_GUIDE.md` first
- Review `TEAM_PROJECT_PLAN.md` for task breakdown
- Infrastructure unchanged - use existing cloud guides

**Troubleshooting**:
- Storage limit exceeded → Use incremental processing
- Slow queries → Check partitioning configured
- Out of memory → Reduce Spark parallelism

---

**You're ready to process 412 million records!** 🚀

*Estimated effort: Same 4 weeks, dramatically better results!*
