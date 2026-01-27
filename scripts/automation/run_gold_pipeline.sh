#!/bin/bash
# Auto-Run Gold Layer Pipeline (Post-Silver)
# This script waits for Silver to complete, then runs all Gold layer steps sequentially

set -e  # Exit on any error

echo "🚀 Gold Layer Auto-Pipeline Starting..."
echo "========================================"
echo ""

# 1. Wait for Silver to complete
echo "⏳ Step 1: Waiting for Silver transformation to complete..."
while docker exec lakehouse-spark ps aux | grep -q "transform_orders_silver.py"; do
    echo "   Silver still processing... (checking again in 60s)"
    sleep 60
done
echo "✅ Silver transformation complete!"
echo ""

# 2. Verify Silver count
echo "🔍 Step 2: Verifying Silver table..."
docker exec lakehouse-spark python3 -c "
from pyspark.sql import SparkSession
import sys
sys.path.append('/home/jovyan/scripts')
from utils.spark_utils import get_spark_session

spark = get_spark_session('VerifySilver')
count = spark.table('nessie.ecommerce.\`orders_silver@silver\`').count()
print(f'✅ Silver verified: {count:,} records')
spark.stop()
"
echo ""

# 3. Merge Silver branch to main
echo "🔀 Step 3: Merging Silver branch to main..."
docker exec lakehouse-spark python3 /home/jovyan/scripts/silver/merge_silver.py
echo "✅ Silver merged to main"
echo ""

# 4. Gold - Customer Summary
echo "📊 Step 4: Building Gold Customer Summary..."
START_TIME=$(date +%s)
docker exec lakehouse-spark python3 /home/jovyan/scripts/gold/aggregate_customer_summary_gold.py
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))
echo "✅ Customer Summary complete (${DURATION}s)"
echo ""

# 5. Gold - Daily Summary
echo "📈 Step 5: Building Gold Daily Summary..."
START_TIME=$(date +%s)
docker exec lakehouse-spark python3 /home/jovyan/scripts/gold/build_gold_layer.py
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))
echo "✅ Daily Summary complete (${DURATION}s)"
echo ""

# 6. ML - Customer Segmentation
echo "🧠 Step 6: Running Customer Segmentation ML..."
START_TIME=$(date +%s)
docker exec lakehouse-spark python3 /home/jovyan/scripts/gold/customer_segmentation_simple.py
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))
echo "✅ Customer Segmentation complete (${DURATION}s)"
echo ""

# 7. ML - Product Recommendations
echo "🛍️ Step 7: Running Product Recommendations ML..."
START_TIME=$(date +%s)
docker exec lakehouse-spark python3 /home/jovyan/scripts/gold/product_recommendation_iceberg.py
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))
echo "✅ Product Recommendations complete (${DURATION}s)"
echo ""

# Final Verification
echo "🎯 Final Verification:"
echo "========================================"
docker exec lakehouse-spark python3 -c "
from pyspark.sql import SparkSession
import sys
sys.path.append('/home/jovyan/scripts')
from utils.spark_utils import get_spark_session

spark = get_spark_session('FinalCheck')

tables = [
    ('nessie.ecommerce.orders_bronze', 'Bronze Orders'),
    ('nessie.ecommerce.orders_silver', 'Silver Orders'),
    ('nessie.ecommerce.customer_summary_gold', 'Gold Customers'),
    ('nessie.ecommerce.daily_summary_gold', 'Gold Daily'),
    ('nessie.ecommerce.customer_segments', 'ML Segments'),
    ('nessie.ecommerce.product_recommendations', 'ML Recommendations')
]

for table, name in tables:
    try:
        count = spark.table(table).count()
        print(f'✅ {name:30s}: {count:,} records')
    except Exception as e:
        print(f'❌ {name:30s}: NOT FOUND ({e})')

spark.stop()
"

echo ""
echo "========================================"
echo "🎉 DAY 1 PIPELINE COMPLETE!"
echo "========================================"
echo ""
echo "Next Steps (Day 2):"
echo "  1. Deploy Apache Superset (BI Dashboards)"
echo "  2. Test SQL access via Spark Thrift Server"
echo "  3. Run end-to-end Airflow DAG"
echo "  4. Deploy OpenMetadata (Data Lineage)"
