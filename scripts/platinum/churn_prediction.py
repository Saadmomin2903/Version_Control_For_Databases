"""
Customer Churn Prediction Model
--------------------------------
Predicts probability of customer churn in next 30/60/90 days.
Uses gradient boosting with engineered RFM + behavioral features.

Reads from: nessie.ecommerce.orders_silver@main
            nessie.ecommerce.customers_silver@main
Writes to: nessie.ecommerce.churn_predictions@gold
"""

import os
import pyspark
from pyspark.sql import SparkSession, Window
from pyspark.sql import functions as F
from pyspark.sql.types import DoubleType, IntegerType, StringType
from datetime import datetime, timedelta

from pyspark.ml.feature import VectorAssembler, StandardScaler
from pyspark.ml.classification import GBTClassifier, LogisticRegression
from pyspark.ml.evaluation import BinaryClassificationEvaluator, MulticlassClassificationEvaluator
from pyspark.ml import Pipeline

# Configuration
NESSIE_URI = os.getenv("NESSIE_URI", "http://172.18.0.2:19120/api/v1")
WAREHOUSE = "s3a://lakehouse-prod/warehouse"
AWS_ACCESS_KEY = "962c9f862226831e4edea90cfcfafb8a8dffcd51"
AWS_SECRET_KEY = "sd2rGU918DTmn35E4xJ8EV7BX2XUt7DkqC8v6WDNDUw="
AWS_S3_ENDPOINT = "https://bmcfe6z38foz.compat.objectstorage.ap-mumbai-1.oraclecloud.com"
AWS_REGION = "ap-mumbai-1"

# Churn Configuration
CHURN_WINDOW_DAYS = 90  # Predict churn in next 90 days
OBSERVATION_WINDOW_DAYS = 180  # Use last 180 days for features
MIN_PURCHASES_FOR_TRAINING = 2  # Need history to predict churn
LOOKBACK_DAYS_FOR_LABELS = 270  # Historical period for creating training labels

def get_spark_session():
    """Initialize Spark with optimized configuration"""
    conf = (
        pyspark.SparkConf()
        .setAppName('ecommerce-churn-prediction-prod')
        
        # Jars
        .set('spark.jars.packages',
             'org.apache.iceberg:iceberg-spark-runtime-3.3_2.12:1.3.1,'
             'org.projectnessie.nessie-integrations:nessie-spark-extensions-3.3_2.12:0.67.0,'
             'software.amazon.awssdk:bundle:2.17.178,'
             'software.amazon.awssdk:url-connection-client:2.17.178')
        
        # Extensions & Catalog
        .set('spark.sql.extensions',
             'org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions,'
             'org.projectnessie.spark.extensions.NessieSparkSessionExtensions')
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
        
        # S3A
        .set('spark.hadoop.fs.s3a.access.key', AWS_ACCESS_KEY)
        .set('spark.hadoop.fs.s3a.secret.key', AWS_SECRET_KEY)
        .set('spark.hadoop.fs.s3a.endpoint', AWS_S3_ENDPOINT)
        .set('spark.hadoop.fs.s3a.path.style.access', 'true')
        .set('spark.hadoop.fs.s3a.connection.ssl.enabled', 'true')
        .set('spark.hadoop.fs.s3a.impl', 'org.apache.hadoop.fs.s3a.S3AFileSystem')
        .set('spark.hadoop.fs.s3a.endpoint.region', AWS_REGION)
        
        # Performance
        .set('spark.sql.adaptive.enabled', 'true')
        .set('spark.sql.adaptive.coalescePartitions.enabled', 'true')
        .set('spark.sql.shuffle.partitions', '200')
        .set('spark.default.parallelism', '200')
        .set('spark.executor.memory', '6g')
        .set('spark.driver.memory', '4g')
        .set('spark.memory.fraction', '0.8')
    )
    return SparkSession.builder.config(conf=conf).getOrCreate()

def create_training_labels(spark, cutoff_date, observation_end_date):
    """
    Create churn labels for training.
    Churn = No purchase in CHURN_WINDOW_DAYS after observation period.
    """
    churn_window_end = observation_end_date + timedelta(days=CHURN_WINDOW_DAYS)
    
    print(f"📊 Creating training labels...")
    print(f"  Observation end: {observation_end_date}")
    print(f"  Churn window: {observation_end_date} to {churn_window_end}")
    
    labels_query = f"""
    WITH customer_last_purchase AS (
        SELECT 
            customer_id,
            MAX(order_date) as last_purchase_date
        FROM nessie.ecommerce.`orders_silver@main`
        WHERE event_type = 'purchase'
          AND customer_id IS NOT NULL
          AND order_date <= DATE'{churn_window_end}'
        GROUP BY customer_id
    ),
    active_customers AS (
        -- Customers active during observation period
        SELECT DISTINCT customer_id
        FROM nessie.ecommerce.`orders_silver@main`
        WHERE event_type = 'purchase'
          AND customer_id IS NOT NULL
          AND order_date <= DATE'{observation_end_date}'
    )
    SELECT 
        a.customer_id,
        CASE 
            WHEN c.last_purchase_date > DATE'{observation_end_date}' THEN 0  -- Not churned
            ELSE 1  -- Churned
        END as churn
    FROM active_customers a
    LEFT JOIN customer_last_purchase c
        ON a.customer_id = c.customer_id
    """
    
    labels = spark.sql(labels_query)
    labels.persist(pyspark.StorageLevel.MEMORY_AND_DISK)
    
    # Statistics
    label_stats = labels.groupBy('churn').count().collect()
    total = labels.count()
    
    print(f"\n  ✅ Training labels created: {total:,} customers")
    for row in label_stats:
        pct = (row['count'] / total) * 100
        status = "Churned" if row['churn'] == 1 else "Active"
        print(f"     {status}: {row['count']:,} ({pct:.1f}%)")
    
    return labels

