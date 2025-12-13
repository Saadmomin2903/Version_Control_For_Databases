"""
Gold Layer - Customer Summary Aggregation

Joins customers_silver and orders_silver to create business-ready customer metrics
Writes to main branch (Gold = Production)
"""

import os
import pyspark
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.window import Window

# Configuration
NESSIE_URI = os.getenv("NESSIE_URI", "http://nessie:19120/api/v1")
WAREHOUSE = os.getenv("WAREHOUSE", "s3a://lakehouse/warehouse")
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID", "admin")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "password123")
AWS_S3_ENDPOINT = os.getenv("AWS_S3_ENDPOINT", "http://minio:9000")

print("=" * 70)
print("GOLD LAYER - CUSTOMER SUMMARY AGGREGATION")
print("=" * 70)
print("")

# Spark configuration
conf = (
    pyspark.SparkConf()
        .setAppName('gold-customer-summary')
        .set('spark.jars.packages', 
             'org.apache.iceberg:iceberg-spark-runtime-3.3_2.12:1.3.1,'
             'org.projectnessie.nessie-integrations:nessie-spark-extensions-3.3_2.12:0.67.0,'
             'software.amazon.awssdk:bundle:2.17.178,'
             'software.amazon.awssdk:url-connection-client:2.17.178')
        .set('spark.sql.extensions', 
             'org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions,'
             'org.projectnessie.spark.extensions.NessieSparkSessionExtensions')
        .set('spark.sql.catalog.nessie', 'org.apache.iceberg.spark.SparkCatalog')
        .set('spark.sql.catalog.nessie.uri', NESSIE_URI)
        .set('spark.sql.catalog.nessie.ref', 'main')  # Write to main (Gold = production)
        .set('spark.sql.catalog.nessie.authentication.type', 'NONE')
        .set('spark.sql.catalog.nessie.catalog-impl', 'org.apache.iceberg.nessie.NessieCatalog')
        .set('spark.sql.catalog.nessie.warehouse', WAREHOUSE)
        .set('spark.sql.catalog.nessie.io-impl', 'org.apache.iceberg.aws.s3.S3FileIO')
        .set('spark.sql.catalog.nessie.s3.endpoint', AWS_S3_ENDPOINT)
        .set('spark.hadoop.fs.s3a.access.key', AWS_ACCESS_KEY)
        .set('spark.hadoop.fs.s3a.secret.key', AWS_SECRET_KEY)
        .set('spark.hadoop.fs.s3a.endpoint', AWS_S3_ENDPOINT)
        .set('spark.hadoop.fs.s3a.path.style.access', 'true')
        .set('spark.hadoop.fs.s3a.connection.ssl.enabled', 'false')
        .set('spark.hadoop.fs.s3a.impl', 'org.apache.hadoop.fs.s3a.S3AFileSystem')
)

spark = SparkSession.builder.config(conf=conf).getOrCreate()

print("📖 Step 1: Reading from Silver tables...")
print("-" * 70)

# Read customers from silver branch
customers_df = spark.sql("SELECT * FROM nessie.ecommerce.`customers_silver@silver`")
customers_count = customers_df.count()
print(f"✓ Loaded {customers_count} customers from silver")

# Read orders from silver branch  
orders_df = spark.sql("SELECT * FROM nessie.ecommerce.`orders_silver@silver`")
orders_count = orders_df.count()
print(f"✓ Loaded {orders_count} orders from silver")
print("")

print("🔧 Step 2: Calculating customer metrics...")
print("-" * 70)

# Filter only completed orders for metrics
completed_orders = orders_df.filter(F.col("status") == "completed")

# Aggregate order metrics per customer
customer_metrics = completed_orders.groupBy("customer_id").agg(
    F.count("order_id").alias("total_orders"),
    F.sum("total_amount").alias("total_revenue"),
    F.avg("total_amount").alias("avg_order_value"),
    F.min("order_date").alias("first_order_date"),
    F.max("order_date").alias("last_order_date")
)

# Calculate customer lifetime value (total revenue from completed orders)
customer_metrics = customer_metrics.withColumn(
    "customer_lifetime_value",
    F.col("total_revenue")
)

# Round numeric values for readability
customer_metrics = customer_metrics.withColumn(
    "total_revenue", F.round(F.col("total_revenue"), 2)
).withColumn(
    "avg_order_value", F.round(F.col("avg_order_value"), 2)
).withColumn(
    "customer_lifetime_value", F.round(F.col("customer_lifetime_value"), 2)
)

