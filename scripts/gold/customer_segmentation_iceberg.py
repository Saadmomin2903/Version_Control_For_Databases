"""
Customer Segmentation & Churn Prediction (Lakehouse Edition)
-------------------------------------------------------------
Uses Scikit-Learn for:
1. K-Means Customer Segmentation
2. Churn Prediction (Random Forest, Gradient Boosting)

Reads from: nessie.ecommerce.orders_silver@main (via Spark SQL -> Pandas)
Writes to: nessie.ecommerce.customer_ml_insights@gold (via Spark)
"""

import os
import pyspark
from pyspark.sql import SparkSession
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.model_selection import train_test_split, RandomizedSearchCV
from sklearn.metrics import classification_report, roc_auc_score, silhouette_score
from sklearn.pipeline import Pipeline

# Configuration
NESSIE_URI = os.getenv("NESSIE_URI", "http://nessie:19120/api/v1")
WAREHOUSE = os.getenv("WAREHOUSE", "s3a://lakehouse-prod/warehouse")
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY", "962c9f862226831e4edea90cfcfafb8a8dffcd51")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_KEY", "sd2rGU918DTmn35E4xJ8EV7BX2XUt7DkqC8v6WDNDUw=")
AWS_S3_ENDPOINT = os.getenv("AWS_S3_ENDPOINT", "https://bmcfe6z38foz.compat.objectstorage.ap-mumbai-1.oraclecloud.com")

def get_spark_session():
    """Initialize Spark with Nessie + Iceberg + S3 configuration"""
    conf = (
        pyspark.SparkConf()
        .setAppName('ml-customer-segmentation-churn')
        .set('spark.jars.packages',
             'org.apache.iceberg:iceberg-spark-runtime-3.3_2.12:1.3.1,'
             'org.projectnessie.nessie-integrations:nessie-spark-extensions-3.3_2.12:0.67.0,'
             'org.apache.hadoop:hadoop-aws:3.3.1')
        .set('spark.sql.extensions',
             'org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions,'
             'org.projectnessie.spark.extensions.NessieSparkSessionExtensions')
        .set('spark.sql.catalog.nessie', 'org.apache.iceberg.spark.SparkCatalog')
        .set('spark.sql.catalog.nessie.uri', NESSIE_URI)
        .set('spark.sql.catalog.nessie.ref', 'gold')
        .set('spark.sql.catalog.nessie.catalog-impl', 'org.apache.iceberg.nessie.NessieCatalog')
        .set('spark.sql.catalog.nessie.warehouse', WAREHOUSE)
        .set('spark.sql.catalog.nessie.io-impl', 'org.apache.iceberg.hadoop.HadoopFileIO')
        .set('spark.hadoop.fs.s3a.access.key', AWS_ACCESS_KEY)
        .set('spark.hadoop.fs.s3a.secret.key', AWS_SECRET_KEY)
        .set('spark.hadoop.fs.s3a.endpoint', AWS_S3_ENDPOINT)
        .set('spark.hadoop.fs.s3a.path.style.access', 'true')
        .set('spark.hadoop.fs.s3a.connection.ssl.enabled', 'true')
    )
    return SparkSession.builder.config(conf=conf).getOrCreate()