def engineer_features(spark, observation_end_date):
    """
    Engineer comprehensive features for churn prediction.
    """
    observation_start = observation_end_date - timedelta(days=OBSERVATION_WINDOW_DAYS)
    
    print(f"\n🔧 Engineering features...")
    print(f"  Feature window: {observation_start} to {observation_end_date}")
    
    features_query = f"""
    WITH purchase_events AS (
        SELECT 
            customer_id,
            order_date,
            price,
            product_id,
            category_code,
            brand,
            event_time
        FROM nessie.ecommerce.`orders_silver@main`
        WHERE event_type = 'purchase'
          AND customer_id IS NOT NULL
          AND price > 0
          AND order_date > DATE'{observation_start}'
          AND order_date <= DATE'{observation_end_date}'
          AND (data_quality_score >= 90 OR data_quality_score IS NULL)
    ),
    customer_metrics AS (
        SELECT 
            customer_id,
            
            -- RFM Features
            DATEDIFF(DATE'{observation_end_date}', MAX(order_date)) as recency_days,
            COUNT(*) as frequency,
            SUM(price) as monetary_value,
            AVG(price) as avg_order_value,
            STDDEV(price) as stddev_order_value,
            MIN(price) as min_order_value,
            MAX(price) as max_order_value,
            
            -- Temporal Features
            DATEDIFF(MAX(order_date), MIN(order_date)) as customer_lifetime_days,
            COUNT(DISTINCT order_date) as unique_purchase_days,
            
            -- Product Diversity
            COUNT(DISTINCT product_id) as unique_products_purchased,
            COUNT(DISTINCT category_code) as unique_categories,
            COUNT(DISTINCT brand) as unique_brands,
            
            -- Time-based aggregations for trend detection
            COUNT(*) as total_purchases
            
        FROM purchase_events
        GROUP BY customer_id
    ),
    -- Calculate purchase trends (comparing first vs second half)
    purchase_trends AS (
        SELECT 
            customer_id,
            SUM(CASE WHEN order_date <= DATE_ADD(DATE'{observation_start}', {OBSERVATION_WINDOW_DAYS//2}) 
                THEN 1 ELSE 0 END) as purchases_first_half,
            SUM(CASE WHEN order_date > DATE_ADD(DATE'{observation_start}', {OBSERVATION_WINDOW_DAYS//2}) 
                THEN 1 ELSE 0 END) as purchases_second_half,
            SUM(CASE WHEN order_date <= DATE_ADD(DATE'{observation_start}', {OBSERVATION_WINDOW_DAYS//2}) 
                THEN price ELSE 0 END) as revenue_first_half,
            SUM(CASE WHEN order_date > DATE_ADD(DATE'{observation_start}', {OBSERVATION_WINDOW_DAYS//2}) 
                THEN price ELSE 0 END) as revenue_second_half
        FROM purchase_events
        GROUP BY customer_id
    ),
    -- View-to-purchase ratio (engagement metric)
    view_metrics AS (
        SELECT 
            customer_id,
            SUM(CASE WHEN event_type = 'view' THEN 1 ELSE 0 END) as total_views,
            SUM(CASE WHEN event_type = 'cart' THEN 1 ELSE 0 END) as total_carts,
            SUM(CASE WHEN event_type = 'purchase' THEN 1 ELSE 0 END) as total_purchases_check
        FROM nessie.ecommerce.`orders_silver@main`
        WHERE customer_id IS NOT NULL
          AND order_date > DATE'{observation_start}'
          AND order_date <= DATE'{observation_end_date}'
        GROUP BY customer_id
    )
    SELECT 
        cm.customer_id,
        
        -- RFM
        cm.recency_days,
        cm.frequency,
        cm.monetary_value,
        cm.avg_order_value,
        COALESCE(cm.stddev_order_value, 0) as stddev_order_value,
        cm.min_order_value,
        cm.max_order_value,
        
        -- Lifetime
        cm.customer_lifetime_days,
        cm.unique_purchase_days,
        CASE WHEN cm.customer_lifetime_days > 0 
            THEN cm.frequency / (cm.customer_lifetime_days / 30.0) 
            ELSE cm.frequency 
        END as purchases_per_month,
        
        -- Diversity
        cm.unique_products_purchased,
        cm.unique_categories,
        cm.unique_brands,
        cm.unique_products_purchased / cm.frequency as product_exploration_rate,
        
        -- Trends (engagement change)
        pt.purchases_first_half,
        pt.purchases_second_half,
        CASE WHEN pt.purchases_first_half > 0
            THEN (pt.purchases_second_half - pt.purchases_first_half) / pt.purchases_first_half
            ELSE 0
        END as purchase_frequency_trend,
        
        pt.revenue_first_half,
        pt.revenue_second_half,
        CASE WHEN pt.revenue_first_half > 0
            THEN (pt.revenue_second_half - pt.revenue_first_half) / pt.revenue_first_half
            ELSE 0
        END as revenue_trend,
        
        -- Engagement
        COALESCE(vm.total_views, 0) as total_views,
        COALESCE(vm.total_carts, 0) as total_carts,
        CASE WHEN vm.total_views > 0 
            THEN cm.frequency / vm.total_views 
            ELSE 0 
        END as view_to_purchase_rate,
        CASE WHEN vm.total_carts > 0 
            THEN cm.frequency / vm.total_carts 
            ELSE 0 
        END as cart_to_purchase_rate
        
    FROM customer_metrics cm
    LEFT JOIN purchase_trends pt ON cm.customer_id = pt.customer_id
    LEFT JOIN view_metrics vm ON cm.customer_id = vm.customer_id
    WHERE cm.frequency >= {MIN_PURCHASES_FOR_TRAINING}
    """
    
    features = spark.sql(features_query)
    features.persist(pyspark.StorageLevel.MEMORY_AND_DISK)
    
    feature_count = features.count()
    print(f"  ✅ Features engineered for {feature_count:,} customers")
    
    return features

