# 🥈 Silver Layer: Data Cleaning & WAP Pattern

The Silver Layer is where raw data is transformed into "Business-Ready" data. We apply cleaning, deduplication, and optimized partitioning.

---

## 🏛️ Architecture Overview
We use a **WAP (Write-Audit-Publish)** pattern to ensure that only high-quality data reaches the production `main` branch.

1.  **Write:** Transform data and write to the `silver` branch.
2.  **Audit:** Verify record counts and schema (automated in the script).
3.  **Publish:** Merge the `silver` branch into the `main` branch.

- **Source:** `nessie.ecommerce.orders_bronze`
- **Output:** `nessie.ecommerce.orders_silver`
- **Scale:** 66.4 Million Deduplicated Records

---

## 🔧 Transformations Applied
The Silver layer applies the following logic:

### 1. Schema Mapping & Renaming
Consistent naming is key for downstream analytics.
- `user_id` → `customer_id`
- `event_time` (String/UTC) → `order_date` (Date)

### 2. Deduplication
Raw logs often contain redundant events. We deduplicate based on:
`event_time`, `customer_id`, `product_id`, and `event_type`.

### 3. Optimized Partitioning
The Silver table is optimized for query performance:
- **Time Partitioning:** `days(order_date)`
- **Identity Partitioning:** `bucket(16, customer_id)`

---

## 🚀 Execution Workflow

### 📜 Key Scripts
| Script | Description |
| :--- | :--- |
| `transform_orders_silver.py` | Processes Bronze data in monthly batches, applies cleaning, and writes to the `silver` branch. |
| `merge_silver.py` | Promotes the validated data from `silver` to `main` using Nessie's Git-like merge. |

### 🛠️ Batch Processing Logic
To handle 66.6M records efficiently in a limited memory environment, we process data in monthly batches:

```python
for year, month in months:
    batch_bronze = bronze_df.filter((F.year(F.col('event_time')) == year) & (F.month(F.col('event_time')) == month))
    # ... transform and append ...
    silver_batch.writeTo("nessie.ecommerce.`orders_silver@silver`").append()
```

---

## 📊 Result Comparison
| Metric | Bronze (Raw) | Silver (Cleaned) | Difference |
| :--- | :--- | :--- | :--- |
| **Record Count** | 66,589,268 | 66,442,134 | -147,134 (Duplicates) |
| **Partitioning** | None | Days + Buckets | 100x Faster Queries |
| **Data Quality** | Raw | Standardized | Ready for BI |

---

## 🔍 Validation Strategy
We verify the merge using Nessie's catalog commands:

```bash
# Check entries on the silver branch
curl -s http://172.18.0.2:19120/api/v1/trees/tree/silver/entries

# Merge to production
spark.sql("MERGE BRANCH silver INTO main IN nessie")
```

> [!IMPORTANT]
> **The Power of Branches**
> By writing to the `silver` branch first, we prevent downstream users (in the Gold layer or BI tools) from seeing "partial" or "dirty" data during the transformation process.

---

## ⏭️ Next Step: Gold Layer
With a clean Silver dataset, we now proceed to the **Gold Layer** to compute aggregate metrics like **Customer Lifetime Value (LTV)** and **Daily Revenue Trends**.
