# Phase 4: Write-Audit-Publish (WAP) Implementation Guide

This guide details how to implement the **Write-Audit-Publish** pattern using Nessie branches and Spark. This is a core feature of your production lakehouse that ensures data quality isolation.

---

## 🎯 Objective

Demonstrate the safety of the Lakehouse architecture by:
1.  Creating an isolated feature branch (`experiment-v1`).
2.  Making changes (e.g., adding a new column or filtering data) on that branch.
3.  Verifying the changes *without* affecting the main branch.
4.  Merging the changes only after validation checks pass.

---

## 🛠️ Step 1: Create a Feature Branch

We will create a branch named `wap_demo_etl` from `main`.

**Command:**
```bash
# Using Nessie CLI or API (via our python helper)
python3 scripts/utils/create_nessie_branches.py --branch wap_demo_etl --source main
```

*Or manually in Python:*
```python
# In a Spark/Python script
spark.sql("CREATE BRANCH IF NOT EXISTS wap_demo_etl IN nessie FROM main")
```

---

## 🧪 Step 2: Write Data to the Branch (Write)

We will create a modified version of the `daily_sales_summary` table on this branch. Let's say we want to filter out low-value orders (< $10).

**Spark SQL:**
```sql
-- Switch context to the new branch
USE REFERENCE wap_demo_etl IN nessie;

-- Perform the Transformation (Write)
CREATE OR REPLACE TABLE nessie.ecommerce.daily_sales_high_value 
USING iceberg AS
SELECT * 
FROM nessie.ecommerce.daily_sales_summary
WHERE avg_order_value > 10;
```

**Verification of Isolation:**
Open two terminal windows/Spark sessions.
1.  Session A (`ref=main`): `SELECT * FROM nessie.ecommerce.daily_sales_high_value` -> **Should Fail** (Table doesn't exist here).
2.  Session B (`ref=wap_demo_etl`): `SELECT * FROM nessie.ecommerce.daily_sales_high_value` -> **Should Succeed**.

---

## 🔍 Step 3: Audit the Data (Audit)

Run quality checks on the data in the `wap_demo_etl` branch.

**Quality Check Logic:**
1.  Row Count > 0
2.  No Nulls in PK
3.  Avg Order Value > 10 (since that was our filter)

**Python Script (`scripts/wap/audit_branch.py`):**
```python
branch = "wap_demo_etl"
df = spark.sql(f"SELECT * FROM nessie.ecommerce.daily_sales_high_value@{branch}")

# Check 1: Row Count
count = df.count()
if count == 0:
    raise Exception("Audit Failed: Table is empty!")

# Check 2: Logic
invalid_rows = df.filter("avg_order_value <= 10").count()
if invalid_rows > 0:
    raise Exception(f"Audit Failed: Found {invalid_rows} rows with low value!")

print("✅ AUDIT PASSED")
```

---

## 🚀 Step 4: Publish to Main (Publish)

Once the audit passes, merge the branch into `main`.

**Command:**
```bash
# Using our helper (we'll need to create a merge script if not exists, or use Spark SQL)
```

**Spark SQL Merge:**
```sql
MERGE BRANCH wap_demo_etl INTO main IN nessie;
```

**Python Way:**
```python
spark.sql("MERGE BRANCH wap_demo_etl INTO main IN nessie")
```

---

## 📝 WAP Demo Script

Create `scripts/wap/run_wap_demo.py` to automate this flow:

```python
import time
from pyspark.sql import SparkSession

def get_spark():
    # ... Standard Spark Config ...
    return SparkSession.builder.appName("WAP_Demo").getOrCreate() # (Add full config)

def run_demo():
    spark = get_spark()
    
    # 1. Create Branch
    print("🌿 Creating branch 'wap_demo'...")
    spark.sql("DROP BRANCH IF EXISTS wap_demo IN nessie")
    spark.sql("CREATE BRANCH wap_demo IN nessie FROM main")
    
    # 2. Write (Simulate ETL)
    print("✍️  Writing data to 'wap_demo'...")
    spark.sql("USE REFERENCE wap_demo IN nessie")
    spark.sql("""
        CREATE OR REPLACE TABLE nessie.ecommerce.wap_test_table 
        USING iceberg 
        AS SELECT * FROM nessie.ecommerce.orders_bronze LIMIT 100
    """)
    
    # 3. Audit
    print("🔍 Auditing data...")
    count = spark.sql("SELECT COUNT(*) FROM nessie.ecommerce.wap_test_table").collect()[0][0]
    print(f"   Row count: {count}")
    
    if count == 100:
        print("✅ Audit Passed!")
        
        # 4. Publish
        print("🚀 Publishing to main...")
        spark.sql("USE REFERENCE main IN nessie")
        spark.sql("MERGE BRANCH wap_demo INTO main IN nessie")
        print("✅ Merge Complete. WAP Pattern Successful.")
        
    else:
        print("❌ Audit Failed. Rolling back (not merging).")

if __name__ == "__main__":
    run_demo()
```
