"""
Production Customer Segmentation for Big Data E-commerce
---------------------------------------------------------
Optimized for 300M+ order records with proper partitioning,
incremental processing, and distributed ML.

Reads from: nessie.ecommerce.orders_silver@main
            nessie.ecommerce.customers_silver@main
Writes to: nessie.ecommerce.customer_segments@gold
"""

import os
import pyspark
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import StringType
from datetime import datetime

from pyspark.ml.feature import VectorAssembler, StandardScaler
from pyspark.ml.clustering import KMeans
from pyspark.ml.evaluation import ClusteringEvaluator

# Configuration
NESSIE_URI = os.getenv("NESSIE_URI", "http://172.18.0.2:19120/api/v1")
WAREHOUSE = "s3a://lakehouse-prod/warehouse"
AWS_ACCESS_KEY = "962c9f862226831e4edea90cfcfafb8a8dffcd51"
AWS_SECRET_KEY = "sd2rGU918DTmn35E4xJ8EV7BX2XUt7DkqC8v6WDNDUw="
AWS_S3_ENDPOINT = "https://bmcfe6z38foz.compat.objectstorage.ap-mumbai-1.oraclecloud.com"
AWS_REGION = "ap-mumbai-1"

# ML Configuration
MIN_PURCHASE_THRESHOLD = 2  # Minimum purchases to be considered active
OPTIMAL_K_RANGE = range(3, 8)  # Test K from 3-7
SAMPLE_FRACTION_FOR_K_SELECTION = 0.1  # Use 10% sample for K selection

def get_spark_session():
    """Initialize Spark with optimized settings for big data ML"""
    conf = (
        pyspark.SparkConf()
        .setAppName('ecommerce-customer-segmentation-prod')
        
        # Jars
        .set('spark.jars.packages',
             'org.apache.iceberg:iceberg-spark-runtime-3.3_2.12:1.3.1,'
             'org.projectnessie.nessie-integrations:nessie-spark-extensions-3.3_2.12:0.67.0,'
             'software.amazon.awssdk:bundle:2.17.178,'
             'software.amazon.awssdk:url-connection-client:2.17.178')
        
        # Extensions
        .set('spark.sql.extensions',
             'org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions,'
             'org.projectnessie.spark.extensions.NessieSparkSessionExtensions')
        
        # Nessie Catalog
        .set('spark.sql.catalog.nessie', 'org.apache.iceberg.spark.SparkCatalog')
        .set('spark.sql.catalog.nessie.uri', NESSIE_URI)
        .set('spark.sql.catalog.nessie.ref', 'gold')
        .set('spark.sql.catalog.nessie.catalog-impl', 'org.apache.iceberg.nessie.NessieCatalog')
        .set('spark.sql.catalog.nessie.warehouse', WAREHOUSE)
        .set('spark.sql.catalog.nessie.io-impl', 'org.apache.iceberg.aws.s3.S3FileIO')
        .set('spark.sql.catalog.nessie.s3.endpoint', AWS_S3_ENDPOINT)
        .set('spark.sql.catalog.nessie.s3.region', AWS_REGION)
        .set('spark.sql.catalog.nessie.s3.path-style-access', 'true')
        .set('spark.sql.catalog.nessie.client.region', AWS_REGION)
        .set('spark.sql.catalog.nessie.s3.access-key-id', AWS_ACCESS_KEY)
        .set('spark.sql.catalog.nessie.s3.secret-access-key', AWS_SECRET_KEY)
        
        # S3A Configuration
        .set('spark.hadoop.fs.s3a.access.key', AWS_ACCESS_KEY)
        .set('spark.hadoop.fs.s3a.secret.key', AWS_SECRET_KEY)
        .set('spark.hadoop.fs.s3a.endpoint', AWS_S3_ENDPOINT)
        .set('spark.hadoop.fs.s3a.path.style.access', 'true')
        .set('spark.hadoop.fs.s3a.connection.ssl.enabled', 'true')
        .set('spark.hadoop.fs.s3a.impl', 'org.apache.hadoop.fs.s3a.S3AFileSystem')
        .set('spark.hadoop.fs.s3a.endpoint.region', AWS_REGION)
        
        # Performance Tuning for Large Data
        .set('spark.sql.adaptive.enabled', 'true')
        .set('spark.sql.adaptive.coalescePartitions.enabled', 'true')
        .set('spark.sql.shuffle.partitions', '200')
        .set('spark.default.parallelism', '200')
        
        # Memory Management
        .set('spark.executor.memory', '4g')
        .set('spark.driver.memory', '2g')
        .set('spark.memory.fraction', '0.8')
        .set('spark.memory.storageFraction', '0.3')
        
        # Broadcast optimization
        .set('spark.sql.autoBroadcastJoinThreshold', '10485760')  # 10MB
    )
    return SparkSession.builder.config(conf=conf).getOrCreate()

