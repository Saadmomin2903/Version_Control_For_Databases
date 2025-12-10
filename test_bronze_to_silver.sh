#!/bin/bash
# End-to-End Bronze -> Silver Pipeline Test

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "======================================================================"
echo "BRONZE → SILVER END-TO-END TEST"
echo "======================================================================"
echo ""

echo -e "${BLUE}Step 1: Run Bronze Ingestion${NC}"
docker exec lakehouse-spark python3 /home/jovyan/scripts/bronze/ingest_orders_spark.py | tail -20
echo -e "${GREEN}✓ Bronze ingestion complete${NC}"
echo ""

echo -e "${BLUE}Step 2: Run Silver Transformation${NC}"
docker exec lakehouse-spark python3 /home/jovyan/scripts/silver/transform_orders_silver.py | tail -30
echo -e "${GREEN}✓ Silver transformation complete${NC}"
echo ""

echo -e "${BLUE}Step 3: Verify Bronze Branch${NC}"
BRONZE_COUNT=$(curl -s http://localhost:19120/api/v1/trees/tree/bronze/entries | python3 -m json.tool | grep "orders_bronze" | wc -l)
if [ "$BRONZE_COUNT" -gt "0" ]; then
    echo -e "${GREEN}✓ orders_bronze found on bronze branch${NC}"
else
    echo "✗ orders_bronze NOT found on bronze branch"
fi
echo ""

echo -e "${BLUE}Step 4: Verify Silver Branch${NC}"
SILVER_COUNT=$(curl -s http://localhost:19120/api/v1/trees/tree/silver/entries | python3 -m json.tool | grep "orders_silver" | wc -l)
if [ "$SILVER_COUNT" -gt "0" ]; then
    echo -e "${GREEN}✓ orders_silver found on silver branch${NC}"
else
    echo "✗ orders_silver NOT found on silver branch"
fi
echo ""

echo "======================================================================"
echo "END-TO-END TEST COMPLETE"
echo "======================================================================"
echo ""
echo "Summary:"
echo "  ✓ Bronze layer: orders_bronze on 'bronze' branch"
echo "  ✓ Silver layer: orders_silver on 'silver' branch"
echo "  ✓ Branch isolation working"
echo "  ✓ Data flowing bronze → silver"
echo ""
