"""
Data Quality & Segmentation Validation Script
---------------------------------------------
Validates data quality and monitors segmentation results.
Run this before and after segmentation to ensure data integrity.
"""

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from datetime import datetime
import sys
import os

# Add current directory to path so we can import the other script
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def validate_silver_tables(spark):
    """Validate Silver layer tables for quality and completeness"""
    print("\n" + "="*70)
    print("📋 SILVER LAYER VALIDATION")
    print("="*70)
    
    # Orders Silver Validation
    print("\n1️⃣  Orders Silver Table:")
    orders = spark.table("nessie.ecommerce.orders_silver")
    
    total_orders = orders.count()
    print(f"   Total Records: {total_orders:,}")
    
    # Check for nulls in critical columns
    null_checks = orders.select([
        F.sum(F.when(F.col(c).isNull(), 1).otherwise(0)).alias(c)
        for c in ['customer_id', 'price', 'order_date', 'event_type']
    ])
    
    print("\n   Null Value Counts:")
    null_checks.show()
    
    # Purchase records only
    purchases = orders.filter(F.col('event_type') == 'purchase')
    purchase_count = purchases.count()
    print(f"   Purchase Records: {purchase_count:,} ({purchase_count/total_orders*100:.2f}%)")
    
    # Data quality score distribution
    print("\n   Data Quality Score Distribution:")
    orders.groupBy('data_quality_score').count().orderBy('data_quality_score').show()
    
    # Date range
    date_range = orders.select(
        F.min('order_date').alias('min_date'),
        F.max('order_date').alias('max_date')
    ).collect()[0]
    print(f"   Date Range: {date_range['min_date']} to {date_range['max_date']}")
    
    # Price statistics
    print("\n   Price Statistics (Purchase Events):")
    purchases.select(
        F.min('price').alias('min_price'),
        F.max('price').alias('max_price'),
        F.avg('price').alias('avg_price'),
        F.stddev('price').alias('stddev_price')
    ).show()
    
    # Customers Silver Validation
    print("\n2️⃣  Customers Silver Table:")
    customers = spark.table("nessie.ecommerce.customers_silver")
    
    total_customers = customers.count()
    print(f"   Total Customers: {total_customers:,}")
    
    # Check email validity
    invalid_emails = customers.filter(
        ~F.col('email').rlike(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    ).count()
    print(f"   Invalid Emails: {invalid_emails:,} ({invalid_emails/total_customers*100:.2f}%)")
    
    # Check for duplicate customer_ids
    duplicate_customers = customers.groupBy('customer_id').count().filter(F.col('count') > 1).count()
    print(f"   Duplicate Customer IDs: {duplicate_customers:,}")
    
    return {
        'total_orders': total_orders,
        'total_purchases': purchase_count,
        'total_customers': total_customers
    }

def analyze_customer_purchase_patterns(spark):
    """Analyze purchase patterns to understand data distribution"""
    print("\n" + "="*70)
    print("📊 CUSTOMER PURCHASE PATTERN ANALYSIS")
    print("="*70)
    
    purchase_stats = spark.sql("""
    SELECT 
        COUNT(DISTINCT customer_id) as unique_customers,
        COUNT(*) as total_purchases,
        AVG(purchases_per_customer) as avg_purchases,
        PERCENTILE(purchases_per_customer, 0.5) as median_purchases,
        PERCENTILE(purchases_per_customer, 0.75) as p75_purchases,
        PERCENTILE(purchases_per_customer, 0.90) as p90_purchases,
        PERCENTILE(purchases_per_customer, 0.95) as p95_purchases,
        MAX(purchases_per_customer) as max_purchases
    FROM (
        SELECT 
            customer_id,
            COUNT(*) as purchases_per_customer
        FROM nessie.ecommerce.`orders_silver@main`
        WHERE event_type = 'purchase'
          AND customer_id IS NOT NULL
          AND price > 0
        GROUP BY customer_id
    )
    """)
    
    print("\n📈 Purchase Frequency Distribution:")
    purchase_stats.show(truncate=False)
    
    # Revenue distribution
    revenue_stats = spark.sql("""
    SELECT 
        PERCENTILE(total_revenue, 0.25) as p25_revenue,
        PERCENTILE(total_revenue, 0.5) as median_revenue,
        PERCENTILE(total_revenue, 0.75) as p75_revenue,
        PERCENTILE(total_revenue, 0.90) as p90_revenue,
        PERCENTILE(total_revenue, 0.95) as p95_revenue,
        PERCENTILE(total_revenue, 0.99) as p99_revenue,
        MAX(total_revenue) as max_revenue
    FROM (
        SELECT 
            customer_id,
            SUM(price) as total_revenue
        FROM nessie.ecommerce.`orders_silver@main`
        WHERE event_type = 'purchase'
          AND customer_id IS NOT NULL
          AND price > 0
        GROUP BY customer_id
    )
    """)
    
    print("\n💰 Revenue Distribution:")
    revenue_stats.show(truncate=False)

def validate_segmentation_results(spark):
    """Validate segmentation output and check for issues"""
    print("\n" + "="*70)
    print("🔍 SEGMENTATION RESULTS VALIDATION")
    print("="*70)
    
    try:
        segments = spark.table("nessie.ecommerce.customer_segments")
        
        # Basic counts
        total_segmented = segments.count()
        print(f"\n✅ Total Segmented Customers: {total_segmented:,}")
        
        # Segment distribution
        print("\n📊 Segment Distribution:")
        segment_dist = segments.groupBy('segment_name').agg(
            F.count('customer_id').alias('count'),
            (F.count('customer_id') / total_segmented * 100).alias('percentage')
        ).orderBy(F.desc('count'))
        segment_dist.show(truncate=False)
        
        # Check for nulls
        print("\n🔍 Null Value Check:")
        null_check = segments.select([
            F.sum(F.when(F.col(c).isNull(), 1).otherwise(0)).alias(c)
            for c in segments.columns
        ])
        null_check.show()
        
        # Cluster balance check (warn if highly imbalanced)
        cluster_sizes = segments.groupBy('cluster_id').count().collect()
        max_cluster = max(cluster_sizes, key=lambda x: x['count'])['count']
        min_cluster = min(cluster_sizes, key=lambda x: x['count'])['count']
        imbalance_ratio = max_cluster / min_cluster if min_cluster > 0 else float('inf')
        
        print(f"\n⚖️  Cluster Balance Ratio: {imbalance_ratio:.2f}")
        if imbalance_ratio > 10:
            print("   ⚠️  WARNING: Clusters are highly imbalanced! Consider adjusting K or features.")
        else:
            print("   ✅ Cluster balance looks good")
        
        # Feature statistics by segment
        print("\n📈 Feature Statistics by Segment:")
        segments.groupBy('segment_name').agg(
            F.count('customer_id').alias('count'),
            F.round(F.avg('recency_days'), 2).alias('avg_recency'),
            F.round(F.avg('frequency'), 2).alias('avg_frequency'),
            F.round(F.avg('monetary_value'), 2).alias('avg_monetary'),
            F.round(F.avg('avg_order_value'), 2).alias('avg_order_val')
        ).orderBy(F.desc('avg_monetary')).show(truncate=False)
        
        # Check for outliers
        print("\n🎯 Outlier Detection:")
        outlier_stats = segments.select(
            F.percentile_approx('monetary_value', 0.99).alias('p99_monetary'),
            F.percentile_approx('frequency', 0.99).alias('p99_frequency'),
            F.max('monetary_value').alias('max_monetary'),
            F.max('frequency').alias('max_frequency')
        ).collect()[0]
        
        print(f"   99th Percentile Monetary: ${outlier_stats['p99_monetary']:,.2f}")
        print(f"   Max Monetary: ${outlier_stats['max_monetary']:,.2f}")
        print(f"   99th Percentile Frequency: {outlier_stats['p99_frequency']}")
        print(f"   Max Frequency: {outlier_stats['max_frequency']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Segmentation table not found or error: {e}")
        return False

def generate_business_insights(spark):
    """Generate actionable business insights from segmentation"""
    print("\n" + "="*70)
    print("💡 BUSINESS INSIGHTS & RECOMMENDATIONS")
    print("="*70)
    
    try:
        segments = spark.table("nessie.ecommerce.customer_segments")
        
        # Top revenue segments
        print("\n1️⃣  Revenue Contribution:")
        total_revenue = segments.agg(F.sum('monetary_value')).collect()[0][0]
        
        revenue_contrib = segments.groupBy('segment_name').agg(
            F.sum('monetary_value').alias('segment_revenue'),
            F.count('customer_id').alias('customer_count')
        ).withColumn('revenue_pct', F.round((F.col('segment_revenue') / total_revenue) * 100, 2))
        
        revenue_contrib.orderBy(F.desc('revenue_pct')).show(truncate=False)
        
        # At-risk customers
        print("\n2️⃣  Customer Retention Focus:")
        at_risk = segments.filter(
            (F.col('recency_days') > 90) & (F.col('monetary_value') > 100)
        ).count()
        
        print(f"   High-value customers inactive >90 days: {at_risk:,}")
        print("   💡 Recommendation: Launch re-engagement campaign")
        
        # Growth opportunities
        print("\n3️⃣  Growth Opportunities:")
        growth_segment = segments.filter(
            (F.col('frequency') >= 3) & (F.col('avg_order_value') < 50)
        ).count()
        
        print(f"   Frequent buyers with low AOV: {growth_segment:,}")
        print("   💡 Recommendation: Implement upsell/cross-sell strategies")
        
    except Exception as e:
        print(f"❌ Could not generate insights: {e}")

def main():
    """Run complete validation suite"""
    # Import validation from the optimized script (must be in same dir)
    try:
        from customer_segmentation_simple import get_spark_session
    except ImportError:
        # Fallback if using a different filename pattern
        print("⚠️ Could not import get_spark_session from customer_segmentation_simple.")
        print("   Creating a default session...")
        # Define a fallback session builder or just exit - better to try/except
        # For now we'll assume the files are together.
        raise

    spark = get_spark_session()
    spark.sparkContext.setLogLevel("WARN")
    
    try:
        print("\n🚀 Starting Data Quality & Segmentation Validation")
        print(f"⏰ Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Pre-segmentation validation
        stats = validate_silver_tables(spark)
        analyze_customer_purchase_patterns(spark)
        
        # Post-segmentation validation
        segmentation_exists = validate_segmentation_results(spark)
        
        if segmentation_exists:
            generate_business_insights(spark)
        else:
            print("\n⏭️  Skipping segmentation validation (run segmentation first)")
        
        print("\n✅ Validation completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Validation failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        spark.stop()

if __name__ == "__main__":
    main()
