# Branching in Data Lakehouse - Explained Simply

## 🤔 Your Question: Why Create Branches?

Let me answer your questions with real examples from your pipeline.

---

## 📊 Current Setup: What You Have

```
main branch (Production)
  └── ecommerce.customer_summary (Gold layer)

silver branch
  ├── ecommerce.orders_silver
  └── ecommerce.customers_silver

bronze branch
  ├── ecommerce.orders_bronze
  └── ecommerce.customers_bronze
```

---

## 🎯 Why Branching Helps: Real-World Scenarios

### Scenario 1: Testing New Transformations Safely

**Problem**: You want to change the silver transformation logic without breaking production.

**Without Branches** ❌:
```
orders.csv → Bronze → Silver (new logic) → Gold → 💥 BREAKS PRODUCTION!
```
If your new transformation has a bug, it immediately affects Gold layer and BI dashboards.

**With Branches** ✅:
```
orders.csv → Bronze → silver (old logic) → main (SAFE, unchanged)
                    ↓
                  dev-branch (new logic) → ISOLATED, test here!
```

**Example**:
```bash
# Create a dev branch to test new logic
curl -X POST http://localhost:19120/api/v1/trees/tree \
  -d '{"name": "dev-silver", "type": "BRANCH", "hash": "<silver-hash>"}'

# Run transformation on dev branch
spark.sql("""
  CREATE TABLE nessie.ecommerce.`orders_silver@dev-silver`
  AS SELECT 
    *,
    -- NEW: Add currency conversion
    total_amount * 0.85 as total_amount_eur
  FROM nessie.ecommerce.`orders_bronze@bronze`
""")

# Compare results
SELECT COUNT(*) FROM nessie.ecommerce.`orders_silver@silver`        -- Old: 1000 rows
SELECT COUNT(*) FROM nessie.ecommerce.`orders_silver@dev-silver`   -- New: 1000 rows

# Check quality on dev branch
SELECT AVG(total_amount_eur) FROM nessie.ecommerce.`orders_silver@dev-silver`
```

✅ **Production (silver branch) is untouched!**  
✅ **You can test without fear!**

---

### Scenario 2: Multiple Teams Working Simultaneously

**Problem**: Data engineer A is working on orders, engineer B is working on customers.

**Without Branches** ❌:
```
Engineer A: Updates orders_silver → Breaks engineer B's work
Engineer B: Updates customers_silver → Conflicts with A's changes
```

**With Branches** ✅:
```
main branch (Production)
  │
  ├── feature-orders branch (Engineer A)
  │     └── orders_silver (new schema: added "discount_applied" column)
  │
  └── feature-customers branch (Engineer B)
        └── customers_silver (new validation: phone number check)
```

Each engineer works independently, then merges to silver when ready.

---

### Scenario 3: Rollback Bad Data

**Problem**: You ran a transformation with a bug. 1 million bad records in Silver.

**Without Branches** ❌:
```
Bad transformation → Silver layer corrupted → Gold layer affected → 
  → Need to re-run entire pipeline from scratch (hours/days)
```

**With Branches** ✅:
```
silver branch
  ├── Commit abc123 (yesterday) ← Good data
  └── Commit def456 (today)     ← Bad data (bug in transformation)

# Simply point to previous commit!
curl -X PUT http://localhost:19120/api/v1/trees/branch/silver \
  -d '{"hash": "abc123"}'  # Rollback to yesterday

# Silver layer instantly back to good state!
```

**Time Travel Query**:
```sql
-- Query data as it was yesterday (before bug)
SELECT COUNT(*) 
FROM nessie.ecommerce.`orders_silver@silver`
AT COMMIT 'abc123'
```

---

## 🔄 How Merging Works in Your Pipeline

### Current Workflow (Your Setup)

You have **isolated branches** for each layer:

```
bronze branch     silver branch     main branch
     ↓                 ↓                ↓
  Raw data      Cleaned data       Aggregated data
```

**Data flows between branches** but **doesn't merge automatically**.

### Example: Promoting Silver to Production (Main)

Let's say you want to merge silver branch changes to main:

```bash
# 1. Create a merge commit
curl -X POST "http://localhost:19120/api/v1/trees/branch/main/merge" \
  -H "Content-Type: application/json" \
  -d '{
    "fromRef": "silver",
    "message": "Merge silver transformations to main"
  }'
```