def run_sklearn_analysis():
    """Run customer segmentation and churn prediction"""
    spark = get_spark_session()
    
    try:
        print("📊 Loading customer data from Silver layer...")
        
        # Create user features from Silver orders
        user_features_query = """
        SELECT 
            customer_id,
            COUNT(DISTINCT user_session) as frequency,
            SUM(price) as monetary,
            DATEDIFF(MAX(order_date), MIN(order_date)) as tenure_days,
            DATEDIFF(CURRENT_DATE(), MAX(order_date)) as days_since_last_active,
            CASE 
                WHEN DATEDIFF(CURRENT_DATE(), MAX(order_date)) > 90 THEN 1
                ELSE 0
            END as is_churned
        FROM nessie.ecommerce.`orders_silver@main`
        WHERE event_type = 'purchase'
        AND customer_id IS NOT NULL
        GROUP BY customer_id
        HAVING frequency > 0
        """
        
        # Execute via Spark and convert to Pandas for sklearn
        df_spark = spark.sql(user_features_query)
        df = df_spark.toPandas()
        
        print(f"✅ Data loaded: {df.shape[0]} customers")
        
        # Handle missing values
        df = df.fillna(0)
        
        # ==========================================
        # 1. Customer Segmentation (K-Means)
        # ==========================================
        print("\n🎯 Customer Segmentation (K-Means)...")
        
        seg_features = ["frequency", "monetary", "tenure_days", "days_since_last_active"]
        X_seg = df[seg_features]
        
        # Scale features
        scaler = StandardScaler()
        X_seg_scaled = scaler.fit_transform(X_seg)
        
        # K-Means
        k = 4
        kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
        df['cluster'] = kmeans.fit_predict(X_seg_scaled)
        
        # Evaluate
        sil_score = silhouette_score(X_seg_scaled, df['cluster'], sample_size=min(5000, len(df)))
        print(f"  Silhouette Score: {sil_score:.4f}")
        
        # Cluster Profiles
        print("\n📊 Cluster Profiles:")
        print(df.groupby('cluster')[seg_features + ['is_churned']].mean().round(2))
        
        # ==========================================
        # 2. Churn Prediction
        # ==========================================
        print("\n🔮 Churn Prediction...")
        
        pred_features = ["frequency", "monetary", "tenure_days"]
        target = "is_churned"
        
        X = df[pred_features]
        y = df[target]
        
        # Split
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        print(f"  Train: {X_train.shape[0]} samples, Test: {X_test.shape[0]} samples")
        
        # Models
        models_params = {
            'RandomForest': {
                'model': RandomForestClassifier(random_state=42),
                'params': {
                    'classifier__n_estimators': [50, 100],
                    'classifier__max_depth': [None, 10],
                    'classifier__min_samples_split': [2, 5]
                }
            },
            'GradientBoosting': {
                'model': GradientBoostingClassifier(random_state=42),
                'params': {
                    'classifier__n_estimators': [50, 100],
                    'classifier__learning_rate': [0.1, 0.2],
                    'classifier__max_depth': [3, 5]
                }
            }
        }
        
        best_overall_model = None
        best_overall_score = -1
        best_overall_name = ""
        
        for name, mp in models_params.items():
            print(f"\n  Training {name}...")
            pipeline = Pipeline([
                ('scaler', StandardScaler()),
                ('classifier', mp['model'])
            ])
            
            clf = RandomizedSearchCV(
                pipeline, mp['params'],
                n_iter=5, cv=3,
                scoring='roc_auc',
                random_state=42,
                n_jobs=-1
            )
            clf.fit(X_train, y_train)
            
            print(f"    Best params: {clf.best_params_}")
            print(f"    Best CV ROC-AUC: {clf.best_score_:.4f}")
            
            if clf.best_score_ > best_overall_score:
                best_overall_score = clf.best_score_
                best_overall_model = clf.best_estimator_
                best_overall_name = name
        
        print(f"\n🏆 Best Model: {best_overall_name}")
        
        # Evaluate
        y_pred = best_overall_model.predict(X_test)
        y_prob = best_overall_model.predict_proba(X_test)[:, 1]
        
        print("\n📈 Test Set Performance:")
        print(classification_report(y_test, y_pred))
        auc = roc_auc_score(y_test, y_prob)
        print(f"ROC-AUC Score: {auc:.4f}")
        
        # Generate predictions for all customers
        df['churn_prediction'] = best_overall_model.predict(X)
        df['churn_probability'] = best_overall_model.predict_proba(X)[:, 1]
        
        # Map cluster to segment name
        df['segment'] = df['cluster'].map({
            0: 'Low Value',
            1: 'Medium Value',
            2: 'High Value',
            3: 'At Risk'
        })
        
        # ==========================================
        # 3. Write Results to Gold Layer
        # ==========================================
        print("\n💾 Writing ML insights to Gold layer...")
        
        # Convert back to Spark DataFrame
        results_df = spark.createDataFrame(df)
        
        # Write to Iceberg
        results_df.writeTo("nessie.ecommerce.customer_ml_insights").createOrReplace()
        
        print(f"✅ Saved ML insights for {len(df)} customers to nessie.ecommerce.customer_ml_insights@gold")
        print(f"   - Segmentation: {k} clusters")
        print(f"   - Churn Model: {best_overall_name} (AUC: {auc:.4f})")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        raise
    finally:
        spark.stop()

if __name__ == "__main__":
    run_sklearn_analysis()
