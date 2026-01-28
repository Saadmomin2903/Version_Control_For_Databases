"""
Product Recommendation Validation & Quality Check
-------------------------------------------------
Validates recommendation quality, coverage, and business metrics.
Run before and after recommendation generation.
"""

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from datetime import datetime
import sys
import os

# Add current directory to path so we can import the other script
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def validate_transaction_data(spark):
    """Validate source transaction data quality"""
    print("\n" + "="*70)
    print("📋 TRANSACTION DATA VALIDATION")
    print("="*70)
    
    orders = spark.table("nessie.ecommerce.orders_silver")
    
    print("\n1️⃣  Overall Transaction Statistics:")
    total_orders = orders.count()
    purchases = orders.filter(F.col('event_type') == 'purchase')
    purchase_count = purchases.count()
    
    print(f"   Total events: {total_orders:,}")
    print(f"   Purchase events: {purchase_count:,} ({purchase_count/total_orders*100:.1f}%)")
    
    # Session analysis
    print("\n2️⃣  Session Analysis:")
    session_stats = purchases.groupBy('user_session').agg(
        F.count('product_id').alias('products_per_session')
    ).agg(
        F.count('user_session').alias('total_sessions'),
        F.avg('products_per_session').alias('avg_products'),
        F.min('products_per_session').alias('min_products'),
        F.max('products_per_session').alias('max_products'),
        F.expr('percentile(products_per_session, 0.5)').alias('median_products'),
        F.expr('percentile(products_per_session, 0.95)').alias('p95_products')
    ).collect()[0]
    
    print(f"   Total sessions: {session_stats['total_sessions']:,}")
    print(f"   Avg products/session: {session_stats['avg_products']:.2f}")
    print(f"   Median products/session: {session_stats['median_products']}")
    print(f"   95th percentile: {session_stats['p95_products']}")
    print(f"   Max products/session: {session_stats['max_products']}")
    
    # Outlier detection
    if session_stats['max_products'] > 100:
        outlier_sessions = purchases.groupBy('user_session').agg(
            F.count('product_id').alias('products')
        ).filter(F.col('products') > 100).count()
        
        print(f"   ⚠️  Sessions with >100 products: {outlier_sessions:,}")
        print("   💡 Recommendation: These may be bots or test sessions")
    
    # Product diversity
    print("\n3️⃣  Product Diversity:")
    product_stats = purchases.agg(
        F.countDistinct('product_id').alias('unique_products'),
        F.count('product_id').alias('total_purchases')
    ).collect()[0]
    
    print(f"   Unique products: {product_stats['unique_products']:,}")
    print(f"   Total purchases: {product_stats['total_purchases']:,}")
    print(f"   Purchases per product: {product_stats['total_purchases']/product_stats['unique_products']:.2f}")
    
    # Product frequency distribution
    print("\n4️⃣  Product Frequency Distribution:")
    product_freq = purchases.groupBy('product_id').count()
    
    freq_distribution = product_freq.agg(
        F.expr('percentile(count, 0.1)').alias('p10'),
        F.expr('percentile(count, 0.25)').alias('p25'),
        F.expr('percentile(count, 0.5)').alias('p50'),
        F.expr('percentile(count, 0.75)').alias('p75'),
        F.expr('percentile(count, 0.9)').alias('p90'),
        F.expr('percentile(count, 0.95)').alias('p95'),
        F.max('count').alias('max_freq')
    ).collect()[0]
    
    print(f"   10th percentile: {freq_distribution['p10']}")
    print(f"   25th percentile: {freq_distribution['p25']}")
    print(f"   Median: {freq_distribution['p50']}")
    print(f"   75th percentile: {freq_distribution['p75']}")
    print(f"   90th percentile: {freq_distribution['p90']}")
    print(f"   95th percentile: {freq_distribution['p95']}")
    print(f"   Max frequency: {freq_distribution['max_freq']}")
    
    # Low-frequency products (potential noise)
    low_freq_products = product_freq.filter(F.col('count') < 10).count()
    total_products = product_freq.count()
    
    print(f"\n   Products with <10 purchases: {low_freq_products:,} ({low_freq_products/total_products*100:.1f}%)")
    
    if low_freq_products/total_products > 0.5:
        print("   ⚠️  Over 50% of products are rarely purchased")
        print("   💡 Recommendation: Use MIN_PRODUCT_FREQUENCY filter")
    
    # Date range and recency
    print("\n5️⃣  Temporal Analysis:")
    date_stats = purchases.agg(
        F.min('order_date').alias('earliest_date'),
        F.max('order_date').alias('latest_date'),
        F.countDistinct('order_date').alias('unique_dates')
    ).collect()[0]
    
    print(f"   Date range: {date_stats['earliest_date']} to {date_stats['latest_date']}")
    print(f"   Unique dates: {date_stats['unique_dates']}")
    
    # Recent activity (last 90 days)
    recent_purchases = purchases.filter(
        F.datediff(F.lit(date_stats['latest_date']), F.col('order_date')) <= 90
    ).count()
    
    print(f"   Purchases in last 90 days: {recent_purchases:,} ({recent_purchases/purchase_count*100:.1f}%)")
    
    return {
        'total_sessions': session_stats['total_sessions'],
        'avg_basket_size': session_stats['avg_products'],
        'unique_products': product_stats['unique_products']
    }

