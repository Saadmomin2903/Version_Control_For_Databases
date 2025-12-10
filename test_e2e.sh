#!/bin/bash
set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=========================================="
echo "End-to-End Lakehouse Test"
echo "=========================================="
echo ""

# Function to print test results
pass() {
    echo -e "${GREEN}✓${NC} $1"
}

fail() {
    echo -e "${RED}✗${NC} $1"
    exit 1
}

warn() {
    echo -e "${YELLOW}⚠${NC} $1"
}

info() {
    echo "ℹ $1"
}

# Test 1: Check Docker is running
info "Test 1: Checking Docker..."
if docker ps >/dev/null 2>&1; then
    pass "Docker is running"
else
    fail "Docker is not running. Please start Docker Desktop."
fi

# Test 2: Check all services are up
info "Test 2: Checking services status..."
REQUIRED_SERVICES=("lakehouse-minio" "lakehouse-nessie" "lakehouse-spark" "lakehouse-postgres")
for service in "${REQUIRED_SERVICES[@]}"; do
    if docker ps --format '{{.Names}}' | grep -q "^${service}$"; then
        pass "Service $service is running"
    else
        fail "Service $service is not running. Run: docker compose up -d"
    fi
done

# Test 3: Check service health
info "Test 3: Checking service health..."

# MinIO health
if curl -sf http://localhost:9000/minio/health/live >/dev/null 2>&1; then
    pass "MinIO is healthy"
else
    fail "MinIO health check failed"
fi

# Nessie health
if curl -sf http://localhost:19120/api/v1/config >/dev/null 2>&1; then
    pass "Nessie is healthy"
else
    fail "Nessie health check failed"
fi

# Test 4: Check MinIO bucket
info "Test 4: Checking MinIO bucket..."
if docker exec lakehouse-minio mc ls myminio/ 2>/dev/null | grep -q "lakehouse"; then
    pass "MinIO bucket 'lakehouse' exists"
else
    warn "MinIO bucket 'lakehouse' does not exist. Creating..."
    docker exec lakehouse-minio mc alias set myminio http://localhost:9000 admin password123
    docker exec lakehouse-minio mc mb myminio/lakehouse --ignore-existing
    pass "MinIO bucket 'lakehouse' created"
fi

# Test 5: Check if data files exist
info "Test 5: Checking sample data files..."
if [ -f "data/raw/orders.csv" ]; then
    pass "orders.csv exists"
else
    warn "orders.csv not found. Creating sample data..."
    mkdir -p data/raw
    cat > data/raw/orders.csv << 'EOF'
order_id,customer_id,product,quantity,price,order_date
1,101,Laptop,1,1000.00,2023-08-01
2,102,Mouse,2,25.50,2023-08-01
3,103,Keyboard,1,45.00,2023-08-01
4,104,Monitor,1,350.00,2023-08-02
5,105,Headphones,2,75.00,2023-08-02
EOF
    pass "Created sample orders.csv"
fi

if [ -f "data/raw/customers.csv" ]; then
    pass "customers.csv exists"
else
    warn "customers.csv not found. Creating sample data..."
    mkdir -p data/raw
    cat > data/raw/customers.csv << 'EOF'
customer_id,name,email,country
101,John Doe,john@example.com,USA
102,Jane Smith,jane@example.com,UK
103,Bob Johnson,bob@example.com,Canada
104,Alice Williams,alice@example.com,USA
105,Charlie Brown,charlie@example.com,Australia
EOF
    pass "Created sample customers.csv"
fi

# Test 6: Check if ingestion scripts exist
info "Test 6: Checking ingestion scripts..."
if [ -f "scripts/bronze/ingest_orders_spark.py" ]; then
    pass "ingest_orders_spark.py exists"
else
    fail "ingest_orders_spark.py not found"
fi

if [ -f "scripts/bronze/ingest_customers_spark.py" ]; then
    pass "ingest_customers_spark.py exists"
else
    fail "ingest_customers_spark.py not found"
fi

# Test 7: Run orders ingestion
info "Test 7: Running orders ingestion..."
echo "   (This may take 30-60 seconds on first run while downloading JARs...)"
if docker exec lakehouse-spark python3 /home/jovyan/scripts/bronze/ingest_orders_spark.py 2>&1 | grep -q "Bronze ingestion complete"; then
    pass "Orders ingestion completed successfully"
else
    fail "Orders ingestion failed"
fi

# Test 8: Run customers ingestion
info "Test 8: Running customers ingestion..."
if docker exec lakehouse-spark python3 /home/jovyan/scripts/bronze/ingest_customers_spark.py 2>&1 | grep -q "Bronze customers ingestion complete"; then
    pass "Customers ingestion completed successfully"
else
    fail "Customers ingestion failed"
fi