def calculate_rfm_features(spark, analysis_date=None):
    """
    Calculate RFM (Recency, Frequency, Monetary) features efficiently.
    
    Args:
        spark: SparkSession
        analysis_date: Reference date for recency (defaults to max order_date)
    
    Returns:
        DataFrame with customer_id and RFM features
    """
    print("📊 Calculating RFM features from orders...")
    
    # Get analysis date if not provided
    if analysis_date is None:
        analysis_date = spark.sql("""
            SELECT MAX(order_date) as max_date 
            FROM nessie.ecommerce.`orders_silver@main`
        """).collect()[0]['max_date']
        print(f"  Using analysis date: {analysis_date}")
    
    # Calculate RFM using pushdown predicates and partitioning
    rfm_query = f"""
    WITH customer_purchases AS (
        SELECT 
            customer_id,
            order_date,
            price,
            event_time
        FROM nessie.ecommerce.`orders_silver@main`
        WHERE event_type = 'purchase'
          AND customer_id IS NOT NULL
          AND price > 0
          AND (data_quality_score >= 90 OR data_quality_score IS NULL)
    ),
    rfm_base AS (
        SELECT 
            customer_id,
            -- Recency: Days since last purchase
            DATEDIFF(DATE'{analysis_date}', MAX(order_date)) as recency_days,
            
            -- Frequency: Total number of purchases
            COUNT(*) as frequency,
            
            -- Monetary: Total revenue
            SUM(price) as monetary_value,
            
            -- Additional metrics
            AVG(price) as avg_order_value,
            MIN(price) as min_order_value,
            MAX(price) as max_order_value,
            STDDEV(price) as stddev_order_value,
            
            -- Time-based features
            MIN(order_date) as first_purchase_date,
            MAX(order_date) as last_purchase_date,
            DATEDIFF(MAX(order_date), MIN(order_date)) as customer_lifetime_days
        FROM customer_purchases
        GROUP BY customer_id
    )
    SELECT 
        customer_id,
        recency_days,
        frequency,
        monetary_value,
        avg_order_value,
        min_order_value,
        max_order_value,
        COALESCE(stddev_order_value, 0) as stddev_order_value,
        first_purchase_date,
        last_purchase_date,
        customer_lifetime_days,
        -- Derived metrics
        CASE 
            WHEN customer_lifetime_days > 0 
            THEN frequency / (customer_lifetime_days / 30.0)
            ELSE frequency 
        END as purchase_frequency_per_month
    FROM rfm_base
    WHERE frequency >= {MIN_PURCHASE_THRESHOLD}
    """
    
    rfm_df = spark.sql(rfm_query)
    
    # Repartition for better performance
    rfm_df = rfm_df.repartition(100, "customer_id")
    
    # Cache with storage level
    rfm_df.persist(pyspark.StorageLevel.MEMORY_AND_DISK)
    
    customer_count = rfm_df.count()
    print(f"✅ RFM features calculated for {customer_count:,} active customers")
    
    return rfm_df