**What happens**:
- Tables from `silver` branch are now visible on `main` branch
- Main branch gets new commit with silver's changes
- Both branches continue to exist independently

---

## 🎬 Step-by-Step: Real Use Case

### Use Case: Update Customer Segmentation Logic

**Current**: Segments based on lifetime value  
**New**: Segments based on lifetime value + recency

#### Step 1: Create Development Branch
```bash
# Create dev branch from silver
curl -X POST http://localhost:19120/api/v1/trees/tree \
  -d '{"name": "dev-segmentation", "type": "BRANCH", "hash": "<silver-hash>"}'
```

```
silver branch (Production - unchanged)
  └── ecommerce.customers_silver (old logic)

dev-segmentation branch (Testing)
  └── ecommerce.customers_silver (will have new logic)
```

#### Step 2: Test New Logic on Dev Branch
```python
# Run transformation on dev branch
spark.sql("""
  CREATE OR REPLACE TABLE nessie.ecommerce.`customers_silver@dev-segmentation`
  AS SELECT 
    *,
    -- NEW: Add recency score
    DATEDIFF(CURRENT_DATE(), last_order_date) as days_since_last_order,
    CASE 
      WHEN days_since_last_order <= 30 THEN 'Active'
      WHEN days_since_last_order <= 90 THEN 'At Risk'
      ELSE 'Churned'
    END as recency_segment
  FROM nessie.ecommerce.`customers_silver@silver`
""")

# Verify on dev branch
spark.sql("""
  SELECT recency_segment, COUNT(*) 
  FROM nessie.ecommerce.`customers_silver@dev-segmentation`
  GROUP BY recency_segment
""").show()

# Output:
# +------------------+-----+
# |recency_segment   |count|
# +------------------+-----+
# |Active            |89   |
# |At Risk           |42   |
# |Churned           |20   |
# +------------------+-----+
```

✅ **Production (silver branch) still has old logic!**

#### Step 3: Compare Branches
```python
# Production data (silver branch)
old_df = spark.sql("SELECT * FROM nessie.ecommerce.`customers_silver@silver`")
print(f"Production columns: {old_df.columns}")
# Output: [customer_id, name, email, signup_date, is_active, email_valid, data_quality_score]

# Dev data (dev-segmentation branch)
new_df = spark.sql("SELECT * FROM nessie.ecommerce.`customers_silver@dev-segmentation`")
print(f"Dev columns: {new_df.columns}")
# Output: [customer_id, name, email, signup_date, is_active, email_valid, data_quality_score, 
#          days_since_last_order, recency_segment]

# Side-by-side comparison
print(f"Production rows: {old_df.count()}")  # 200
print(f"Dev rows: {new_df.count()}")         # 200
```

#### Step 4: Run Quality Checks on Dev
```python
from utils.quality_checks import QualityChecker

checker = QualityChecker(new_df, "customers_silver_dev")
checker.check_row_count(min_expected=200)
checker.check_nulls(["customer_id", "recency_segment"])
checker.check_duplicates(["customer_id"])
checker.validate(raise_on_failure=True)

# Output:
# ✓ All checks passed!
```

#### Step 5: Merge to Silver (Production)
```bash
# Merge dev branch to silver
curl -X POST "http://localhost:19120/api/v1/trees/branch/silver/merge" \
  -H "Content-Type: application/json" \
  -d '{
    "fromRef": "dev-segmentation",
    "message": "Add recency segmentation to customers"
  }'
```

**Result**:
```
silver branch (NOW has new logic!)
  └── ecommerce.customers_silver (includes recency_segment column)

dev-segmentation branch (can be deleted or kept for history)
  └── ecommerce.customers_silver (same data)
```

#### Step 6: Verify Production Updated
```python
# Check silver branch now has new columns
prod_df = spark.sql("SELECT * FROM nessie.ecommerce.`customers_silver@silver`")
print(prod_df.columns)
# Output: [..., recency_segment] ← NEW COLUMN!

# Production query works
spark.sql("""
  SELECT recency_segment, COUNT(*) 
  FROM nessie.ecommerce.`customers_silver@silver`
  GROUP BY recency_segment
""").show()
```

✅ **New logic is now in production!**  
✅ **You tested it safely first!**

---

## 🔍 Key Differences: Git vs Nessie Branches

### Git (Code Branching)
```
main branch
  ├── feature-login (changes to login.py)
  └── feature-payment (changes to payment.py)

# Merge creates combined code
git merge feature-login  → main has login.py changes
```

