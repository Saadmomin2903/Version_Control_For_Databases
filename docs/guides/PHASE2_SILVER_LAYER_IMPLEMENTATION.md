# Phase 2: Silver Layer Implementation Guide

## Objective
To transform raw, unpartitioned Bronze data (411M+ records) into a clean, optimized, and partitioned **Silver Layer**, ready for analytics.

## Success Criteria
- [x] **Data Cleaning**: Deduplicated and schema-validated.
- [x] **Partitioning**: `days(order_date)` and `bucket(16, customer_id)` applied for query performance.
- [x] **Storage**: Data stored in Iceberg format on Oracle Object Storage.
- [x] **WAP Pattern**: Changes made on `silver` branch, verified, and merged to `main`.
- [x] **Optimization**: Successfully processed 411M records on a single node (12GB RAM) using **Batched Writes**.

---

## 1. Strategy & Architecture

### The Challenge: Single Node Capacity
We are running Spark on a single VM (`spark-master`) with ~12GB RAM and 45GB Disk.
- **Problem**: A naive "Read 411M -> Sort -> Write" job triggered a global shuffle that required >36GB of temporary disk space, causing `java.io.IOException: No space left on device`.
- **Solution**: **Batched Processing**. We iterated through the data month-by-month (e.g., `2019-10`, `2019-11`), processing ~70M records at a time. This kept peak resource usage low.

### Schema Transformation
| Bronze Column | Silver Transformation | Reason |
| :--- | :--- | :--- |
| `event_time` | `event_time` (Timestamp) | Preserved |
| `user_id` | `customer_id` (String) | **Renamed** to match Project Vision (Star Schema) |
| - | `order_date` (Date) | **Derived** `to_date(event_time)` for Partitioning |
| `price` | `price` (Double) | Verified >= 0 |
| `product_id` | `product_id` (Long) | Typed |
| - | `data_quality_score` | **Computed** (100 if clean, 50 if missing fields) |

---

## 2. Implementation Steps

### Step 1: Create Silver Branch
We isolated our work to keep `main` clean.
```bash
nessie branch silver
```

### Step 2: The Optimized Transformation Script
Located at: `scripts/silver/transform_orders_silver.py`

**Key Logic (Batched Write):**
```python
# 1. Create Empty Table with Correct Partitioning
spark.sql("""
    CREATE TABLE nessie.ecommerce.`orders_silver@silver`
    USING iceberg
    PARTITIONED BY (days(order_date), bucket(16, customer_id))
    AS SELECT * FROM silver_structure
""")

# 2. Iterate months
months = ['2019-10', '2019-11', ...]
for month in months:
    # Filter -> Dedup -> Append
    batch_df = silver_final.filter(F.col("event_time").like(f"{month}%"))
    batch_df.writeTo("nessie.ecommerce.`orders_silver@silver`").append()
```

### Step 3: Verification (Quality Checks)
We ran automated checks embedded in the script:
- **Duplicates**: Removed ~1.6M duplicates.
- **Nulls**: Verified 0 nulls in `event_time` and `customer_id`.
- **Count**: Verified **410,104,956** records written.

### Step 4: The Merge (Write-Audit-Publish)
Once verified, we merged the changes to Production (`main`).
Script: `scripts/silver/merge_silver.py`

```python
spark.sql("MERGE BRANCH silver INTO main IN nessie")
```

### Step 5: Post-Merge Smart Audit
To strictly validate the Production state, we created a dedicated audit script:
`scripts/silver/audit_silver_quality.py`

**Audit Results:**
- **Final Row Count**: 410,104,956
- **Critical Nulls**: 0 (Passed)
- **Negative Prices**: 0 (Passed)
- **Duplicate Check**: Passed (Verified on sample partition)

---

## 3. Results & Verification

### Final Table Location
- **Catalog**: `nessie`
- **Namespace**: `ecommerce`
- **Table**: `orders_silver`
- **Branch**: `main` (and `silver`)

### Performance Statistics
- **Input Records**: 411,709,736
- **Cleaned Records**: 410,104,956
- **Partition Strategy**: Date-based + Customer Bucketing (Optimized for excessive user filtering).

---

## 4. Next Steps (Gold Layer)
Now that we have verified Silver data:
1.  **Create `gold` branch**.
2.  Aggregate Silver data into Business KPIs:
    - `daily_sales`
    - `customer_ltv`
    - `product_performance`
3.  Publish Gold tables to `main`.
