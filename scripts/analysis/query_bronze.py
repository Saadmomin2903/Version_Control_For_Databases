#!/usr/bin/env python3
"""
Quick Bronze Table Query Script
Run: python3 query_bronze.py
"""

import sys
import os
sys.path.append('/home/jovyan/scripts')

from pyspark.sql import functions as F
from utils.spark_utils import get_spark_session

def main():
    print("\n" + "="*70)
    print("BRONZE TABLE INTERACTIVE QUERY")
    print("="*70)
    
    # Initialize Spark
    spark = get_spark_session('BronzeQuery')
    
    # Load Bronze table
    df = spark.table('nessie.ecommerce.orders_bronze')
    
    # Basic info
    total = df.count()
    print(f"\n📊 Total Records: {total:,}")
    
    # Date range
    date_stats = df.agg(
        F.min('event_time').alias('min_date'),
        F.max('event_time').alias('max_date')
    ).collect()[0]
    print(f"📅 Date Range: {date_stats['min_date']} to {date_stats['max_date']}")
    
    # Monthly breakdown
    print("\n📈 Monthly Breakdown:")
    monthly = df.groupBy(
        F.year('event_time').alias('year'),
        F.month('event_time').alias('month')
    ).agg(
        F.count('*').alias('records'),
        F.countDistinct('user_id').alias('users'),
        F.countDistinct('product_id').alias('products'),
        F.sum('price').alias('revenue')
    ).orderBy('year', 'month')
    monthly.show(truncate=False)
    
    # Event types
    print("\n🎯 Event Type Distribution:")
    df.groupBy('event_type').count().orderBy(F.desc('count')).show()
    
    # Sample data
    print("\n📋 Sample Records:")
    df.show(10, truncate=False)
    
    # Category analysis
    print("\n🏷️ Top 10 Categories:")
    df.groupBy('category_code').count().orderBy(F.desc('count')).limit(10).show(truncate=False)
    
    # Brand analysis
    print("\n🏢 Top 10 Brands:")
    df.groupBy('brand').count().orderBy(F.desc('count')).limit(10).show(truncate=False)
    
    # Price statistics
    print("\n💰 Price Statistics:")
    price_stats = df.agg(
        F.min('price').alias('min_price'),
        F.avg('price').alias('avg_price'),
        F.max('price').alias('max_price'),
        F.sum('price').alias('total_revenue')
    ).collect()[0]
    
    print(f"  Min Price: ${price_stats['min_price']:.2f}")
    print(f"  Avg Price: ${price_stats['avg_price']:.2f}")
    print(f"  Max Price: ${price_stats['max_price']:.2f}")
    print(f"  Total Revenue: ${price_stats['total_revenue']:,.2f}")
    
    # Data quality
    print("\n✅ Data Quality Check:")
    for col in ['event_time', 'user_id', 'product_id', 'price']:
        null_count = df.filter(F.col(col).isNull()).count()
        null_pct = (null_count / total) * 100
        status = "✅" if null_pct < 1 else "⚠️"
        print(f"  {status} {col:20s}: {null_count:,} nulls ({null_pct:.2f}%)")
    
    print("\n" + "="*70)
    print("✅ Query Complete!")
    print("="*70 + "\n")
    
    spark.stop()

if __name__ == "__main__":
    main()