### Nessie (Data Branching)
```
main branch
  └── customer_summary table

silver branch
  ├── orders_silver table
  └── customers_silver table

# Branches reference different TABLES, not file changes
# Each branch has its own view of the data catalog
```

**Key Insight**: Nessie branches contain **table references**, not data files.  
The actual Parquet files are in MinIO. Branches just point to different versions.

---

## 💡 Benefits in Your Current Pipeline

### 1. **Layer Isolation**
```
bronze branch: Raw data, never touched after ingestion
  ↓ (read-only for silver)
silver branch: Curated data, can be updated independently
  ↓ (read-only for gold)
main branch: Production aggregations
```

**Why helpful**:
- Bronze data is immutable (audit trail)
- Silver can be re-processed without affecting Gold
- Gold updates don't cascade to Silver/Bronze

### 2. **Safe Experimentation**
```
# Want to test a new deduplication algorithm?
CREATE TABLE nessie.ecommerce.`orders_silver@experiment`
AS SELECT DISTINCT ON (order_id, customer_id) *  -- New logic
FROM nessie.ecommerce.`orders_bronze@bronze`

# Compare
SELECT COUNT(*) FROM nessie.ecommerce.`orders_silver@silver`      -- 1000
SELECT COUNT(*) FROM nessie.ecommerce.`orders_silver@experiment`  -- 950

# If experiment is better, merge it
# If not, just delete the branch
```

### 3. **Parallel Development**
```
main (production)
  ├── dev-team-a (new customer features)
  ├── dev-team-b (new order features)
  └── hotfix (urgent bug fix)

# All teams work independently
# Merge when ready
```

---

## 📝 Common Patterns

### Pattern 1: Dev → Staging → Production
```
dev branch (testing)
  ↓ (merge after QA)
staging branch (pre-production)
  ↓ (merge after approval)
main branch (production)
```

### Pattern 2: Environment-Based Branches
```
bronze-dev, silver-dev, gold-dev (development)
bronze-qa, silver-qa, gold-qa (QA testing)
bronze, silver, gold (production)
```

### Pattern 3: Time-Travel for Debugging
```sql
-- Something wrong with today's data?
-- Query yesterday's version
SELECT * 
FROM nessie.ecommerce.`orders_silver@silver`
AT COMMIT '<yesterday-commit-hash>'

-- Compare
SELECT COUNT(*) FROM ... AT COMMIT 'today'     -- 1050
SELECT COUNT(*) FROM ... AT COMMIT 'yesterday' -- 1000
-- Ah! 50 duplicate records added today
```

---

## 🎯 Summary: How It Helps You

| Scenario | Without Branches | With Branches |
|----------|-----------------|---------------|
| **Test new logic** | Breaks production | Test on dev branch |
| **Rollback bad data** | Re-run entire pipeline | Point to previous commit |
| **Multiple teams** | Conflicts, overwrites | Isolated work, merge later |
| **Audit** | Hard to track changes | Full commit history |
| **Experimentation** | Risky, affects users | Safe, isolated |

---

## 🚀 Try It Yourself

### Exercise: Create a Test Branch

