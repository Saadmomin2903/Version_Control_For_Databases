"""
Full ML Pipeline - Production Run
Creates Gold/Platinum layer tables from ACTUAL orders_silver data
Uses Spark SQL to read Iceberg tables via Nessie catalog
"""

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.window import Window

# S3 Config
AWS_ACCESS_KEY = "962c9f862226831e4edea90cfcfafb8a8dffcd51"
AWS_SECRET_KEY = "sd2rGU918DTmn35E4xJ8EV7BX2XUt7DkqC8v6WDNDUw="
AWS_S3_ENDPOINT = "https://bmcfe6z38foz.compat.objectstorage.ap-mumbai-1.oraclecloud.com"
AWS_REGION = "ap-mumbai-1"
NESSIE_URI = "http://172.18.0.2:19120/api/v1"
WAREHOUSE = "s3a://lakehouse-prod/warehouse"

print("🚀 Starting FULL ML Pipeline with Actual Data...")

spark = (SparkSession.builder
    .appName("full-ml-pipeline")
    .config("spark.sql.catalog.nessie", "org.apache.iceberg.spark.SparkCatalog")
    .config("spark.sql.catalog.nessie.uri", NESSIE_URI)
    .config("spark.sql.catalog.nessie.ref", "main")
    .config("spark.sql.catalog.nessie.catalog-impl", "org.apache.iceberg.nessie.NessieCatalog")
    .config("spark.sql.catalog.nessie.warehouse", WAREHOUSE)
    .config("spark.sql.catalog.nessie.io-impl", "org.apache.iceberg.aws.s3.S3FileIO")
    .config("spark.sql.catalog.nessie.s3.endpoint", AWS_S3_ENDPOINT)
    .config("spark.sql.catalog.nessie.s3.region", AWS_REGION)
    .config("spark.sql.catalog.nessie.s3.path-style-access", "true")
    .config("spark.sql.catalog.nessie.s3.access-key-id", AWS_ACCESS_KEY)
    .config("spark.sql.catalog.nessie.s3.secret-access-key", AWS_SECRET_KEY)
    .config("spark.sql.catalog.nessie.client.region", AWS_REGION)
    .config("spark.hadoop.fs.s3a.access.key", AWS_ACCESS_KEY)
    .config("spark.hadoop.fs.s3a.secret.key", AWS_SECRET_KEY)
    .config("spark.hadoop.fs.s3a.endpoint", AWS_S3_ENDPOINT)
    .config("spark.hadoop.fs.s3a.path.style.access", "true")
    .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem")
    .config("spark.sql.shuffle.partitions", "20")
    .config("spark.driver.memory", "4g")
    .config("spark.executor.memory", "4g")
    .getOrCreate())

print("✅ Spark Session Created")

