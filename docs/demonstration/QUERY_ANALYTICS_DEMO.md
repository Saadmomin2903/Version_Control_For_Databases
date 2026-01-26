# 📊 Query Gold/Silver Tables Demo

## What This Shows

Demonstrates querying aggregated analytics data from the Lakehouse.

---

## 🎯 Demo: Query Top Brands by Revenue

```bash
ssh -i ~/.ssh/oracle-vm1.key ubuntu@140.238.224.207 "docker exec lakehouse-spark python3 -c \"
from pyspark.sql import SparkSession
spark = SparkSession.builder \
    .appName('analytics_query') \
    .config('spark.jars.packages', 'org.apache.iceberg:iceberg-spark-runtime-3.3_2.12:1.3.1,org.projectnessie.nessie-integrations:nessie-spark-extensions-3.3_2.12:0.67.0,org.apache.hadoop:hadoop-aws:3.3.1') \
    .config('spark.sql.extensions', 'org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions,org.projectnessie.spark.extensions.NessieSparkSessionExtensions') \
    .config('spark.sql.catalog.nessie', 'org.apache.iceberg.spark.SparkCatalog') \
    .config('spark.sql.catalog.nessie.uri', 'http://172.18.0.2:19120/api/v1') \
    .config('spark.sql.catalog.nessie.ref', 'silver') \
    .config('spark.sql.catalog.nessie.catalog-impl', 'org.apache.iceberg.nessie.NessieCatalog') \
    .config('spark.sql.catalog.nessie.warehouse', 's3a://lakehouse-prod/warehouse') \
    .config('spark.sql.catalog.nessie.io-impl', 'org.apache.iceberg.hadoop.HadoopFileIO') \
    .config('spark.hadoop.fs.s3a.endpoint', 'https://bmcfe6z38foz.compat.objectstorage.ap-mumbai-1.oraclecloud.com') \
    .config('spark.hadoop.fs.s3a.access.key', '962c9f862226831e4edea90cfcfafb8a8dffcd51') \
    .config('spark.hadoop.fs.s3a.secret.key', 'sd2rGU918DTmn35E4xJ8EV7BX2XUt7DkqC8v6WDNDUw=') \
    .config('spark.hadoop.fs.s3a.path.style.access', 'true') \
    .config('spark.hadoop.fs.s3a.impl', 'org.apache.hadoop.fs.s3a.S3AFileSystem') \
    .config('spark.hadoop.fs.s3a.connection.ssl.enabled', 'true') \
    .getOrCreate()

print('Top Brands by Revenue:')
spark.sql('''
    SELECT brand, 
           ROUND(SUM(price), 2) as total_revenue,
           COUNT(*) as order_count
    FROM nessie.ecommerce.orders_silver 
    WHERE brand IS NOT NULL
    GROUP BY brand 
    ORDER BY total_revenue DESC 
    LIMIT 10
''').show(truncate=False)

spark.stop()
\""
```

---

## Expected Output

```
+-------+--------------+-----------+
|brand  |total_revenue |order_count|
+-------+--------------+-----------+
|apple  |188,733,445   |207,758    |
|samsung|148,047,820   |415,650    |
|acer   |64,518,874    |110,218    |
|asus   |54,237,207    |104,963    |
|lenovo |52,098,901    |101,281    |
|hp     |48,835,788    |89,881     |
|xiaomi |37,423,553    |148,407    |
|lg     |20,400,682    |39,975     |
|huawei |19,950,307    |82,940     |
|sony   |19,935,613    |42,860     |
+-------+--------------+-----------+
```

---

## 💼 Business Value

| Insight | Value |
|---------|-------|
| Top brand by revenue | Apple ($188M) |
| Most orders | Samsung (415K) |
| Total analyzed | 3.1M orders |

---

## 🎤 Presentation Script

> "Now let me query our analytics layer to show real business insights."
>
> *[Run query]*
>
> "From 3 million e-commerce events, we can instantly see:"
> - **Apple** leads with $188 million revenue
> - **Samsung** has the most orders at 415 thousand
>
> "This data is **version controlled** - we can compare to yesterday, last week, or any historical point."
