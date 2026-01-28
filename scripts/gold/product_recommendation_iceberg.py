"""
Production Product Recommendation Engine
-----------------------------------------
Optimized FPGrowth-based recommendation system for 300M+ records.
Includes session deduplication, temporal filtering, and efficient rule mining.

Reads from: nessie.ecommerce.orders_silver@main
Writes to: nessie.ecommerce.product_recommendations@gold
          nessie.ecommerce.frequent_itemsets@gold
"""

import os
import pyspark
from pyspark.sql import SparkSession, Window
from pyspark.sql import functions as F
from pyspark.sql.types import ArrayType, LongType, StructType, StructField, StringType, DoubleType
from pyspark.ml.fpm import FPGrowth
from datetime import datetime, timedelta

# Configuration
NESSIE_URI = os.getenv("NESSIE_URI", "http://172.18.0.2:19120/api/v1")
WAREHOUSE = "s3a://lakehouse-prod/warehouse"
AWS_ACCESS_KEY = "962c9f862226831e4edea90cfcfafb8a8dffcd51"
AWS_SECRET_KEY = "sd2rGU918DTmn35E4xJ8EV7BX2XUt7DkqC8v6WDNDUw="
AWS_S3_ENDPOINT = "https://bmcfe6z38foz.compat.objectstorage.ap-mumbai-1.oraclecloud.com"
AWS_REGION = "ap-mumbai-1"

# Recommendation Configuration
MIN_BASKET_SIZE = 2  # Minimum products per session
MAX_BASKET_SIZE = 50  # Maximum products per session (filter outliers)
RECENCY_DAYS = 90  # Only use recent transactions
MIN_PRODUCT_FREQUENCY = 10  # Minimum times a product must appear
MAX_RECOMMENDATIONS = 10  # Top N recommendations per product

# FPGrowth Hyperparameters
FP_CONFIG = {
    'default': {'minSupport': 0.001, 'minConfidence': 0.3},
    'conservative': {'minSupport': 0.005, 'minConfidence': 0.5},
    'aggressive': {'minSupport': 0.0005, 'minConfidence': 0.1}
}

def get_spark_session():
    """Initialize Spark with optimized configuration for FPGrowth"""
    conf = (
        pyspark.SparkConf()
        .setAppName('ecommerce-product-recommendations-prod')
        
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
        
        # Performance Tuning for FPGrowth
        .set('spark.sql.adaptive.enabled', 'true')
        .set('spark.sql.adaptive.coalescePartitions.enabled', 'true')
        .set('spark.sql.shuffle.partitions', '400')  # Higher for FPGrowth
        .set('spark.default.parallelism', '400')
        
        # Memory Management (FPGrowth can be memory-intensive)
        .set('spark.executor.memory', '6g')
        .set('spark.driver.memory', '4g')
        .set('spark.memory.fraction', '0.8')
        .set('spark.memory.storageFraction', '0.2')  # Lower storage, higher execution
        
        # Broadcast and Join Optimization
        .set('spark.sql.autoBroadcastJoinThreshold', '20971520')  # 20MB
        .set('spark.sql.broadcastTimeout', '600')  # 10 minutes
        
        # Network and Serialization
        .set('spark.network.timeout', '600s')
        .set('spark.executor.heartbeatInterval', '60s')
    )
    return SparkSession.builder.config(conf=conf).getOrCreate()