def select_optimal_k(scaled_data, k_range=OPTIMAL_K_RANGE, sample_fraction=SAMPLE_FRACTION_FOR_K_SELECTION):
    """
    Find optimal K using sampled data and Silhouette scores.
    
    Args:
        scaled_data: Scaled feature DataFrame
        k_range: Range of K values to test
        sample_fraction: Fraction of data to sample for K selection
    
    Returns:
        Optimal K value
    """
    print(f"\n🔍 Finding optimal K using {sample_fraction*100}% sample...")
    
    # Sample data for faster K selection
    sampled_data = scaled_data.sample(withReplacement=False, fraction=sample_fraction, seed=42)
    sampled_data.cache()
    
    evaluator = ClusteringEvaluator(
        featuresCol='features',
        predictionCol='prediction',
        metricName='silhouette',
        distanceMeasure='squaredEuclidean'
    )
    
    k_scores = []
    for k in k_range:
        kmeans = KMeans(
            featuresCol='features',
            predictionCol='prediction',
            k=k,
            seed=42,
            maxIter=20,
            initMode='k-means||'
        )
        model = kmeans.fit(sampled_data)
        predictions = model.transform(sampled_data)
        silhouette = evaluator.evaluate(predictions)
        k_scores.append((k, silhouette))
        print(f"  K={k}: Silhouette = {silhouette:.4f}")
    
    sampled_data.unpersist()
    
    # Select K with highest silhouette score
    best_k = max(k_scores, key=lambda x: x[1])[0]
    best_score = max(k_scores, key=lambda x: x[1])[1]
    
    print(f"\n🏆 Optimal K={best_k} (Silhouette={best_score:.4f})")
    return best_k

def assign_segment_labels(predictions, cluster_centers):
    """
    Assign business-friendly labels based on cluster characteristics.
    Uses native Spark functions instead of UDFs for better performance.
    
    Args:
        predictions: DataFrame with cluster predictions
        cluster_centers: Array of cluster center vectors
    
    Returns:
        DataFrame with segment labels
    """
    print("\n🏷️  Assigning segment labels...")
    
    # Calculate monetary ranking for each cluster
    # Assuming features are [recency, frequency, monetary, ...]
    # We'll rank by monetary (index 2) descending and frequency (index 1) descending
    cluster_stats = []
    for idx, center in enumerate(cluster_centers):
        # Monetary value is typically the most important for segmentation
        monetary_score = center[2]
        frequency_score = center[1]
        recency_score = -center[0]  # Lower recency (more recent) is better
        
        combined_score = (monetary_score * 0.5) + (frequency_score * 0.3) + (recency_score * 0.2)
        cluster_stats.append((idx, combined_score, monetary_score, frequency_score))
    
    # Sort by combined score
    sorted_clusters = sorted(cluster_stats, key=lambda x: x[1])
    
    # Create segment mapping
    segment_names = {
        0: 'At Risk',
        1: 'Promising',
        2: 'Loyal',
        3: 'Champions',
        4: 'VIP',
        5: 'Whales',
        6: 'Ultra Premium'
    }
    
    # Create mapping from cluster_id to segment
    cluster_to_segment = {
        cluster_id: {
            'rank': rank,
            'name': segment_names.get(rank, f'Segment_{rank}')
        }
        for rank, (cluster_id, _, _, _) in enumerate(sorted_clusters)
    }
    
    # Create mapping expressions using CASE WHEN (native Spark, much faster than UDF)
    rank_expr = F.when(F.col('prediction') == list(cluster_to_segment.keys())[0], 
                       cluster_to_segment[list(cluster_to_segment.keys())[0]]['rank'])
    name_expr = F.when(F.col('prediction') == list(cluster_to_segment.keys())[0], 
                       cluster_to_segment[list(cluster_to_segment.keys())[0]]['name'])
    
    for cluster_id in list(cluster_to_segment.keys())[1:]:
        rank_expr = rank_expr.when(F.col('prediction') == cluster_id, 
                                   cluster_to_segment[cluster_id]['rank'])
        name_expr = name_expr.when(F.col('prediction') == cluster_id, 
                                   cluster_to_segment[cluster_id]['name'])
    
    # Add segment columns
    result = predictions \
        .withColumn('segment_rank', rank_expr) \
        .withColumn('segment_name', name_expr)
    
    return result