try:
    # Read source data via SQL - sample for faster processing
    print("\n📊 Reading orders_silver via Nessie catalog...")
    print("   Fetching sample of 500,000 records...")
    
    # Use SQL to read a sample
    orders_df = spark.sql("""
        SELECT 
            customer_id,
            product_id,
            brand,
            category_code,
            price,
            order_date
        FROM nessie.ecommerce.orders_silver 
        LIMIT 500000
    """)
    
    sample_count = orders_df.count()
    print(f"   ✅ Loaded {sample_count:,} records")
    
    # Cache for reuse
    orders_df.cache()
    orders_df.createOrReplaceTempView("orders")
    
    # ============================================
    # Stage 1: Product Recommendations (Co-purchase analysis)
    # ============================================
    print("\n📌 Stage 1/5: Creating product_recommendations_full...")
    
    # Find products frequently bought by same customer
    recommendations = spark.sql("""
        WITH customer_products AS (
            SELECT customer_id, collect_set(product_id) as products
            FROM orders
            GROUP BY customer_id
            HAVING size(collect_set(product_id)) >= 2
        ),
        product_pairs AS (
            SELECT 
                products[i] as product_a,
                products[j] as product_b
            FROM customer_products
            LATERAL VIEW posexplode(products) t1 AS i, pa
            LATERAL VIEW posexplode(products) t2 AS j, pb
            WHERE i < j
        )
        SELECT 
            product_a,
            product_b,
            COUNT(*) as co_purchase_count,
            ROUND(COUNT(*) / SUM(COUNT(*)) OVER (PARTITION BY product_a), 4) as confidence
        FROM product_pairs
        GROUP BY product_a, product_b
        HAVING co_purchase_count >= 3
        ORDER BY co_purchase_count DESC
        LIMIT 10000
    """)
    
    recommendations.writeTo("nessie.ecommerce.product_recommendations_full").createOrReplace()
    rec_count = recommendations.count()
    print(f"   ✅ product_recommendations_full created ({rec_count:,} pairs)")
    
    # ============================================
    # Stage 2: Customer Segmentation (RFM Analysis)
    # ============================================
    print("\n📌 Stage 2/5: Creating customer_segments_full (RFM)...")
    
    rfm_segments = spark.sql("""
        WITH rfm AS (
            SELECT 
                customer_id,
                DATEDIFF(current_date(), MAX(order_date)) as recency_days,
                COUNT(*) as frequency,
                SUM(price) as monetary_value,
                AVG(price) as avg_order_value,
                COUNT(DISTINCT product_id) as unique_products,
                COUNT(DISTINCT brand) as unique_brands,
                MIN(order_date) as first_purchase,
                MAX(order_date) as last_purchase
            FROM orders
            WHERE customer_id IS NOT NULL
            GROUP BY customer_id
        ),
        rfm_scored AS (
            SELECT *,
                CASE 
                    WHEN recency_days <= 7 THEN 5
                    WHEN recency_days <= 14 THEN 4
                    WHEN recency_days <= 30 THEN 3
                    WHEN recency_days <= 60 THEN 2
                    ELSE 1
                END as r_score,
                CASE 
                    WHEN frequency >= 10 THEN 5
                    WHEN frequency >= 5 THEN 4
                    WHEN frequency >= 3 THEN 3
                    WHEN frequency >= 2 THEN 2
                    ELSE 1
                END as f_score,
                CASE 
                    WHEN monetary_value >= 1000 THEN 5
                    WHEN monetary_value >= 500 THEN 4
                    WHEN monetary_value >= 200 THEN 3
                    WHEN monetary_value >= 100 THEN 2
                    ELSE 1
                END as m_score
            FROM rfm
        )
        SELECT *,
            (r_score + f_score + m_score) as rfm_score,
            CASE 
                WHEN (r_score + f_score + m_score) >= 13 THEN 'Champions'
                WHEN (r_score + f_score + m_score) >= 10 THEN 'Loyal Customers'
                WHEN (r_score + f_score + m_score) >= 7 THEN 'Potential Loyalists'
                WHEN (r_score + f_score + m_score) >= 5 THEN 'At Risk'
                ELSE 'Need Attention'
            END as segment
        FROM rfm_scored
    """)
    
    rfm_segments.writeTo("nessie.ecommerce.customer_segments_full").createOrReplace()
    seg_count = rfm_segments.count()
    print(f"   ✅ customer_segments_full created ({seg_count:,} customers)")
    
    # Cache segments for downstream use
    rfm_segments.createOrReplaceTempView("segments")
    
    # ============================================
    # Stage 3: Churn Predictions
    # ============================================
    print("\n📌 Stage 3/5: Creating churn_predictions_full...")
    
    churn_predictions = spark.sql("""
        SELECT 
            customer_id,
            recency_days,
            frequency,
            monetary_value,
            ROUND(
                LEAST(
                    CASE 
                        WHEN recency_days >= 90 THEN 0.9
                        WHEN recency_days >= 60 THEN 0.7
                        WHEN recency_days >= 30 THEN 0.4
                        WHEN recency_days >= 14 THEN 0.2
                        ELSE 0.1
                    END *
                    CASE 
                        WHEN frequency <= 1 THEN 1.2
                        WHEN frequency <= 2 THEN 1.0
                        ELSE 0.8
                    END,
                    1.0
                ), 
                2
            ) as churn_probability,
            CASE 
                WHEN LEAST(
                    CASE 
                        WHEN recency_days >= 90 THEN 0.9
                        WHEN recency_days >= 60 THEN 0.7
                        WHEN recency_days >= 30 THEN 0.4
                        WHEN recency_days >= 14 THEN 0.2
                        ELSE 0.1
                    END *
                    CASE 
                        WHEN frequency <= 1 THEN 1.2
                        WHEN frequency <= 2 THEN 1.0
                        ELSE 0.8
                    END,
                    1.0
                ) >= 0.7 THEN 'High'
                WHEN LEAST(
                    CASE 
                        WHEN recency_days >= 90 THEN 0.9
                        WHEN recency_days >= 60 THEN 0.7
                        WHEN recency_days >= 30 THEN 0.4
                        WHEN recency_days >= 14 THEN 0.2
                        ELSE 0.1
                    END *
                    CASE 
                        WHEN frequency <= 1 THEN 1.2
                        WHEN frequency <= 2 THEN 1.0
                        ELSE 0.8
                    END,
                    1.0
                ) >= 0.4 THEN 'Medium'
                ELSE 'Low'
            END as risk_category,
            current_timestamp() as prediction_date
        FROM segments
    """)
    
    churn_predictions.writeTo("nessie.ecommerce.churn_predictions_full").createOrReplace()
    churn_count = churn_predictions.count()
    print(f"   ✅ churn_predictions_full created ({churn_count:,} predictions)")
    
    # ============================================
    # Stage 4: CLV Predictions
    # ============================================
    print("\n📌 Stage 4/5: Creating clv_predictions_full...")
    
    clv_predictions = spark.sql("""
        SELECT 
            customer_id,
            monetary_value,
            ROUND(
                CASE 
                    WHEN DATEDIFF(last_purchase, first_purchase) > 0 
                    THEN monetary_value / (DATEDIFF(last_purchase, first_purchase) / 30)
                    ELSE monetary_value
                END,
                2
            ) as avg_monthly_spend,
            ROUND(
                CASE 
                    WHEN DATEDIFF(last_purchase, first_purchase) > 0 
                    THEN monetary_value / (DATEDIFF(last_purchase, first_purchase) / 30)
                    ELSE monetary_value
                END * 12 *
                CASE 
                    WHEN segment = 'Champions' THEN 1.2
                    WHEN segment = 'Loyal Customers' THEN 1.0
                    WHEN segment = 'Potential Loyalists' THEN 0.8
                    WHEN segment = 'At Risk' THEN 0.5
                    ELSE 0.3
                END,
                2
            ) as predicted_clv_12m,
            CASE 
                WHEN (
                    CASE 
                        WHEN DATEDIFF(last_purchase, first_purchase) > 0 
                        THEN monetary_value / (DATEDIFF(last_purchase, first_purchase) / 30)
                        ELSE monetary_value
                    END * 12 *
                    CASE 
                        WHEN segment = 'Champions' THEN 1.2
                        WHEN segment = 'Loyal Customers' THEN 1.0
                        WHEN segment = 'Potential Loyalists' THEN 0.8
                        WHEN segment = 'At Risk' THEN 0.5
                        ELSE 0.3
                    END
                ) >= 2000 THEN 'Platinum'
                WHEN (
                    CASE 
                        WHEN DATEDIFF(last_purchase, first_purchase) > 0 
                        THEN monetary_value / (DATEDIFF(last_purchase, first_purchase) / 30)
                        ELSE monetary_value
                    END * 12 *
                    CASE 
                        WHEN segment = 'Champions' THEN 1.2
                        WHEN segment = 'Loyal Customers' THEN 1.0
                        WHEN segment = 'Potential Loyalists' THEN 0.8
                        WHEN segment = 'At Risk' THEN 0.5
                        ELSE 0.3
                    END
                ) >= 1000 THEN 'Gold'
                WHEN (
                    CASE 
                        WHEN DATEDIFF(last_purchase, first_purchase) > 0 
                        THEN monetary_value / (DATEDIFF(last_purchase, first_purchase) / 30)
                        ELSE monetary_value
                    END * 12 *
                    CASE 
                        WHEN segment = 'Champions' THEN 1.2
                        WHEN segment = 'Loyal Customers' THEN 1.0
                        WHEN segment = 'Potential Loyalists' THEN 0.8
                        WHEN segment = 'At Risk' THEN 0.5
                        ELSE 0.3
                    END
                ) >= 500 THEN 'Silver'
                ELSE 'Bronze'
            END as value_tier,
            segment,
            current_timestamp() as prediction_date
        FROM segments
    """)
    
    clv_predictions.writeTo("nessie.ecommerce.clv_predictions_full").createOrReplace()
    clv_count = clv_predictions.count()
    print(f"   ✅ clv_predictions_full created ({clv_count:,} predictions)")
    
    # ============================================
    # Stage 5: Next Purchase Predictions
    # ============================================
    print("\n📌 Stage 5/5: Creating next_purchase_predictions_full...")
    
    next_purchase = spark.sql("""
        WITH purchase_intervals AS (
            SELECT 
                customer_id,
                order_date,
                LAG(order_date) OVER (PARTITION BY customer_id ORDER BY order_date) as prev_date
            FROM (SELECT DISTINCT customer_id, order_date FROM orders)
        ),
        avg_intervals AS (
            SELECT 
                customer_id,
                AVG(DATEDIFF(order_date, prev_date)) as avg_purchase_interval
            FROM purchase_intervals
            WHERE prev_date IS NOT NULL
            GROUP BY customer_id
        )
        SELECT 
            s.customer_id,
            s.last_purchase,
            COALESCE(a.avg_purchase_interval, 30) as avg_purchase_interval,
            GREATEST(
                CAST(COALESCE(a.avg_purchase_interval, 30) - s.recency_days AS INT),
                1
            ) as predicted_days_to_next,
            DATE_ADD(current_date(), 
                GREATEST(
                    CAST(COALESCE(a.avg_purchase_interval, 30) - s.recency_days AS INT),
                    1
                )
            ) as predicted_next_date,
            CASE 
                WHEN GREATEST(CAST(COALESCE(a.avg_purchase_interval, 30) - s.recency_days AS INT), 1) <= 7 THEN 'High'
                WHEN GREATEST(CAST(COALESCE(a.avg_purchase_interval, 30) - s.recency_days AS INT), 1) <= 21 THEN 'Medium'
                ELSE 'Low'
            END as purchase_urgency,
            current_timestamp() as prediction_date
        FROM segments s
        LEFT JOIN avg_intervals a ON s.customer_id = a.customer_id
    """)
    
    next_purchase.writeTo("nessie.ecommerce.next_purchase_predictions_full").createOrReplace()
    npp_count = next_purchase.count()
    print(f"   ✅ next_purchase_predictions_full created ({npp_count:,} predictions)")
    
    # ============================================
    # Summary
    # ============================================
    print("\n🎉 ALL 5 STAGES COMPLETED SUCCESSFULLY!")
    print("\n📋 Tables on Main branch:")
    spark.sql("SHOW TABLES IN nessie.ecommerce").show(25, False)
    
    print("\n📊 Summary Statistics:")
    print(f"   - Source records processed: {sample_count:,}")
    print(f"   - Product Recommendations: {rec_count:,} pairs")
    print(f"   - Customer Segments: {seg_count:,} customers")
    print(f"   - Churn Predictions: {churn_count:,} predictions")
    print(f"   - CLV Predictions: {clv_count:,} predictions")
    print(f"   - Next Purchase Predictions: {npp_count:,} predictions")
    
    print("\n📈 Sample Churn Distribution:")
    spark.sql("SELECT risk_category, COUNT(*) as count FROM nessie.ecommerce.churn_predictions_full GROUP BY risk_category").show()
    
    print("\n📈 Sample Segment Distribution:")
    spark.sql("SELECT segment, COUNT(*) as count FROM nessie.ecommerce.customer_segments_full GROUP BY segment ORDER BY count DESC").show()
    
except Exception as e:
    print(f"\n❌ ERROR: {str(e)}")
    import traceback
    traceback.print_exc()
finally:
    spark.stop()
    print("\n🛑 Spark Session Stopped")
