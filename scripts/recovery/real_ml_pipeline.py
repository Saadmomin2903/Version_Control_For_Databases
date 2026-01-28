"""
REAL ML Pipeline - Production Run with SparkML (FIXED)
Uses actual machine learning algorithms:
- FPGrowth for Product Recommendations
- KMeans for Customer Segmentation  
- GBTClassifier for Churn Prediction
- GBTRegressor for CLV Prediction
- GBTRegressor for Next Purchase Prediction
"""

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.window import Window
from pyspark.sql.types import DoubleType, IntegerType, FloatType

# SparkML imports
from pyspark.ml.feature import VectorAssembler, StandardScaler
from pyspark.ml.classification import GBTClassifier
from pyspark.ml.regression import GBTRegressor
from pyspark.ml.clustering import KMeans
from pyspark.ml.fpm import FPGrowth
from pyspark.ml import Pipeline
from pyspark.ml.evaluation import BinaryClassificationEvaluator, RegressionEvaluator
from pyspark.ml.linalg import Vectors, VectorUDT

# S3 Config
AWS_ACCESS_KEY = "962c9f862226831e4edea90cfcfafb8a8dffcd51"
AWS_SECRET_KEY = "sd2rGU918DTmn35E4xJ8EV7BX2XUt7DkqC8v6WDNDUw="
AWS_S3_ENDPOINT = "https://bmcfe6z38foz.compat.objectstorage.ap-mumbai-1.oraclecloud.com"
AWS_REGION = "ap-mumbai-1"
NESSIE_URI = "http://172.18.0.2:19120/api/v1"
WAREHOUSE = "s3a://lakehouse-prod/warehouse"

print("=" * 60)
print("🚀 REAL ML Pipeline with SparkML Algorithms (FIXED)")
print("=" * 60)
print("⚠️  This will take 15-30+ minutes to complete")
print("=" * 60)

