"""
Customer Lifetime Value (CLV) Prediction Model
----------------------------------------------
Predicts 12-month future revenue per customer using XGBoost regression.
Enables customer prioritization and acquisition cost optimization.

Reads from: nessie.ecommerce.orders_silver@main
            nessie.ecommerce.customers_silver@main
Writes to: nessie.ecommerce.clv_predictions@gold
"""

import os
import pyspark
from pyspark.sql import SparkSession, Window
from pyspark.sql import functions as F
from pyspark.sql.types import DoubleType, StringType
from datetime import datetime, timedelta

from pyspark.ml.feature import VectorAssembler, StandardScaler
from pyspark.ml.regression import GBTRegressor, LinearRegression
from pyspark.ml.evaluation import RegressionEvaluator
from pyspark.ml import Pipeline

# Configuration
NESSIE_URI = os.getenv("NESSIE_URI", "http://172.18.0.2:19120/api/v1")
WAREHOUSE = "s3a://lakehouse-prod/warehouse"
AWS_ACCESS_KEY = "962c9f862226831e4edea90cfcfafb8a8dffcd51"
AWS_SECRET_KEY = "sd2rGU918DTmn35E4xJ8EV7BX2XUt7DkqC8v6WDNDUw="
AWS_S3_ENDPOINT = "https://bmcfe6z38foz.compat.objectstorage.ap-mumbai-1.oraclecloud.com"
AWS_REGION = "ap-mumbai-1"

# CLV Configuration
PREDICTION_WINDOW_MONTHS = 12  # Predict 12-month CLV
OBSERVATION_WINDOW_DAYS = 365  # Use 1 year of history for features
MIN_PURCHASES_FOR_TRAINING = 3  # Need purchase history
LOOKBACK_MONTHS_FOR_LABELS = 24  # 2 years history for training