def train_churn_model(train_data, test_data):
    """
    Train gradient boosting churn prediction model.
    """
    print("\n🤖 Training churn prediction model...")
    
    # Feature columns (exclude customer_id and churn)
    feature_cols = [col for col in train_data.columns 
                   if col not in ['customer_id', 'churn']]
    
    # Build pipeline
    assembler = VectorAssembler(
        inputCols=feature_cols,
        outputCol='unscaled_features',
        handleInvalid='skip'
    )
    
    scaler = StandardScaler(
        inputCol='unscaled_features',
        outputCol='features',
        withStd=True,
        withMean=True
    )
    
    # Gradient Boosting Trees Classifier
    gbt = GBTClassifier(
        labelCol='churn',
        featuresCol='features',
        maxIter=100,
        maxDepth=5,
        stepSize=0.1,
        seed=42
    )
    
    pipeline = Pipeline(stages=[assembler, scaler, gbt])
    model = pipeline.fit(train_data)
    
    # Evaluate
    predictions = model.transform(test_data)
    evaluator = BinaryClassificationEvaluator(labelCol='churn', metricName='areaUnderROC')
    auc = evaluator.evaluate(predictions)
    print(f"  ✅ Model trained. AUC-ROC: {auc:.4f}")
    
    return model

def score_current_customers(spark, model, current_date):
    """
    Score all current customers for churn risk.
    """
    print(f"\n💯 Scoring current customers as of {current_date}...")
    features = engineer_features(spark, current_date)
    predictions = model.transform(features)
    
    # Extract probability of churn
    predictions = predictions.withColumn('churn_probability', F.expr('probability[1]'))
    
    # Categorize risk
    predictions = predictions.withColumn(
        'risk_category',
        F.when(F.col('churn_probability') >= 0.7, 'High')
         .when(F.col('churn_probability') >= 0.4, 'Medium')
         .otherwise('Low')
    )
    
    output = predictions.select(
        'customer_id',
        'churn_probability',
        'risk_category',
        'recency_days',
        'frequency',
        'monetary_value',
        F.current_timestamp().alias('scored_at'),
        F.lit('v1.0').alias('model_version')
    )
    
    return output

def main():
    spark = get_spark_session()
    spark.sparkContext.setLogLevel("WARN")
    
    try:
        max_date = spark.sql("SELECT MAX(order_date) FROM nessie.ecommerce.`orders_silver@main`").collect()[0][0]
        observation_end_date = max_date - timedelta(days=CHURN_WINDOW_DAYS)
        cutoff_date = observation_end_date - timedelta(days=OBSERVATION_WINDOW_DAYS)
        
        # Training Flow
        labels = create_training_labels(spark, cutoff_date, observation_end_date)
        features = engineer_features(spark, observation_end_date)
        training_data = features.join(labels, 'customer_id', 'inner')
        
        train_data, test_data = training_data.randomSplit([0.8, 0.2], seed=42)
        model = train_churn_model(train_data, test_data)
        
        # Inference Flow
        predictions = score_current_customers(spark, model, max_date)
        
        # Save to Iceberg (Platinum Layer)
        predictions.writeTo("nessie.ecommerce.churn_predictions") \
            .partitionedBy("risk_category") \
            .createOrReplace()
            
        print(f"✅ Churn predictions written to nessie.ecommerce.churn_predictions@gold")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        spark.stop()

if __name__ == "__main__":
    main()