def run_segmentation():
    """Main segmentation pipeline with production optimizations"""
    spark = get_spark_session()
    spark.sparkContext.setLogLevel("WARN")
    
    try:
        # Step 1: Calculate RFM Features
        rfm_features = calculate_rfm_features(spark)
        
        # Step 2: Feature Engineering
        print("\n🎯 Preparing features for clustering...")
        
        # Select features for clustering
        feature_cols = [
            'recency_days',
            'frequency', 
            'monetary_value',
            'avg_order_value',
            'purchase_frequency_per_month'
        ]
        
        assembler = VectorAssembler(
            inputCols=feature_cols,
            outputCol='unscaled_features',
            handleInvalid='skip'  # Skip rows with nulls/NaN
        )
        
        vectorized = assembler.transform(rfm_features)
        
        # Standardize features
        scaler = StandardScaler(
            inputCol='unscaled_features',
            outputCol='features',
            withStd=True,
            withMean=True
        )
        
        scaler_model = scaler.fit(vectorized)
        scaled_data = scaler_model.transform(vectorized)
        
        # Persist for iterative training
        scaled_data.persist(pyspark.StorageLevel.MEMORY_AND_DISK)
        
        # Step 3: Find Optimal K
        optimal_k = select_optimal_k(scaled_data)
        
        # Step 4: Train Final Model
        print(f"\n🤖 Training final K-Means model (K={optimal_k})...")
        
        final_kmeans = KMeans(
            featuresCol='features',
            predictionCol='prediction',
            k=optimal_k,
            seed=42,
            maxIter=50,
            initMode='k-means||',
            tol=1e-4
        )
        
        final_model = final_kmeans.fit(scaled_data)
        predictions = final_model.transform(scaled_data)
        
        # Step 5: Assign Business Labels
        labeled_predictions = assign_segment_labels(predictions, final_model.clusterCenters())
        
        # Step 6: Generate Segment Profiles
        print("\n📊 Segment Profiles:")
        segment_summary = labeled_predictions.groupBy('segment_name').agg(
            F.count('customer_id').alias('customer_count'),
            F.avg('recency_days').alias('avg_recency_days'),
            F.avg('frequency').alias('avg_frequency'),
            F.avg('monetary_value').alias('avg_monetary'),
            F.avg('avg_order_value').alias('avg_order_value'),
            F.sum('monetary_value').alias('total_revenue')
        ).orderBy(F.desc('avg_monetary'))
        
        segment_summary.show(truncate=False)
        
        # Calculate revenue contribution
        total_revenue = segment_summary.agg(F.sum('total_revenue')).collect()[0][0]
        segment_summary_with_pct = segment_summary.withColumn(
            'revenue_pct',
            F.round((F.col('total_revenue') / total_revenue) * 100, 2)
        )
        
        print("\n💰 Revenue Contribution by Segment:")
        segment_summary_with_pct.select(
            'segment_name', 'customer_count', 'total_revenue', 'revenue_pct'
        ).orderBy(F.desc('revenue_pct')).show(truncate=False)
        
        # Step 7: Prepare Output
        print("\n💾 Writing segments to Gold layer...")
        
        output_df = labeled_predictions.select(
            'customer_id',
            'recency_days',
            'frequency',
            'monetary_value',
            'avg_order_value',
            'purchase_frequency_per_month',
            'first_purchase_date',
            'last_purchase_date',
            'customer_lifetime_days',
            F.col('prediction').alias('cluster_id'),
            'segment_rank',
            'segment_name',
            F.current_timestamp().alias('segmented_at')
        )
        
        # Write with partitioning for efficient queries
        output_df.writeTo("nessie.ecommerce.customer_segments") \
            .partitionedBy("segment_name") \
            .createOrReplace()
        
        final_count = output_df.count()
        print(f"✅ Successfully segmented {final_count:,} customers")
        print(f"✅ Written to nessie.ecommerce.customer_segments@gold")
        
        # Step 8: Cleanup
        rfm_features.unpersist()
        scaled_data.unpersist()
        
    except Exception as e:
        print(f"❌ Error during segmentation: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        spark.stop()

if __name__ == "__main__":
    print("=" * 70)
    print("🚀 E-commerce Customer Segmentation Pipeline")
    print("=" * 70)
    run_segmentation()
    print("\n" + "=" * 70)
    print("✅ Pipeline completed successfully!")
    print("=" * 70)
