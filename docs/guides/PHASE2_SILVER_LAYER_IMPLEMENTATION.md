# Phase 2: Silver Layer Implementation Guide

The **Silver Layer** represents refined, cleaned, and enriched data. It is the "Enterprise View" of your data, suitable for ad-hoc querying and downstream analytics.

---

## 🎯 Objective

1.  **Read from Bronze**: Source data from `orders_bronze@bronze`.
2.  **Transform**: Clean data, add computed columns.
3.  **Write to Silver**: Save to `orders_silver@silver`.
4.  **Quality Checks**: Enforce data contracts.

---

## 🔄 Transformations

We will apply the following transformations:
- **Deduplication**: Remove duplicate records based on `order_id` (if present) or `event_time`/`user_id`.
- **Cleaning**: Ensure `price` is not negative.
- **Enrichment**:
    - `is_purchase`: Boolean flag.
    - `category_level1`: Extracted from `category_code` (e.g., `electronics` from `electronics.smartphone`).

---

## 🛠️ Step 1: Create Silver Branch

Always isolate transformation logic on its own branch first.

```bash
python3 scripts/utils/create_nessie_branches.py --branch silver --source main
```

---

## 📝 Script: `scripts/silver/transform_orders_silver.py`

```python
from pyspark.sql import SparkSession
from pyspark.sql import functions as F

def create_spark_session():
    # ... (Same config as Bronze) ...
    return SparkSession.builder.appName("Silver_Transformation").getOrCreate() # Placeholder for full config

def transform_silver(spark):
    print("🔄 Reading from Bronze...")
    # NOTE: Reading specifically from the BRONZE branch reference
    df_bronze = spark.sql("SELECT * FROM nessie.ecommerce.`orders_bronze@bronze`")

    # 1. Deduplicate
    df_dedup = df_bronze.dropDuplicates(["event_time", "user_id", "product_id"])

    # 2. Transformations
    df_silver = df_dedup \
        .withColumn("is_purchase", F.col("event_type") == "purchase") \
        .withColumn("category_level1", F.split(F.col("category_code"), "\.").getItem(0)) \
        .filter(F.col("price") >= 0) \
        .withColumn("processed_at", F.current_timestamp())

    # 3. Quality Check (In-line)
    if df_silver.count() == 0:
        raise Exception("❌ Transformation resulted in empty dataset!")

    # 4. Write to Silver Branch
    print("💾 Writing to nessie.ecommerce.`orders_silver@silver`...")
    df_silver.writeTo("nessie.ecommerce.`orders_silver@silver`") \
        .using("iceberg") \
        .createOrReplace()
        
    print("✅ Silver Transformation Complete!")

if __name__ == "__main__":
    spark = create_spark_session()
    transform_silver(spark)
    spark.stop()
```

---

## ⚡ Comparison: Bronze vs. Silver

| Feature | Bronze (`orders_bronze`) | Silver (`orders_silver`) |
|---------|--------------------------|--------------------------|
| **Source** | Raw CSV/Parquet | `orders_bronze` |
| **Schema** | Flexible (all strings allowed) | Enforced Types |
| **Cleaning**| None (Raw) | Filtered (price > 0), Deduped |
| **Augmented**| No | Yes (`is_purchase`, `category_level1`) |
| **Branch** | `bronze` | `silver` |

---

## 🏃 Execution

```bash
docker exec lakehouse-spark python3 /home/jovyan/scripts/silver/transform_orders_silver.py
```

---

## 🧩 Next Steps

Once the Silver layer is populated and verified, you can proceed to **Phase 3: Gold Layer Aggregations**.