def prepare_transaction_data(spark, recency_days=RECENCY_DAYS):
    """
    Prepare high-quality transaction baskets with filtering and deduplication.
    
    Args:
        spark: SparkSession
        recency_days: Only include transactions from last N days
    
    Returns:
        DataFrame with user_session and items (array of product_ids)
    """
    print(f"📊 Preparing transaction data (last {recency_days} days)...")
    
    # Calculate date threshold
    max_date_query = spark.sql("""
        SELECT MAX(order_date) as max_date 
        FROM nessie.ecommerce.`orders_silver@main`
    """)
    max_date = max_date_query.collect()[0]['max_date']
    cutoff_date = max_date - timedelta(days=recency_days)
    
    print(f"  Analysis period: {cutoff_date} to {max_date}")
    
    # Extract purchase transactions with quality filters
    transactions_query = f"""
    WITH purchase_events AS (
        SELECT 
            user_session,
            product_id,
            event_time,
            order_date,
            price,
            data_quality_score
        FROM nessie.ecommerce.`orders_silver@main`
        WHERE event_type = 'purchase'
          AND user_session IS NOT NULL
          AND product_id IS NOT NULL
          AND price > 0
          AND (data_quality_score >= 90 OR data_quality_score IS NULL)
          AND order_date >= DATE'{cutoff_date}'
    ),
    -- Deduplicate: Keep only one instance of each product per session
    deduplicated AS (
        SELECT DISTINCT
            user_session,
            product_id
        FROM purchase_events
    ),
    -- Filter products that appear too rarely (noise)
    product_frequencies AS (
        SELECT 
            product_id,
            COUNT(DISTINCT user_session) as session_count
        FROM deduplicated
        GROUP BY product_id
        HAVING session_count >= {MIN_PRODUCT_FREQUENCY}
    )
    SELECT 
        d.user_session,
        d.product_id
    FROM deduplicated d
    INNER JOIN product_frequencies pf
        ON d.product_id = pf.product_id
    """
    
    transactions_df = spark.sql(transactions_query)
    
    # Cache for reuse
    transactions_df.persist(pyspark.StorageLevel.MEMORY_AND_DISK)
    
    total_transactions = transactions_df.count()
    unique_sessions = transactions_df.select('user_session').distinct().count()
    unique_products = transactions_df.select('product_id').distinct().count()
    
    print(f"  ✅ Transactions: {total_transactions:,}")
    print(f"  ✅ Unique sessions: {unique_sessions:,}")
    print(f"  ✅ Unique products: {unique_products:,}")
    
    # Group into baskets
    print("\n🛒 Creating shopping baskets...")
    baskets = transactions_df.groupBy("user_session").agg(
        F.collect_set("product_id").alias("items")
    )
    
    # Filter baskets by size
    baskets = baskets.filter(
        (F.size(F.col("items")) >= MIN_BASKET_SIZE) & 
        (F.size(F.col("items")) <= MAX_BASKET_SIZE)
    )
    
    # Repartition for better FPGrowth performance
    baskets = baskets.repartition(200)
    baskets.persist(pyspark.StorageLevel.MEMORY_AND_DISK)
    
    basket_count = baskets.count()
    avg_basket_size = baskets.agg(F.avg(F.size("items"))).collect()[0][0]
    
    print(f"  ✅ Valid baskets: {basket_count:,}")
    print(f"  ✅ Average basket size: {avg_basket_size:.2f} products")
    
    # Cleanup
    transactions_df.unpersist()
    
    return baskets, basket_count

def train_fpgrowth_model(baskets, config_name='default'):
    """
    Train FPGrowth model with specified configuration.
    
    Args:
        baskets: DataFrame with items column
        config_name: Configuration preset ('default', 'conservative', 'aggressive')
    
    Returns:
        Trained FPGrowth model
    """
    config = FP_CONFIG.get(config_name, FP_CONFIG['default'])
    
    print(f"\n🤖 Training FPGrowth model ({config_name} config)...")
    print(f"  minSupport: {config['minSupport']}")
    print(f"  minConfidence: {config['minConfidence']}")
    
    fp_growth = FPGrowth(
        itemsCol="items",
        minSupport=config['minSupport'],
        minConfidence=config['minConfidence'],
        numPartitions=200  # Explicit partitioning for large data
    )
    
    model = fp_growth.fit(baskets)
    
    num_freq_itemsets = model.freqItemsets.count()
    num_rules = model.associationRules.count()
    
    print(f"  ✅ Frequent itemsets: {num_freq_itemsets:,}")
    print(f"  ✅ Association rules: {num_rules:,}")
    
    return model, num_rules