def validate_recommendations(spark):
    """Validate recommendation output quality"""
    print("\n" + "="*70)
    print("🔍 RECOMMENDATION VALIDATION")
    print("="*70)
    
    try:
        recs = spark.table("nessie.ecommerce.product_recommendations")
        
        # Basic statistics
        print("\n1️⃣  Recommendation Statistics:")
        total_recs = recs.count()
        unique_products = recs.select('product_id').distinct().count()
        
        print(f"   Total recommendations: {total_recs:,}")
        print(f"   Products with recommendations: {unique_products:,}")
        
        if total_recs > 0:
            avg_recs_per_product = total_recs / unique_products
            print(f"   Avg recommendations per product: {avg_recs_per_product:.2f}")
        
        # Quality metrics
        print("\n2️⃣  Quality Metrics:")
        quality_stats = recs.agg(
            F.avg('confidence').alias('avg_confidence'),
            F.min('confidence').alias('min_confidence'),
            F.max('confidence').alias('max_confidence'),
            F.avg('lift').alias('avg_lift'),
            F.min('lift').alias('min_lift'),
            F.max('lift').alias('max_lift'),
            F.avg('recommendation_score').alias('avg_score')
        ).collect()[0]
        
        print(f"   Confidence (avg): {quality_stats['avg_confidence']:.3f}")
        print(f"   Confidence (min): {quality_stats['min_confidence']:.3f}")
        print(f"   Confidence (max): {quality_stats['max_confidence']:.3f}")
        print(f"   Lift (avg): {quality_stats['avg_lift']:.3f}")
        print(f"   Lift (min): {quality_stats['min_lift']:.3f}")
        print(f"   Lift (max): {quality_stats['max_lift']:.3f}")
        print(f"   Recommendation Score (avg): {quality_stats['avg_score']:.3f}")
        
        # Quality thresholds check
        low_confidence_recs = recs.filter(F.col('confidence') < 0.1).count()
        low_lift_recs = recs.filter(F.col('lift') <= 1.0).count()
        
        if low_confidence_recs > 0:
            print(f"   ⚠️  {low_confidence_recs:,} recommendations with confidence < 0.1")
        
        if low_lift_recs > 0:
            print(f"   ⚠️  {low_lift_recs:,} recommendations with lift <= 1.0 (should be filtered)")
        
        # Coverage analysis
        print("\n3️⃣  Coverage Analysis:")
        
        all_products = spark.sql("""
            SELECT DISTINCT product_id
            FROM nessie.ecommerce.`orders_silver@main`
            WHERE event_type = 'purchase'
              AND product_id IS NOT NULL
        """)
        
        total_products = all_products.count()
        coverage_pct = (unique_products / total_products) * 100
        
        print(f"   Total products in catalog: {total_products:,}")
        print(f"   Products with recommendations: {unique_products:,}")
        print(f"   Coverage: {coverage_pct:.1f}%")
        
        if coverage_pct < 20:
            print("   ⚠️  Very low coverage (<20%)")
            print("   💡 Recommendation: Lower minSupport or MIN_PRODUCT_FREQUENCY")
        elif coverage_pct < 50:
            print("   ⚠️  Moderate coverage (<50%)")
            print("   💡 Consider hybrid approach (FPGrowth + content-based)")
        else:
            print("   ✅ Good coverage!")
        
        # Rank distribution
        print("\n4️⃣  Recommendation Rank Distribution:")
        recs.groupBy('rank').count().orderBy('rank').show()
        
        # Top recommended products
        print("\n5️⃣  Most Frequently Recommended Products:")
        top_recs = recs.groupBy('recommended_product_id').agg(
            F.count('product_id').alias('times_recommended')
        ).orderBy(F.desc('times_recommended')).limit(10)
        
        top_recs.show(truncate=False)
        
        # Self-recommendations check (should be none)
        self_recs = recs.filter(F.col('product_id') == F.col('recommended_product_id')).count()
        
        if self_recs > 0:
            print(f"   ❌ CRITICAL: {self_recs:,} self-recommendations found!")
            print("   💡 These should be filtered out")
        else:
            print("   ✅ No self-recommendations (good!)")
        
        # Freshness check
        print("\n6️⃣  Data Freshness:")
        latest_gens = recs.agg(F.max('generated_at')).collect()[0][0]
        
        if latest_gens:
            print(f"   Last generated: {latest_gens}")
            
            # Check if stale (>7 days old)
            from datetime import datetime, timedelta
            if isinstance(latest_gens, str):
                latest_gens = datetime.fromisoformat(latest_gens.replace('Z', '+00:00'))
            
            age_days = (datetime.now() - latest_gens.replace(tzinfo=None)).days
            
            print(f"   Age: {age_days} days")
            
            if age_days > 7:
                print("   ⚠️  Recommendations are >7 days old")
                print("   💡 Consider re-running the pipeline")
            else:
                print("   ✅ Recommendations are fresh")
        
        return True
        
    except Exception as e:
        print(f"❌ Recommendations table not found or error: {e}")
        print("💡 Run the recommendation pipeline first")
        return False

