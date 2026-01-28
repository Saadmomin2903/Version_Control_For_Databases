# 🥈 Silver Layer: Data Cleaning & WAP Pattern

The Silver Layer is where raw data is transformed into "Business-Ready" data. We apply advanced cleaning, deduplication, and optimized partitioning while maintaining absolute data integrity using the **WAP (Write-Audit-Publish)** pattern.

---

## 🏛️ Architecture & Governance
We use **Project Nessie** to maintain a "Git-for-Data" workflow. In this layer, we isolate massive transformations on the `silver` branch to ensure the `main` branch remains a stable source of truth.

- **Source:** `nessie.ecommerce.orders_bronze@bronze`
- **Output:** `nessie.ecommerce.orders_silver` & `nessie.ecommerce.customers_silver`
- **Catalog:** Nessie (Versioned)
- **Format:** Iceberg (V2)

### 🛡️ The WAP Pattern
1.  **Write:** Perform complex transformations and write to the isolated `silver` branch.
2.  **Audit:** Verify record counts, schema integrity, and distribution (Verified: **300.3M Orders**, **13.3M Customers**).
3.  **Publish:** Transparently merge the `silver` branch into `main` using Nessie's atomic merge operation.

---

## 📊 Production Statistics (Full Dataset)
Our Silver layer processing for the 12-month period (Dec 2019 - Nov 2020) has yielded the following results:

| Table | Status | Records | Transformation Details |
| :--- | :--- | :--- | :--- |
| `orders_silver` | ✅ COMPLETE | 300,298,449 | Deduplicated, Partitioned by Day, Standardized Schema. |
| `customers_silver` | ✅ COMPLETE | 13,283,688 | Synthesized from Orders (Unique identities), Generated Master Data. |

---

## 🔧 Transformations Applied

### 1. Schema Standardization
Standardizing field names and types for downstream BI and ML compatibility:
- **Identifier Mapping:** `user_id` → `customer_id` (Integer)
- **Temporal Cleaning:** `event_time` (String) → `order_date` (Date) + `event_time` (Timestamp)
- **Null Management:** Removed invalid records with missing identifiers.

### 2. High-Fidelity Deduplication
Raw Bronze data often contains redundant clickstream events. We apply a window-based deduplication strategy:
```python
# Logic: Deduplicate based on time, identity, and action
deduped_df = window_df.withColumn("row_num", row_number().over(
    Window.partitionBy("customer_id", "product_id", "event_time", "event_type").orderBy("event_time")
)).filter("row_num == 1").drop("row_num")
```

### 3. Synthesis of Customer Dimension
Since the original customers source was unavailable, we extracted unique identities from the 301M orders and synthesized a master record for each:
- **Extracted:** 13.3M unique customer IDs.
- **Generated:** Consistent names, emails, and signup dates to unblock Gold layer segmentation.

---

## 📓 Interactive Exploration (Jupyter)

### 🚀 Step 1: Initialize Silver-Aware Spark
```python
from pyspark.sql import SparkSession

spark = SparkSession.builder \
    .appName("Silver-Layer-Explorer") \
    .config("spark.sql.catalog.nessie.ref", "silver") \
    .config("spark.sql.catalog.nessie.uri", "http://140.238.224.207:19120/api/v1") \
    # ... additional S3/Iceberg configs from Bronze guide ...
    .getOrCreate()
```

### 📊 Step 2: Query the Cleaned Data
```python
# Count deduplicated orders
spark.sql("SELECT count(*) FROM nessie.ecommerce.orders_silver").show()

# Sample the synthetic Customer Master
spark.sql("SELECT * FROM nessie.ecommerce.customers_silver LIMIT 5").show()
```

---

## 🌿 Branching Logic: How We Transition
The transition from Silver to Main is managed by a dedicated merge script:

```python
# MERGE BRANCH silver INTO main IN nessie
spark.sql("MERGE BRANCH silver INTO main IN nessie")
```

> [!TIP]
> **Data Quality Assurance**
> If the Silver transformation had failed or produced incorrect data, we could simply **DROP** the `silver` branch without ever touching production data on `main`. This is the core benefit of Lakehouse versioning.

---

## 🔍 Validation Matrix
| Strategy | Method | Result | 
| :--- | :--- | :--- |
| **Record Integrity** | Bronze vs Silver Count | **-1.46M Duplicates Found & Dropped** |
| **Schema Validation** | Iceberg Schema Check | Matches Gold Layer Requirements |
| **Identity Clarity** | Unique Customer Extraction | **13,283,688 Verified Identities** |

---

## ⏭️ Next Step: Gold Layer
The landscape is now clean. We proceed to the **Gold Layer** to build aggregated value tables:
- `daily_sales_performance`
- `customer_segmentation`
- `brand_loyalty_metrics`