def select_best_model(baskets, basket_count):
    """
    Evaluate multiple configurations and select the best model.
    
    Args:
        baskets: DataFrame with items column
        basket_count: Total number of baskets
    
    Returns:
        Best model and its configuration name
    """
    print("\n🔍 Evaluating multiple FPGrowth configurations...")
    
    results = []
    
    for config_name in ['conservative', 'default', 'aggressive']:
        print(f"\n{'='*60}")
        try:
            model, num_rules = train_fpgrowth_model(baskets, config_name)
            
            if num_rules == 0:
                print(f"  ⚠️  {config_name}: No rules generated (too strict)")
                continue
            
            # Calculate quality metrics
            rules_df = model.associationRules
            
            # Average confidence and lift
            stats = rules_df.agg(
                F.avg('confidence').alias('avg_confidence'),
                F.avg('lift').alias('avg_lift'),
                F.max('lift').alias('max_lift')
            ).collect()[0]
            
            avg_confidence = stats['avg_confidence']
            avg_lift = stats['avg_lift']
            max_lift = stats['max_lift']
            
            print(f"  📊 Quality Metrics:")
            print(f"     Avg Confidence: {avg_confidence:.3f}")
            print(f"     Avg Lift: {avg_lift:.3f}")
            print(f"     Max Lift: {max_lift:.3f}")
            
            # Score: balance between rule count and quality
            # Want high lift, reasonable confidence, and enough rules
            quality_score = (avg_lift * 0.5) + (avg_confidence * 0.3) + (min(num_rules/1000, 1) * 0.2)
            
            results.append({
                'config': config_name,
                'model': model,
                'num_rules': num_rules,
                'avg_confidence': avg_confidence,
                'avg_lift': avg_lift,
                'quality_score': quality_score
            })
            
        except Exception as e:
            print(f"  ❌ {config_name} failed: {e}")
            continue
    
    if not results:
        raise ValueError("No valid models generated. Try adjusting MIN_PRODUCT_FREQUENCY or date range.")
    
    # Select best by quality score
    best = max(results, key=lambda x: x['quality_score'])
    
    print(f"\n{'='*60}")
    print(f"🏆 Best Model: {best['config']}")
    print(f"   Rules: {best['num_rules']:,}")
    print(f"   Avg Confidence: {best['avg_confidence']:.3f}")
    print(f"   Avg Lift: {best['avg_lift']:.3f}")
    print(f"   Quality Score: {best['quality_score']:.3f}")
    
    return best['model'], best['config']

def create_recommendation_table(model, spark):
    """
    Create user-friendly recommendation table from association rules.
    
    Args:
        model: Trained FPGrowth model
        spark: SparkSession
    
    Returns:
        DataFrame with product recommendations
    """
    print("\n📋 Creating recommendation table...")
    
    # Get association rules
    rules = model.associationRules
    
    # Filter for single-product antecedents (most practical)
    rules_filtered = rules.filter(F.size(F.col('antecedent')) == 1)
    
    # Explode antecedent and consequent arrays
    recommendations = rules_filtered.select(
        F.col('antecedent')[0].alias('product_id'),
        F.col('consequent')[0].alias('recommended_product_id'),
        F.col('confidence'),
        F.col('lift'),
        F.col('support').alias('rule_support')
    )
    
    # Filter for meaningful recommendations (lift > 1.0)
    recommendations = recommendations.filter(F.col('lift') > 1.0)
    
    # Rank recommendations per product
    window = Window.partitionBy('product_id').orderBy(
        F.desc('lift'),
        F.desc('confidence')
    )
    
    recommendations = recommendations.withColumn('rank', F.row_number().over(window))
    
    # Keep only top N recommendations per product
    recommendations = recommendations.filter(F.col('rank') <= MAX_RECOMMENDATIONS)
    
    # Add metadata
    recommendations = recommendations.withColumn(
        'recommendation_score',
        F.round((F.col('lift') * 0.7) + (F.col('confidence') * 0.3), 4)
    )
    
    recommendations = recommendations.withColumn(
        'generated_at',
        F.current_timestamp()
    )
    
    # Final selection and ordering
    final_recommendations = recommendations.select(
        'product_id',
        'recommended_product_id',
        'rank',
        'recommendation_score',
        'confidence',
        'lift',
        'rule_support',
        'generated_at'
    ).orderBy('product_id', 'rank')
    
    rec_count = final_recommendations.count()
    unique_products = final_recommendations.select('product_id').distinct().count()
    
    print(f"  ✅ Total recommendations: {rec_count:,}")
    print(f"  ✅ Products with recommendations: {unique_products:,}")
    print(f"  ✅ Avg recommendations per product: {rec_count/unique_products:.1f}")
    
    return final_recommendations

def create_frequent_itemsets_table(model, spark):
    """
    Export frequent itemsets for additional analysis.
    
    Args:
        model: Trained FPGrowth model
        spark: SparkSession
    
    Returns:
        DataFrame with frequent itemsets
    """
    print("\n📦 Creating frequent itemsets table...")
    
    freq_itemsets = model.freqItemsets
    
    # Add itemset size
    freq_itemsets = freq_itemsets.withColumn(
        'itemset_size',
        F.size(F.col('items'))
    )
    
    # Convert array to string for compatibility
    freq_itemsets = freq_itemsets.withColumn(
        'items_str',
        F.concat_ws(',', F.col('items'))
    )
    
    # Add metadata
    freq_itemsets = freq_itemsets.withColumn(
        'generated_at',
        F.current_timestamp()
    )
    
    # Select and order
    result = freq_itemsets.select(
        'items_str',
        'itemset_size',
        F.col('freq').alias('frequency'),
        'generated_at'
    ).orderBy(F.desc('frequency'))
    
    total_itemsets = result.count()
    print(f"  ✅ Total frequent itemsets: {total_itemsets:,}")
    
    # Show distribution by size
    print("\n  📊 Itemset size distribution:")
    result.groupBy('itemset_size').count().orderBy('itemset_size').show()
    
    return result