def get_spark_session():
    """Initialize Spark with optimized configuration"""
    conf = (
        pyspark.SparkConf()
        .setAppName('ecommerce-clv-prediction-prod')
        
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

def create_training_labels(spark, cutoff_date, prediction_end_date):
    """
    Create CLV labels = actual revenue in next 12 months.
    """
    print(f"📊 Creating CLV training labels...")
    print(f"  Prediction window: {cutoff_date} to {prediction_end_date}")
    
    labels_query = f"""
    SELECT 
        customer_id,
        SUM(price) as actual_clv_12m,
        COUNT(*) as future_purchases,
        AVG(price) as future_avg_order_value
    FROM nessie.ecommerce.`orders_silver@main`
    WHERE event_type = 'purchase'
      AND customer_id IS NOT NULL
      AND price > 0
      AND order_date > DATE'{cutoff_date}'
      AND order_date <= DATE'{prediction_end_date}'
    GROUP BY customer_id
    """
    
    labels = spark.sql(labels_query)
    labels.persist(pyspark.StorageLevel.MEMORY_AND_DISK)
    return labels

def engineer_clv_features(spark, observation_end_date):
    """
    Engineer comprehensive features for CLV prediction.
    """
    observation_start = observation_end_date - timedelta(days=OBSERVATION_WINDOW_DAYS)
    
    print(f"\n🔧 Engineering CLV features...")
    print(f"  Feature window: {observation_start} to {observation_end_date}")
    
    features_query = f"""
    WITH purchase_events AS (
        SELECT 
            customer_id,
            order_date,
            price,
            product_id,
            category_code,
            brand
        FROM nessie.ecommerce.`orders_silver@main`
        WHERE event_type = 'purchase'
          AND customer_id IS NOT NULL
          AND price > 0
          AND order_date > DATE'{observation_start}'
          AND order_date <= DATE'{observation_end_date}'
          AND (data_quality_score >= 90 OR data_quality_score IS NULL)
    ),
    base_metrics AS (
        SELECT 
            customer_id,
            SUM(price) as historical_revenue,
            AVG(price) as avg_order_value,
            STDDEV(price) as stddev_order_value,
            MIN(price) as min_order_value,
            MAX(price) as max_order_value,
            COUNT(*) as total_purchases,
            COUNT(DISTINCT order_date) as unique_purchase_days,
            DATEDIFF(DATE'{observation_end_date}', MAX(order_date)) as recency_days,
            DATEDIFF(MAX(order_date), MIN(order_date)) as customer_lifetime_days,
            COUNT(DISTINCT product_id) as unique_products,
            COUNT(DISTINCT category_code) as unique_categories,
            COUNT(DISTINCT brand) as unique_brands
        FROM purchase_events
        GROUP BY customer_id
    ),
    quarterly_trends AS (
        SELECT 
            customer_id,
            SUM(CASE WHEN DATEDIFF(DATE'{observation_end_date}', order_date) <= 90 
                THEN price ELSE 0 END) as revenue_last_3m,
            COUNT(CASE WHEN DATEDIFF(DATE'{observation_end_date}', order_date) <= 90 
                THEN 1 END) as purchases_last_3m,
            SUM(CASE WHEN DATEDIFF(DATE'{observation_end_date}', order_date) BETWEEN 91 AND 180 
                THEN price ELSE 0 END) as revenue_3_6m,
            SUM(CASE WHEN DATEDIFF(DATE'{observation_end_date}', order_date) BETWEEN 181 AND 270 
                THEN price ELSE 0 END) as revenue_6_9m,
            SUM(CASE WHEN DATEDIFF(DATE'{observation_end_date}', order_date) BETWEEN 271 AND 365 
                THEN price ELSE 0 END) as revenue_9_12m
        FROM purchase_events
        GROUP BY customer_id
    )
    SELECT 
        bm.*,
        qt.revenue_last_3m,
        qt.revenue_3_6m,
        qt.revenue_6_9m,
        qt.revenue_9_12m,
        qt.purchases_last_3m,
        CASE WHEN qt.revenue_6_9m > 0
            THEN (qt.revenue_last_3m - qt.revenue_6_9m) / qt.revenue_6_9m
            ELSE 0
        END as revenue_growth_rate
    FROM base_metrics bm
    LEFT JOIN quarterly_trends qt ON bm.customer_id = qt.customer_id
    WHERE bm.total_purchases >= {MIN_PURCHASES_FOR_TRAINING}
    """
    
    features = spark.sql(features_query)
    features.persist(pyspark.StorageLevel.MEMORY_AND_DISK)
    return features

def train_clv_model(train_data, test_data):
    """
    Train gradient boosting CLV regression model.
    """
    print("\n🤖 Training CLV prediction model...")
    feature_cols = [col for col in train_data.columns if col not in ['customer_id', 'actual_clv_12m']]
    
    assembler = VectorAssembler(inputCols=feature_cols, outputCol='unscaled_features', handleInvalid='skip')
    scaler = StandardScaler(inputCol='unscaled_features', outputCol='features', withStd=True, withMean=True)
    gbt = GBTRegressor(labelCol='actual_clv_12m', featuresCol='features', maxIter=100, maxDepth=6, seed=42)
    
    pipeline = Pipeline(stages=[assembler, scaler, gbt])
    model = pipeline.fit(train_data)
    
    predictions = model.transform(test_data)
    evaluator = RegressionEvaluator(labelCol='actual_clv_12m', predictionCol='prediction', metricName='rmse')
    rmse = evaluator.evaluate(predictions)
    print(f"  ✅ Model trained. RMSE: ${rmse:.2f}")
    
    return model

def main():
    spark = get_spark_session()
    spark.sparkContext.setLogLevel("WARN")
    
    try:
        max_date = spark.sql("SELECT MAX(order_date) FROM nessie.ecommerce.`orders_silver@main`").collect()[0][0]
        prediction_end_date = max_date
        observation_end_date = max_date - timedelta(days=365)
        
        # Training Flow
        labels = create_training_labels(spark, observation_end_date, prediction_end_date)
        features = engineer_clv_features(spark, observation_end_date)
        training_data = features.join(labels, 'customer_id', 'inner')
        
        train_data, test_data = training_data.randomSplit([0.8, 0.2], seed=42)
        model = train_clv_model(train_data, test_data)
        
        # Inference Flow
        current_features = engineer_clv_features(spark, max_date)
        predictions = model.transform(current_features)
        
        predictions = predictions.withColumn('predicted_clv_12m', F.round('prediction', 2))
        predictions = predictions.withColumn(
            'value_tier',
            F.when(F.col('predicted_clv_12m') >= 1000, 'Platinum')
             .when(F.col('predicted_clv_12m') >= 500, 'Gold')
             .when(F.col('predicted_clv_12m') >= 200, 'Silver')
             .otherwise('Bronze')
        )
        
        output = predictions.select(
            'customer_id', 'predicted_clv_12m', 'value_tier', 
            'historical_revenue', 'total_purchases', 'recency_days',
            F.current_timestamp().alias('predicted_at')
        )
        
        output.writeTo("nessie.ecommerce.clv_predictions") \
            .partitionedBy("value_tier") \
            .createOrReplace()
            
        print(f"✅ CLV predictions written to nessie.ecommerce.clv_predictions@gold")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        spark.stop()

if __name__ == "__main__":
    main()