spark = (SparkSession.builder
    .appName("real-ml-pipeline-v2")
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

# Register UDF to extract probability from vector
@F.udf(returnType=FloatType())
def extract_prob(probability):
    """Extract positive class probability from dense/sparse vector"""
    try:
        return float(probability[1])
    except:
        return 0.5

print("✅ Spark Session Created")

try:
    # ============================================
    # Load Source Data
    # ============================================
    print("\n📊 Loading orders_silver data...")
    
    orders_df = spark.sql("""
        SELECT 
            customer_id,
            product_id,
            brand,
            category_code,
            price,
            order_date
        FROM nessie.ecommerce.orders_silver 
        WHERE customer_id IS NOT NULL AND price > 0
        LIMIT 200000
    """)
    
    total_orders = orders_df.count()
    print(f"   Loaded {total_orders:,} orders")
    orders_df.cache()
    
    # ============================================
    # STAGE 1: FPGrowth - Product Recommendations
    # ============================================
    print("\n" + "=" * 60)
    print("📌 STAGE 1/5: FPGrowth Product Recommendations")
    print("=" * 60)
    
    # Create basket data
    baskets = orders_df.groupBy("customer_id").agg(
        F.collect_set("product_id").alias("items")
    ).filter(F.size("items") >= 2).limit(50000)
    
    print(f"   Training FPGrowth on {baskets.count():,} customer baskets...")
    
    fpgrowth = FPGrowth(itemsCol="items", minSupport=0.001, minConfidence=0.1)
    fpg_model = fpgrowth.fit(baskets)
    
    rules = fpg_model.associationRules
    rules_count = rules.count()
    print(f"   Found {rules_count:,} association rules")
    
    recommendations = rules.select(
        F.col("antecedent").getItem(0).alias("source_product"),
        F.col("consequent").getItem(0).alias("recommended_product"),
        F.round("confidence", 4).alias("confidence"),
        F.round("lift", 4).alias("lift"),
        "support"
    ).filter(F.col("source_product").isNotNull() & F.col("recommended_product").isNotNull())
    
    recommendations.writeTo("nessie.ecommerce.product_recommendations_ml").createOrReplace()
    rec_count = recommendations.count()
    print(f"   ✅ product_recommendations_ml created ({rec_count:,} rules)")
    
    # ============================================
    # STAGE 2: KMeans - Customer Segmentation
    # ============================================
    print("\n" + "=" * 60)
    print("📌 STAGE 2/5: KMeans Customer Segmentation")
    print("=" * 60)
    
    print("   Building customer feature matrix...")
    
    customer_features = orders_df.groupBy("customer_id").agg(
        F.datediff(F.current_date(), F.max("order_date")).alias("recency_days"),
        F.count("*").alias("frequency"),
        F.sum("price").alias("monetary_value"),
        F.avg("price").alias("avg_order_value"),
        F.countDistinct("product_id").alias("unique_products"),
        F.countDistinct("brand").alias("unique_brands"),
        F.countDistinct("category_code").alias("unique_categories")
    ).na.fill(0)
    
    customer_count = customer_features.count()
    print(f"   Created features for {customer_count:,} customers")
    
    feature_cols = ["recency_days", "frequency", "monetary_value", 
                    "avg_order_value", "unique_products", "unique_brands", "unique_categories"]
    
    assembler = VectorAssembler(inputCols=feature_cols, outputCol="features_raw", handleInvalid="skip")
    scaler = StandardScaler(inputCol="features_raw", outputCol="features", withStd=True, withMean=True)
    kmeans = KMeans(featuresCol="features", predictionCol="cluster", k=5, seed=42, maxIter=20)
    
    pipeline = Pipeline(stages=[assembler, scaler, kmeans])
    
    print("   Training KMeans model (k=5)...")
    kmeans_model = pipeline.fit(customer_features)
    
    clustered = kmeans_model.transform(customer_features)
    
    segments = clustered.withColumn(
        "segment",
        F.when(F.col("cluster") == 0, "Champions")
         .when(F.col("cluster") == 1, "Loyal Customers")
         .when(F.col("cluster") == 2, "Potential Loyalists")
         .when(F.col("cluster") == 3, "At Risk")
         .otherwise("Need Attention")
    ).select(
        "customer_id", "recency_days", "frequency", "monetary_value",
        "avg_order_value", "unique_products", "unique_brands", "cluster", "segment"
    )
    
    segments.writeTo("nessie.ecommerce.customer_segments_ml").createOrReplace()
    print(f"   ✅ customer_segments_ml created ({customer_count:,} customers)")
    
    print("\n   Cluster Distribution:")
    segments.groupBy("segment").count().orderBy(F.desc("count")).show()
    
    segments.cache()
    
    # ============================================
    # STAGE 3: GBTClassifier - Churn Prediction
    # ============================================
    print("\n" + "=" * 60)
    print("📌 STAGE 3/5: GBTClassifier Churn Prediction")
    print("=" * 60)
    
    churn_data = segments.withColumn(
        "churn_label",
        F.when(F.col("recency_days") > 30, 1.0).otherwise(0.0)
    )
    
    churn_feature_cols = ["recency_days", "frequency", "monetary_value", 
                          "avg_order_value", "unique_products", "unique_brands"]
    
    churn_assembler = VectorAssembler(inputCols=churn_feature_cols, outputCol="features_raw", handleInvalid="skip")
    churn_scaler = StandardScaler(inputCol="features_raw", outputCol="features", withStd=True, withMean=True)
    
    gbt_classifier = GBTClassifier(
        labelCol="churn_label",
        featuresCol="features",
        maxIter=50,
        maxDepth=5,
        seed=42
    )
    
    gbt_pipeline = Pipeline(stages=[churn_assembler, churn_scaler, gbt_classifier])
    
    train_data, test_data = churn_data.randomSplit([0.8, 0.2], seed=42)
    print(f"   Training: {train_data.count():,}, Testing: {test_data.count():,}")
    
    print("   Training GBTClassifier for churn prediction...")
    gbt_model = gbt_pipeline.fit(train_data)
    
    predictions = gbt_model.transform(test_data)
    evaluator = BinaryClassificationEvaluator(labelCol="churn_label", rawPredictionCol="rawPrediction")
    auc = evaluator.evaluate(predictions)
    print(f"   Model AUC-ROC: {auc:.4f}")
    
    all_predictions = gbt_model.transform(churn_data)
    
    # Use UDF to extract probability
    churn_results = all_predictions.withColumn(
        "churn_probability", 
        F.round(extract_prob(F.col("probability")), 4)
    ).withColumn(
        "risk_category",
        F.when(F.col("churn_probability") >= 0.7, "High")
         .when(F.col("churn_probability") >= 0.4, "Medium")
         .otherwise("Low")
    ).withColumn(
        "prediction_date", F.current_timestamp()
    ).withColumn(
        "model_auc", F.lit(round(auc, 4))
    ).select(
        "customer_id", "recency_days", "frequency", "monetary_value",
        "churn_probability", "risk_category", "model_auc", "prediction_date"
    )
    
    churn_results.writeTo("nessie.ecommerce.churn_predictions_ml").createOrReplace()
    churn_count = churn_results.count()
    print(f"   ✅ churn_predictions_ml created ({churn_count:,} predictions)")
    
    print("\n   Risk Distribution:")
    churn_results.groupBy("risk_category").count().orderBy(F.desc("count")).show()
    
    # ============================================
    # STAGE 4: GBTRegressor - CLV Prediction
    # ============================================
    print("\n" + "=" * 60)
    print("📌 STAGE 4/5: GBTRegressor CLV Prediction")
    print("=" * 60)
    
    clv_data = segments.filter(F.col("monetary_value") > 0)
    
    clv_feature_cols = ["recency_days", "frequency", "avg_order_value", 
                        "unique_products", "unique_brands"]
    
    clv_assembler = VectorAssembler(inputCols=clv_feature_cols, outputCol="features_raw", handleInvalid="skip")
    clv_scaler = StandardScaler(inputCol="features_raw", outputCol="features", withStd=True, withMean=True)
    
    clv_regressor = GBTRegressor(
        labelCol="monetary_value",
        featuresCol="features",
        maxIter=50,
        maxDepth=5,
        seed=42
    )
    
    clv_pipeline = Pipeline(stages=[clv_assembler, clv_scaler, clv_regressor])
    
    train_clv, test_clv = clv_data.randomSplit([0.8, 0.2], seed=42)
    print(f"   Training: {train_clv.count():,}, Testing: {test_clv.count():,}")
    
    print("   Training GBTRegressor for CLV prediction...")
    clv_model = clv_pipeline.fit(train_clv)
    
    clv_predictions = clv_model.transform(test_clv)
    rmse_evaluator = RegressionEvaluator(labelCol="monetary_value", predictionCol="prediction", metricName="rmse")
    r2_evaluator = RegressionEvaluator(labelCol="monetary_value", predictionCol="prediction", metricName="r2")
    rmse = rmse_evaluator.evaluate(clv_predictions)
    r2 = r2_evaluator.evaluate(clv_predictions)
    print(f"   Model RMSE: ${rmse:.2f}, R²: {r2:.4f}")
    
    all_clv = clv_model.transform(clv_data)
    
    clv_results = all_clv.withColumn(
        "predicted_clv_12m", F.round(F.col("prediction") * 12, 2)
    ).withColumn(
        "value_tier",
        F.when(F.col("predicted_clv_12m") >= 2000, "Platinum")
         .when(F.col("predicted_clv_12m") >= 1000, "Gold")
         .when(F.col("predicted_clv_12m") >= 500, "Silver")
         .otherwise("Bronze")
    ).withColumn(
        "prediction_date", F.current_timestamp()
    ).withColumn(
        "model_rmse", F.lit(round(rmse, 2))
    ).withColumn(
        "model_r2", F.lit(round(r2, 4))
    ).select(
        "customer_id", "monetary_value", "predicted_clv_12m", "value_tier", 
        "segment", "model_rmse", "model_r2", "prediction_date"
    )
    
    clv_results.writeTo("nessie.ecommerce.clv_predictions_ml").createOrReplace()
    clv_count = clv_results.count()
    print(f"   ✅ clv_predictions_ml created ({clv_count:,} predictions)")
    
    print("\n   Value Tier Distribution:")
    clv_results.groupBy("value_tier").count().orderBy(F.desc("count")).show()
    
    # ============================================
    # STAGE 5: GBTRegressor - Next Purchase Prediction
    # ============================================
    print("\n" + "=" * 60)
    print("📌 STAGE 5/5: GBTRegressor Next Purchase Prediction")
    print("=" * 60)
    
    purchase_intervals = orders_df.select("customer_id", "order_date").distinct()
    
    intervals = purchase_intervals.withColumn(
        "prev_date", 
        F.lag("order_date").over(Window.partitionBy("customer_id").orderBy("order_date"))
    ).withColumn(
        "days_between", F.datediff("order_date", "prev_date")
    ).filter(F.col("days_between").isNotNull() & (F.col("days_between") > 0))
    
    avg_intervals = intervals.groupBy("customer_id").agg(
        F.avg("days_between").alias("avg_interval"),
        F.stddev("days_between").alias("interval_stddev"),
        F.count("*").alias("interval_count")
    ).na.fill(0)
    
    npp_data = segments.join(avg_intervals, "customer_id", "left").na.fill({"avg_interval": 30, "interval_stddev": 0, "interval_count": 0})
    
    npp_feature_cols = ["recency_days", "frequency", "monetary_value", 
                        "avg_order_value", "unique_products", "interval_stddev", "interval_count"]
    
    npp_assembler = VectorAssembler(inputCols=npp_feature_cols, outputCol="features_raw", handleInvalid="skip")
    npp_scaler = StandardScaler(inputCol="features_raw", outputCol="features", withStd=True, withMean=True)
    
    npp_regressor = GBTRegressor(
        labelCol="avg_interval",
        featuresCol="features",
        maxIter=50,
        maxDepth=5,
        seed=42
    )
    
    npp_pipeline = Pipeline(stages=[npp_assembler, npp_scaler, npp_regressor])
    
    npp_train_data = npp_data.filter(F.col("avg_interval") > 0)
    
    train_npp, test_npp = npp_train_data.randomSplit([0.8, 0.2], seed=42)
    print(f"   Training: {train_npp.count():,}, Testing: {test_npp.count():,}")
    
    print("   Training GBTRegressor for next purchase prediction...")
    npp_model = npp_pipeline.fit(train_npp)
    
    npp_predictions = npp_model.transform(test_npp)
    npp_rmse_eval = RegressionEvaluator(labelCol="avg_interval", predictionCol="prediction", metricName="rmse")
    npp_r2_eval = RegressionEvaluator(labelCol="avg_interval", predictionCol="prediction", metricName="r2")
    npp_rmse = npp_rmse_eval.evaluate(npp_predictions)
    npp_r2 = npp_r2_eval.evaluate(npp_predictions)
    print(f"   Model RMSE: {npp_rmse:.2f} days, R²: {npp_r2:.4f}")
    
    all_npp = npp_model.transform(npp_data)
    
    npp_results = all_npp.withColumn(
        "predicted_days_to_next",
        F.greatest(F.round(F.col("prediction") - F.col("recency_days")).cast(IntegerType()), F.lit(1))
    ).withColumn(
        "predicted_next_date", F.date_add(F.current_date(), F.col("predicted_days_to_next"))
    ).withColumn(
        "purchase_urgency",
        F.when(F.col("predicted_days_to_next") <= 7, "High")
         .when(F.col("predicted_days_to_next") <= 21, "Medium")
         .otherwise("Low")
    ).withColumn(
        "prediction_date", F.current_timestamp()
    ).withColumn(
        "model_rmse", F.lit(round(npp_rmse, 2))
    ).select(
        "customer_id", "recency_days", "avg_interval",
        "predicted_days_to_next", "predicted_next_date", "purchase_urgency", 
        "model_rmse", "prediction_date"
    )
    
    npp_results.writeTo("nessie.ecommerce.next_purchase_predictions_ml").createOrReplace()
    npp_count = npp_results.count()
    print(f"   ✅ next_purchase_predictions_ml created ({npp_count:,} predictions)")
    
    print("\n   Purchase Urgency Distribution:")
    npp_results.groupBy("purchase_urgency").count().orderBy(F.desc("count")).show()
    
    # ============================================
    # Summary
    # ============================================
    print("\n" + "=" * 60)
    print("🎉 REAL ML PIPELINE COMPLETED SUCCESSFULLY!")
    print("=" * 60)
    
    print("\n📊 Model Performance Summary:")
    print(f"   ┌─────────────────────────────────────────┐")
    print(f"   │ Model                  │ Metrics       │")
    print(f"   ├─────────────────────────────────────────┤")
    print(f"   │ Churn Classifier (GBT) │ AUC: {auc:.4f}  │")
    print(f"   │ CLV Regressor (GBT)    │ RMSE: ${rmse:.2f}, R²: {r2:.4f} │")
    print(f"   │ NPP Regressor (GBT)    │ RMSE: {npp_rmse:.2f} days, R²: {npp_r2:.4f} │")
    print(f"   └─────────────────────────────────────────┘")
    
    print("\n📋 Tables Created (with ML suffix):")
    print(f"   - product_recommendations_ml: {rec_count:,} rules (FPGrowth)")
    print(f"   - customer_segments_ml: {customer_count:,} customers (KMeans k=5)")
    print(f"   - churn_predictions_ml: {churn_count:,} predictions (GBTClassifier)")
    print(f"   - clv_predictions_ml: {clv_count:,} predictions (GBTRegressor)")
    print(f"   - next_purchase_predictions_ml: {npp_count:,} predictions (GBTRegressor)")
    
    print("\n📋 All tables on Main branch:")
    spark.sql("SHOW TABLES IN nessie.ecommerce").show(30, False)
    
except Exception as e:
    print(f"\n❌ ERROR: {str(e)}")
    import traceback
    traceback.print_exc()
finally:
    spark.stop()
    print("\n🛑 Spark Session Stopped")
