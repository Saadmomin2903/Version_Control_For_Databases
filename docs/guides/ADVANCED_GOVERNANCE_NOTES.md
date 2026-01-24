# Advanced Governance & Maintenance Guide

This document covers "Phase 3+" features mentioned in the Project Vision, focusing on Governance, Maintenance, and "Industry WOW" factors.

---

## 🕰️ Time Travel Debugging

One of the most powerful features of Iceberg + Nessie is the ability to query data as it existed in the past.

### Scenario: "Revenue dropped yesterday. Why?"

You can compare data between two points in time without restoring backups.

**SQL Syntax:**
```sql
-- Query 'orders_silver' as of a specific timestamp
SELECT * FROM nessie.ecommerce.orders_silver TIMESTAMP AS OF '2023-10-25 12:00:00';

-- Query 'orders_silver' as of a specific snapshot ID
SELECT * FROM nessie.ecommerce.orders_silver VERSION AS OF 1234567890;
```

**Nessie Syntax (Commit-based):**
```sql
-- Query data at a specific Nessie commit hash
SELECT * FROM nessie.ecommerce.`orders_silver@<commit_hash>`
```

### Script: Data Diff
You can write a script to automatically diff two versions:

```python
df_today = spark.table("nessie.ecommerce.orders_silver")
df_yesterday = spark.read.option("as-of-timestamp", yesterday_ts).table("nessie.ecommerce.orders_silver")

# Find rows in today that weren't in yesterday
new_rows = df_today.exceptAll(df_yesterday)
```

---

## 🧹 Maintenance: Compaction & Cleanup

Over time, Iceberg tables accumulate small data files and metadata files. Regular maintenance is crucial.

### 1. Compaction (Rewrite Data Files)
Merges small files into larger ones to improve read performance.

```python
# Run this weekly via Airflow
spark.sql("""
    CALL nessie.system.rewrite_data_files(
        table => 'nessie.ecommerce.orders_silver', 
        strategy => 'binpack', 
        options => map('min-input-files','5')
    )
""")
```

### 2. Expire Snapshots
Removes old snapshots to free up storage space (Note: Limits time travel history).

```python
spark.sql("""
    CALL nessie.system.expire_snapshots(
        table => 'nessie.ecommerce.orders_silver', 
        retain_last => 100
    )
""")
```

### 3. Orphan File Removal
Deletes files that are no longer referenced by any snapshot (Garbage Collection).

```python
spark.sql("""
    CALL nessie.system.remove_orphan_files(
        table => 'nessie.ecommerce.orders_silver'
    )
""")
```

---

## 🛡️ Data Contracts (Schema Enforcement)

Ensure that changes to table schemas don't break downstream consumers.

### Implementation Strategy
1.  **Strict Bronze**: Allow schema evolution (new columns formatted as strings).
2.  **Strict Silver**: Enforce types. Reject writes if schema doesn't match.
3.  **Frozen Gold**: No schema changes allowed without a major version bump.

**Iceberg Schema Validation:**
Iceberg automatically handles safe evolution (adding optional columns). For strict enforcement, use the `spark.read.schema(strict_schema)` option in your ETL jobs.

---

## 🚀 Parallel Feature Engineering

Use branches for data science experiments.

**Workflow:**
1.  DS Create Branch: `git/nessie branch feature-eng-v1`
2.  Run Spark Job: Transform `orders_silver` -> `user_features`
3.  Evaluate Model: Train model on `user_features@feature-eng-v1`
4.  Discard or Merge: If model improves, merge `user_features` code (and potentially the table structure) to main.