def validate_frequent_itemsets(spark):
    """Validate frequent itemsets table"""
    print("\n" + "="*70)
    print("📦 FREQUENT ITEMSETS VALIDATION")
    print("="*70)
    
    try:
        itemsets = spark.table("nessie.ecommerce.frequent_itemsets")
        
        total_itemsets = itemsets.count()
        print(f"\n✅ Total frequent itemsets: {total_itemsets:,}")
        
        # Size distribution
        print("\n📊 Itemset Size Distribution:")
        size_dist = itemsets.groupBy('itemset_size').agg(
            F.count('*').alias('count'),
            F.avg('frequency').alias('avg_frequency')
        ).orderBy('itemset_size')
        
        size_dist.show(truncate=False)
        
        # Top frequent itemsets
        print("\n🔝 Top 10 Most Frequent Itemsets:")
        itemsets.orderBy(F.desc('frequency')).limit(10).show(truncate=False)
        
        return True
        
    except Exception as e:
        print(f"❌ Frequent itemsets table not found: {e}")
        return False

def generate_recommendation_samples(spark):
    """Generate sample recommendations for manual review"""
    print("\n" + "="*70)
    print("🎯 SAMPLE RECOMMENDATIONS FOR REVIEW")
    print("="*70)
    
    try:
        recs = spark.table("nessie.ecommerce.product_recommendations")
        
        # Sample high-quality recommendations
        print("\n1️⃣  High-Quality Recommendations (Lift > 3.0):")
        high_quality = recs.filter(F.col('lift') > 3.0).limit(5)
        high_quality.select(
            'product_id',
            'recommended_product_id',
            'confidence',
            'lift',
            'recommendation_score'
        ).show(truncate=False)
        
        # Sample medium-quality recommendations
        print("\n2️⃣  Medium-Quality Recommendations (Lift 1.5-3.0):")
        medium_quality = recs.filter(
            (F.col('lift') >= 1.5) & (F.col('lift') <= 3.0)
        ).limit(5)
        medium_quality.select(
            'product_id',
            'recommended_product_id',
            'confidence',
            'lift',
            'recommendation_score'
        ).show(truncate=False)
        
        # Sample for a specific product
        print("\n3️⃣  Sample Recommendations for Random Products:")
        sample_products = recs.select('product_id').distinct().limit(3)
        
        for row in sample_products.collect():
            product_id = row['product_id']
            product_recs = recs.filter(F.col('product_id') == product_id).orderBy('rank')
            
            print(f"\n   Product {product_id}:")
            product_recs.select(
                'rank',
                'recommended_product_id',
                'recommendation_score',
                'confidence',
                'lift'
            ).show(truncate=False)
        
    except Exception as e:
        print(f"❌ Could not generate samples: {e}")

def main():
    """Run complete validation suite"""
    try:
        from product_recommendation_iceberg import get_spark_session
    except ImportError:
        print("⚠️ Could not import get_spark_session from product_recommendation_iceberg.")
        raise
    
    spark = get_spark_session()
    spark.sparkContext.setLogLevel("WARN")
    
    try:
        print("\n🚀 Starting Product Recommendation Validation")
        print(f"⏰ Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Pre-training validation
        stats = validate_transaction_data(spark)
        
        # Post-training validation
        recs_exist = validate_recommendations(spark)
        
        if recs_exist:
            validate_frequent_itemsets(spark)
            generate_recommendation_samples(spark)
        else:
            print("\n⏭️  Skipping recommendation validation (run pipeline first)")
        
        print("\n✅ Validation completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Validation failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        spark.stop()

if __name__ == "__main__":
    main()
