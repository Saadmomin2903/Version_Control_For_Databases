"""
Customer Segmentation Demo (Simplified for 5-day Dataset)
----------------------------------------------------------
Uses K-Means clustering to segment customers based on RFM metrics.
Works with limited time-range data (no churn prediction).

Reads from: nessie.ecommerce.orders_silver@main
Writes to: nessie.ecommerce.customer_segments@gold
"""

import os
import pyspark
from pyspark.sql import SparkSession
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

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
        .setAppName('ml-customer-segmentation')
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

def run_segmentation():
    """Run customer segmentation using K-Means"""
    spark = get_spark_session()
    
    try:
        print("📊 Loading customer data from Silver layer...")
        
        # Create RFM features from purchase events
        rfm_query = """
        SELECT 
            customer_id,
            COUNT(*) as frequency,
            SUM(price) as monetary,
            AVG(price) as avg_order_value
        FROM nessie.ecommerce.`orders_silver@main`
        WHERE event_type = 'purchase'
        AND customer_id IS NOT NULL
        AND price > 0
        GROUP BY customer_id
        HAVING frequency >= 2
        """
        
        # Execute via Spark and convert to Pandas for sklearn
        df_spark = spark.sql(rfm_query)
        df = df_spark.toPandas()
        
        print(f"✅ Data loaded: {df.shape[0]} customers with 2+ purchases")
        
        # ==========================================
        # K-Means Customer Segmentation
        # ==========================================
        print("\n🎯 Running K-Means Clustering...")
        
        features = ["frequency", "monetary", "avg_order_value"]
        X = df[features]
        
        # Scale features
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        # Try different k values
        silhouette_scores = []
        K_range = range(3, 7)
        
        for k in K_range:
            kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
            labels = kmeans.fit_predict(X_scaled)
            score = silhouette_score(X_scaled, labels, sample_size=min(5000, len(df)))
            silhouette_scores.append(score)
            print(f"  K={k}: Silhouette Score = {score:.4f}")
        
        # Use best k
        best_k_idx = silhouette_scores.index(max(silhouette_scores))
        best_k = list(K_range)[best_k_idx]
        
        print(f"\n🏆 Best K: {best_k} (Score: {max(silhouette_scores):.4f})")
        
        # Fit final model
        kmeans = KMeans(n_clusters=best_k, random_state=42, n_init=10)
        df['segment_id'] = kmeans.fit_predict(X_scaled)
        
        # Label segments based on monetary value
        segment_labels = {
            0: 'Low Value',
            1: 'Medium Value',
            2: 'High Value',
            3: 'VIP',
            4: 'Premium',
            5: 'Elite'
        }
        
        # Sort clusters by average monetary value
        cluster_means = df.groupby('segment_id')['monetary'].mean().sort_values()
        cluster_mapping = dict(zip(cluster_means.index, range(best_k)))
        
        df['segment_rank'] = df['segment_id'].map(cluster_mapping)
        df['segment_name'] = df['segment_rank'].map(
            lambda x: list(segment_labels.values())[x] if x < len(segment_labels) else 'Other'
        )
        
        # Show segment profiles
        print("\n📊 Segment Profiles:")
        profile = df.groupby('segment_name')[features].mean().round(2)
        profile['customer_count'] = df.groupby('segment_name').size()
        print(profile.sort_values('monetary', ascending=False))
        
        # ==========================================
        # Generate Visualizations
        # ==========================================
        print("\n📈 Generating visualizations...")
        
        try:
            import matplotlib
            matplotlib.use('Agg')  # Non-interactive backend for server
            import matplotlib.pyplot as plt
            import seaborn as sns
            
            # Set style
            sns.set_style("whitegrid")
            plt.rcParams['figure.figsize'] = (14, 10)
            
            # Create 2x2 subplot
            fig, axes = plt.subplots(2, 2, figsize=(14, 10))
            
            # 1. Segment Distribution (Pie Chart)
            segment_counts = df['segment_name'].value_counts()
            colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A']
            axes[0, 0].pie(segment_counts.values, labels=segment_counts.index, autopct='%1.1f%%',
                          colors=colors, startangle=90)
            axes[0, 0].set_title('Customer Segment Distribution', fontsize=14, fontweight='bold')
            
            # 2. Average Monetary Value by Segment (Bar Chart)
            segment_monetary = df.groupby('segment_name')['monetary'].mean().sort_values(ascending=False)
            bars = axes[0, 1].bar(range(len(segment_monetary)), segment_monetary.values, color=colors)
            axes[0, 1].set_xticks(range(len(segment_monetary)))
            axes[0, 1].set_xticklabels(segment_monetary.index, rotation=45, ha='right')
            axes[0, 1].set_ylabel('Average Lifetime Value ($)', fontweight='bold')
            axes[0, 1].set_title('Average Customer Value by Segment', fontsize=14, fontweight='bold')
            axes[0, 1].grid(axis='y', alpha=0.3)
            
            # Add value labels on bars
            for bar in bars:
                height = bar.get_height()
                axes[0, 1].text(bar.get_x() + bar.get_width()/2., height,
                               f'${height:.0f}', ha='center', va='bottom', fontweight='bold')
            
            # 3. Frequency Distribution by Segment (Box Plot)
            segment_order = df.groupby('segment_name')['monetary'].mean().sort_values(ascending=False).index
            sns.boxplot(data=df, x='segment_name', y='frequency', order=segment_order, 
                       palette=colors, ax=axes[1, 0])
            axes[1, 0].set_xlabel('Segment', fontweight='bold')
            axes[1, 0].set_ylabel('Purchase Frequency', fontweight='bold')
            axes[1, 0].set_title('Purchase Frequency Distribution', fontsize=14, fontweight='bold')
            axes[1, 0].tick_params(axis='x', rotation=45)
            
            # 4. Scatter: Frequency vs Monetary (colored by segment)
            for segment in segment_order:
                segment_data = df[df['segment_name'] == segment]
                axes[1, 1].scatter(segment_data['frequency'], segment_data['monetary'], 
                                 label=segment, alpha=0.6, s=50)
            axes[1, 1].set_xlabel('Purchase Frequency', fontweight='bold')
            axes[1, 1].set_ylabel('Lifetime Value ($)', fontweight='bold')
            axes[1, 1].set_title('Customer Value vs Frequency', fontsize=14, fontweight='bold')
            axes[1, 1].legend(loc='upper right')
            axes[1, 1].grid(alpha=0.3)
            
            plt.tight_layout()
            
            # Save to file
            viz_path = '/tmp/customer_segmentation_analysis.png'
            plt.savefig(viz_path, dpi=300, bbox_inches='tight')
            print(f"✅ Visualization saved to: {viz_path}")
            plt.close()
            
        except ImportError:
            print("⚠️  Matplotlib not available. Skipping visualizations.")
        except Exception as e:
            print(f"⚠️  Visualization error: {e}")
        
        # ==========================================
        # Write Results to Gold Layer
        # ==========================================
        print("\n💾 Writing segments to Gold layer...")
        
        # Select final columns
        results = df[['customer_id', 'frequency', 'monetary', 'avg_order_value', 
                      'segment_id', 'segment_name']]
        
        # Convert back to Spark DataFrame
        results_spark = spark.createDataFrame(results)
        
        # Write to Iceberg
        results_spark.writeTo("nessie.ecommerce.customer_segments").createOrReplace()
        
        print(f"✅ Saved {len(df)} customer segments to nessie.ecommerce.customer_segments@gold")
        print(f"   - Clusters: {best_k}")
        print(f"   - Silhouette Score: {max(silhouette_scores):.4f}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        spark.stop()

if __name__ == "__main__":
    run_segmentation()