def generate_insights(recommendations, model, spark):
    """
    Generate business insights from recommendations.
    
    Args:
        recommendations: Recommendation DataFrame
        model: FPGrowth model
        spark: SparkSession
    """
    print("\n💡 RECOMMENDATION INSIGHTS")
    print("="*70)
    
    # Top products by recommendation count
    print("\n1️⃣  Most Recommended Products:")
    top_recommended = recommendations.groupBy('recommended_product_id').agg(
        F.count('product_id').alias('times_recommended'),
        F.avg('recommendation_score').alias('avg_score')
    ).orderBy(F.desc('times_recommended')).limit(10)
    
    top_recommended.show(truncate=False)
    
    # Products with highest lift recommendations
    print("\n2️⃣  Strongest Product Associations (Highest Lift):")
    recommendations.orderBy(F.desc('lift')).limit(10).select(
        'product_id',
        'recommended_product_id',
        'lift',
        'confidence',
        'recommendation_score'
    ).show(truncate=False)
    
    # Products without recommendations
    all_products = spark.sql("""
        SELECT DISTINCT product_id
        FROM nessie.ecommerce.`orders_silver@main`
        WHERE event_type = 'purchase'
          AND product_id IS NOT NULL
    """)
    
    products_with_recs = recommendations.select('product_id').distinct()
    products_without = all_products.join(products_with_recs, 'product_id', 'left_anti')
    
    no_rec_count = products_without.count()
    total_products = all_products.count()
    coverage_pct = (1 - no_rec_count/total_products) * 100
    
    print(f"\n3️⃣  Recommendation Coverage:")
    print(f"   Total products: {total_products:,}")
    print(f"   Products with recommendations: {total_products - no_rec_count:,}")
    print(f"   Coverage: {coverage_pct:.1f}%")
    
    if no_rec_count > 0:
        print(f"   ⚠️  {no_rec_count:,} products lack recommendations")
        print("   💡 Suggestion: Lower MIN_PRODUCT_FREQUENCY or use content-based fallback")

def run_product_recommendation():
    """Main recommendation pipeline"""
    spark = get_spark_session()
    spark.sparkContext.setLogLevel("WARN")
    
    try:
        print("="*70)
        print("🚀 E-commerce Product Recommendation Engine")
        print("="*70)
        print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Step 1: Prepare Data
        baskets, basket_count = prepare_transaction_data(spark)
        
        # Step 2: Train Model (with hyperparameter selection)
        best_model, best_config = select_best_model(baskets, basket_count)
        
        # Step 3: Create Recommendations
        recommendations = create_recommendation_table(best_model, spark)
        
        # Step 4: Create Frequent Itemsets
        frequent_itemsets = create_frequent_itemsets_table(best_model, spark)
        
        # Step 5: Generate Insights
        generate_insights(recommendations, best_model, spark)
        
        # Step 6: Write to Gold Layer
        print("\n💾 Writing results to Gold layer...")
        
        # Write recommendations (partitioned by product_id modulo for balanced partitions)
        recommendations = recommendations.withColumn(
            'partition_key',
            F.expr('product_id % 100')
        )
        
        recommendations.writeTo("nessie.ecommerce.product_recommendations") \
            .partitionedBy("partition_key") \
            .createOrReplace()
        
        print("  ✅ Recommendations written to: nessie.ecommerce.product_recommendations@gold")
        
        # Write frequent itemsets
        frequent_itemsets.writeTo("nessie.ecommerce.frequent_itemsets") \
            .createOrReplace()
        
        print("  ✅ Frequent itemsets written to: nessie.ecommerce.frequent_itemsets@gold")
        
        # Cleanup
        baskets.unpersist()
        
        print("\n" + "="*70)
        print("✅ Recommendation pipeline completed successfully!")
        print("="*70)
        
    except Exception as e:
        print(f"\n❌ Error in recommendation pipeline: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        spark.stop()

if __name__ == "__main__":
    run_product_recommendation()