print(f"✓ Calculated metrics for {customer_metrics.count()} customers with orders")
print("")

print("🔗 Step 3: Joining with customer information...")
print("-" * 70)

# Join with customer details
customer_summary = customers_df.join(
    customer_metrics,
    on="customer_id",
    how="left"  # Keep all customers, even those without completed orders
)

# Fill nulls for customers with no completed orders
customer_summary = customer_summary.fillna({
    "total_orders": 0,
    "total_revenue": 0.0,
    "avg_order_value": 0.0,
    "customer_lifetime_value": 0.0
})

# Add customer segment based on lifetime value
customer_summary = customer_summary.withColumn(
    "customer_segment",
    F.when(F.col("customer_lifetime_value") >= 1000, "Premium")
     .when(F.col("customer_lifetime_value") >= 500, "Gold")
     .when(F.col("customer_lifetime_value") >= 100, "Silver")
     .when(F.col("customer_lifetime_value") > 0, "Bronze")
     .otherwise("No Orders")
)

# Add processing metadata
customer_summary = customer_summary.withColumn("aggregated_at", F.current_timestamp())

total_customers = customer_summary.count()
print(f"✓ Created summary for {total_customers} customers")
print("")

print("📊 Step 4: Summary Statistics...")
print("-" * 70)

# Show segment distribution
print("Customer Segments:")
customer_summary.groupBy("customer_segment").count().orderBy(
    F.desc("count")
).show()

# Show top customers
print("\nTop 5 Customers by Lifetime Value:")
customer_summary.select(
    "customer_id", "name", "total_orders", "total_revenue", "customer_lifetime_value", "customer_segment"
).orderBy(F.desc("customer_lifetime_value")).limit(5).show(truncate=False)

print("")

print("💾 Step 5: Writing to MAIN branch (Gold/Production)...")
print("-" * 70)

# Create temp view
customer_summary.createOrReplaceTempView("customer_summary_temp")

# Create namespace if needed
try:
    spark.sql("CREATE NAMESPACE IF NOT EXISTS nessie.ecommerce")
    print("✓ Namespace verified")
except:
    pass

# Write to main branch (Gold = production)
print(f"✓ Writing {total_customers} customer summaries to main branch...")
spark.sql("""
    CREATE OR REPLACE TABLE nessie.ecommerce.customer_summary
    USING iceberg
    AS SELECT * FROM customer_summary_temp
""")
print("✓ Table created on main branch")

# Verify the write
verify_count = spark.sql("SELECT COUNT(*) as cnt FROM nessie.ecommerce.customer_summary").collect()[0]['cnt']
print(f"✓ Verified: {verify_count} records in customer_summary")

# Calculate key business metrics
business_metrics = spark.sql("""
    SELECT 
        COUNT(*) as total_customers,
        SUM(total_orders) as total_orders,
        ROUND(SUM(total_revenue), 2) as total_revenue,
        ROUND(AVG(customer_lifetime_value), 2) as avg_customer_value,
        COUNT(CASE WHEN total_orders > 0 THEN 1 END) as active_customers,
        COUNT(CASE WHEN total_orders = 0 THEN 1 END) as inactive_customers
    FROM customer_summary_temp
""").collect()[0]

print("\n📈 Business Metrics:")
print(f"  Total Customers: {business_metrics['total_customers']}")
print(f"  Active Customers: {business_metrics['active_customers']}")
print(f"  Inactive Customers: {business_metrics['inactive_customers']}")
print(f"  Total Orders: {business_metrics['total_orders']}")
print(f"  Total Revenue: ${business_metrics['total_revenue']:,.2f}")
print(f"  Avg Customer Value: ${business_metrics['avg_customer_value']:,.2f}")

spark.stop()

print("")
print("=" * 70)
print("✅ GOLD LAYER - CUSTOMER SUMMARY COMPLETE!")
print("=" * 70)
print("")
print("Summary:")
print(f"  📥 Input:  {customers_count} customers + {orders_count} orders from silver")
print(f"  📤 Output: {verify_count} customer summaries on main branch")
print(f"  💰 Total Revenue: ${business_metrics['total_revenue']:,.2f}")
print(f"  📊 Customer Segments: Premium, Gold, Silver, Bronze, No Orders")
print(f"  🎯 Ready for: BI tools, dashboards, analytics")
print("=" * 70)