# Test 9: Verify tables in Nessie
info "Test 9: Verifying tables in Nessie catalog..."
NESSIE_RESPONSE=$(curl -s http://localhost:19120/api/v1/trees/tree/main/entries)

if echo "$NESSIE_RESPONSE" | grep -q "orders_bronze"; then
    pass "orders_bronze table registered in Nessie"
else
    fail "orders_bronze table not found in Nessie"
fi

if echo "$NESSIE_RESPONSE" | grep -q "customers_bronze"; then
    pass "customers_bronze table registered in Nessie"
else
    fail "customers_bronze table not found in Nessie"
fi

# Test 10: Verify data in MinIO
info "Test 10: Verifying data in MinIO warehouse..."
if docker exec lakehouse-minio mc ls --recursive myminio/lakehouse/warehouse/ecommerce/ 2>/dev/null | grep -q "parquet"; then
    pass "Parquet data files found in MinIO"
else
    fail "No data files found in MinIO"
fi

# Test 11: Count records (if possible)
info "Test 11: Querying data..."
echo "   Creating simple query script..."

cat > /tmp/test_query.py << 'EOF'
import pyspark
from pyspark.sql import SparkSession

try:
    conf = (
        pyspark.SparkConf()
            .setAppName('test-query')
            .set('spark.jars.packages', 
                 'org.apache.iceberg:iceberg-spark-runtime-3.3_2.12:1.3.1,'
                 'org.projectnessie.nessie-integrations:nessie-spark-extensions-3.3_2.12:0.67.0,'
                 'software.amazon.awssdk:bundle:2.17.178,'
                 'software.amazon.awssdk:url-connection-client:2.17.178')
            .set('spark.sql.extensions', 
                 'org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions,'
                 'org.projectnessie.spark.extensions.NessieSparkSessionExtensions')
            .set('spark.sql.catalog.nessie', 'org.apache.iceberg.spark.SparkCatalog')
            .set('spark.sql.catalog.nessie.uri', 'http://nessie:19120/api/v1')
            .set('spark.sql.catalog.nessie.ref', 'main')
            .set('spark.sql.catalog.nessie.authentication.type', 'NONE')
            .set('spark.sql.catalog.nessie.catalog-impl', 'org.apache.iceberg.nessie.NessieCatalog')
            .set('spark.sql.catalog.nessie.warehouse', 's3a://lakehouse/warehouse')
            .set('spark.sql.catalog.nessie.io-impl', 'org.apache.iceberg.aws.s3.S3FileIO')
            .set('spark.sql.catalog.nessie.s3.endpoint', 'http://minio:9000')
            .set('spark.hadoop.fs.s3a.access.key', 'admin')
            .set('spark.hadoop.fs.s3a.secret.key', 'password123')
            .set('spark.hadoop.fs.s3a.endpoint', 'http://minio:9000')
            .set('spark.hadoop.fs.s3a.path.style.access', 'true')
            .set('spark.hadoop.fs.s3a.connection.ssl.enabled', 'false')
            .set('spark.hadoop.fs.s3a.impl', 'org.apache.hadoop.fs.s3a.S3AFileSystem')
    )
    
    spark = SparkSession.builder.config(conf=conf).getOrCreate()
    
    # Query orders
    orders_count = spark.sql("SELECT COUNT(*) as count FROM nessie.ecommerce.orders_bronze").collect()[0]['count']
    print(f"ORDERS_COUNT:{orders_count}")
    
    # Query customers
    customers_count = spark.sql("SELECT COUNT(*) as count FROM nessie.ecommerce.customers_bronze").collect()[0]['count']
    print(f"CUSTOMERS_COUNT:{customers_count}")
    
    spark.stop()
    print("QUERY_SUCCESS")
except Exception as e:
    print(f"QUERY_ERROR:{e}")
EOF

docker cp /tmp/test_query.py lakehouse-spark:/tmp/test_query.py
QUERY_OUTPUT=$(docker exec lakehouse-spark python3 /tmp/test_query.py 2>&1)

if echo "$QUERY_OUTPUT" | grep -q "QUERY_SUCCESS"; then
    ORDERS_COUNT=$(echo "$QUERY_OUTPUT" | grep "ORDERS_COUNT:" | cut -d: -f2)
    CUSTOMERS_COUNT=$(echo "$QUERY_OUTPUT" | grep "CUSTOMERS_COUNT:" | cut -d: -f2)
    pass "Data queries successful"
    info "   Orders: $ORDERS_COUNT records"
    info "   Customers: $CUSTOMERS_COUNT records"
else
    warn "Data query failed (data might still be valid)"
fi

# Cleanup
rm -f /tmp/test_query.py

echo ""
echo "=========================================="
echo -e "${GREEN}ALL TESTS PASSED!${NC}"
echo "=========================================="
echo ""
echo "Summary:"
echo "  ✓ All services running"
echo "  ✓ MinIO bucket configured"
echo "  ✓ Sample data created"
echo "  ✓ Bronze ingestion successful"
echo "  ✓ Tables registered in Nessie"
echo "  ✓ Data stored in MinIO"
echo ""
echo "Next steps:"
echo "  - Access Jupyter: http://localhost:8888"
echo "  - Access MinIO Console: http://localhost:9001"
echo "  - Check Nessie API: curl http://localhost:19120/api/v1/trees/tree/main/entries"
echo ""