```bash
# 1. Create test branch from silver
python3 << 'EOF'
import requests
NESSIE_URL = "http://localhost:19120/api/v1"

# Get silver branch hash
response = requests.get(f"{NESSIE_URL}/trees/tree/silver")
silver_hash = response.json()['hash']

# Create test branch
requests.post(
    f"{NESSIE_URL}/trees/tree",
    json={"name": "test", "type": "BRANCH", "hash": silver_hash}
)
print("✓ Created test branch!")
EOF

# 2. Write data to test branch
docker exec lakehouse-spark python3 << 'EOF'
from pyspark.sql import SparkSession
import pyspark

conf = (pyspark.SparkConf()
    .setAppName('test-branch')
    .set('spark.jars.packages', 
         'org.apache.iceberg:iceberg-spark-runtime-3.3_2.12:1.3.1,'
         'org.projectnessie.nessie-integrations:nessie-spark-extensions-3.3_2.12:0.67.0,'
         'software.amazon.awssdk:bundle:2.17.178,'
         'software.amazon.awssdk:url-connection-client:2.17.178')
    .set('spark.sql.extensions', 
         'org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions,'
         'org.projectnessie.spark.extensions.NessieSparkSessionExtensions')
    .set('spark.sql.catalog.nessie', 'org.apache.iceberg.spark.SparkCatalog')
    .set('spark.sql.catalog.nessie.uri', 'http://nessie:19120/api/v1')
    .set('spark.sql.catalog.nessie.ref', 'main')
    .set('spark.sql.catalog.nessie.authentication.type', 'NONE')
    .set('spark.sql.catalog.nessie.catalog-impl', 'org.apache.iceberg.nessie.NessieCatalog')
    .set('spark.sql.catalog.nessie.warehouse', 's3a://lakehouse/warehouse')
    .set('spark.sql.catalog.nessie.io-impl', 'org.apache.iceberg.aws.s3.S3FileIO')
    .set('spark.sql.catalog.nessie.s3.endpoint', 'http://minio:9000')
    .set('spark.hadoop.fs.s3a.access.key', 'admin')
    .set('spark.hadoop.fs.s3a.secret.key', 'password123')
    .set('spark.hadoop.fs.s3a.endpoint', 'http://minio:9000')
    .set('spark.hadoop.fs.s3a.path.style.access', 'true')
    .set('spark.hadoop.fs.s3a.connection.ssl.enabled', 'false')
    .set('spark.hadoop.fs.s3a.impl', 'org.apache.hadoop.fs.s3a.S3AFileSystem'))

spark = SparkSession.builder.config(conf=conf).getOrCreate()

# Create test table on test branch
spark.sql("""
    CREATE TABLE IF NOT EXISTS nessie.ecommerce.`test_table@test`
    USING iceberg
    AS SELECT 'Hello from test branch!' as message
""")

print("✓ Created table on test branch!")
spark.stop()
EOF

# 3. Verify isolation
docker exec lakehouse-spark python3 << 'EOF'
from pyspark.sql import SparkSession
import pyspark

conf = (pyspark.SparkConf()
    .setAppName('verify')
    .set('spark.jars.packages', 
         'org.apache.iceberg:iceberg-spark-runtime-3.3_2.12:1.3.1,'
         'org.projectnessie.nessie-integrations:nessie-spark-extensions-3.3_2.12:0.67.0,'
         'software.amazon.awssdk:bundle:2.17.178,'
         'software.amazon.awssdk:url-connection-client:2.17.178')
    .set('spark.sql.extensions', 
         'org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions,'
         'org.projectnessie.spark.extensions.NessieSparkSessionExtensions')
    .set('spark.sql.catalog.nessie', 'org.apache.iceberg.spark.SparkCatalog')
    .set('spark.sql.catalog.nessie.uri', 'http://nessie:19120/api/v1')
    .set('spark.sql.catalog.nessie.ref', 'main')
    .set('spark.sql.catalog.nessie.authentication.type', 'NONE')
    .set('spark.sql.catalog.nessie.catalog-impl', 'org.apache.iceberg.nessie.NessieCatalog')
    .set('spark.sql.catalog.nessie.warehouse', 's3a://lakehouse/warehouse')
    .set('spark.sql.catalog.nessie.io-impl', 'org.apache.iceberg.aws.s3.S3FileIO')
    .set('spark.sql.catalog.nessie.s3.endpoint', 'http://minio:9000')
    .set('spark.hadoop.fs.s3a.access.key', 'admin')
    .set('spark.hadoop.fs.s3a.secret.key', 'password123')
    .set('spark.hadoop.fs.s3a.endpoint', 'http://minio:9000')
    .set('spark.hadoop.fs.s3a.path.style.access', 'true')
    .set('spark.hadoop.fs.s3a.connection.ssl.enabled', 'false')
    .set('spark.hadoop.fs.s3a.impl', 'org.apache.hadoop.fs.s3a.S3AFileSystem'))

spark = SparkSession.builder.config(conf=conf).getOrCreate()

# Read from test branch
print("\n📖 Reading from test branch:")
spark.sql("SELECT * FROM nessie.ecommerce.`test_table@test`").show()

# Try reading from main branch (will fail - table doesn't exist there!)
try:
    spark.sql("SELECT * FROM nessie.ecommerce.`test_table@main`").show()
except Exception as e:
    print("\n✓ Confirmed: Table doesn't exist on main branch (isolation working!)")

spark.stop()
EOF
```

---

**Bottom Line**: Branches give you **Git-like version control for data**. You can experiment, test, rollback, and collaborate safely—just like you do with code! 🎉

