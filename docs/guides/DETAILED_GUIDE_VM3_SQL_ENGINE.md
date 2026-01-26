# VM3 Setup Guide: SQL Query Engine (Spark Thrift Server)

This guide documents how to set up **Spark Thrift Server** on VM3. This service provides a JDBC/ODBC interface (port 10000) allowing any SQL client (DBeaver, Tableau, PowerBI) to query your Data Lakehouse.

It replaces Trino for this architecture due to better compatibility with the current Nessie/Iceberg version stack.

---

## 1. Prerequisites (Already Completed)

- **VM3 Created**: `lakehouse-trino-vm3` (repurposed)
- **Public IP**: `161.118.185.218`
- **Private IP**: `10.0.0.247`
- **Docker Installed**: Version 28.x (via Snap)

---

## 2. Quick Setup Commands (Copy-Paste)

If you need to redeploy or restart the service, follow these steps on VM3:

### Step 2.1: Connect to VM3
```bash
ssh -i key3/oracle-vm3.key ubuntu@161.118.185.218
```

### Step 2.2: Create Deployment Files

**1. Create `docker-compose-vm3-thrift.yml`**
```yaml
version: "3"

services:
  spark-thrift:
    image: alexmerced/spark33-notebook
    container_name: lakehouse-thrift
    ports:
      - "10000:10000"  # JDBC/ODBC Interface
      - "4040:4040"    # Spark Web UI
    environment:
      - SPARK_MODE=master
    volumes:
      - ./start-thrift.sh:/opt/spark/start-thrift.sh
    entrypoint: /bin/bash /opt/spark/start-thrift.sh
    restart: always
```

**2. Create `start-thrift.sh` (The Boot Script)**
```bash
#!/bin/bash
echo "Starting Spark Thrift Server with Nessie..."

# Launch Thrift Server with Nessie & S3 Packages
/opt/spark/sbin/start-thriftserver.sh \
  --master local[*] \
  --packages "org.projectnessie.nessie-integrations:nessie-spark-extensions-3.3_2.12:0.67.0,org.apache.iceberg:iceberg-spark-runtime-3.3_2.12:1.3.1,org.apache.hadoop:hadoop-aws:3.3.2" \
  --conf spark.sql.catalog.nessie=org.apache.iceberg.spark.SparkCatalog \
  --conf spark.sql.catalog.nessie.catalog-impl=org.apache.iceberg.nessie.NessieCatalog \
  --conf spark.sql.catalog.nessie.uri=http://10.0.0.148:19120/api/v1 \
  --conf spark.sql.catalog.nessie.ref=main \
  --conf spark.sql.catalog.nessie.authentication.type=NONE \
  --conf spark.sql.catalog.nessie.warehouse=s3a://lakehouse-prod/warehouse \
  --conf spark.hadoop.fs.s3a.access.key=962c9f862226831e4edea90cfcfafb8a8dffcd51 \
  --conf spark.hadoop.fs.s3a.secret.key=sd2rGU918DTmn35E4xJ8EV7BX2XUt7DkqC8v6WDNDUw= \
  --conf spark.hadoop.fs.s3a.endpoint=https://bmcfe6z38foz.compat.objectstorage.ap-mumbai-1.oraclecloud.com \
  --conf spark.hadoop.fs.s3a.path.style.access=true \
  --conf spark.hadoop.fs.s3a.impl=org.apache.hadoop.fs.s3a.S3AFileSystem \
  --conf spark.sql.extensions=org.projectnessie.spark.extensions.NessieSparkSessionExtensions \
  --hiveconf hive.server2.transport.mode=binary

# Keep container running by tailing logs
sleep 5
tail -f /opt/spark/logs/*.out
```

**3. Make Script Executable**
```bash
chmod +x start-thrift.sh
```

---

## 3. Launching the Service

```bash
docker compose -f docker-compose-vm3-thrift.yml up -d
```

**Verify Startup:**
```bash
docker logs -f lakehouse-thrift
```
*Wait until you see: `HiveThriftServer2: HiveThriftServer2 started`*

---

## 4. Testing Connectivity

You can test the SQL engine directly from inside the container using `beeline` (a CLI SQL client):

**1. List Schemas**
```bash
docker exec lakehouse-thrift /opt/spark/bin/beeline -u jdbc:hive2://localhost:10000 -n admin -p admin -e "SHOW SCHEMAS IN nessie"
```
*Output should show `ecommerce`, `demo`, etc.*

**2. Query Data**
```bash
docker exec lakehouse-thrift /opt/spark/bin/beeline -u jdbc:hive2://localhost:10000 -n admin -p admin -e "SELECT count(*) FROM nessie.ecommerce.orders_silver"
```
*Output should show the row count (e.g. 3,138,325).*

---

## 5. Connecting External Tools (DBeaver/Tableau)

From your laptop, you can now connect to VM3:

- **Type**: Apache Hive or Spark SQL
- **Host**: `161.118.185.218`
- **Port**: `10000`
- **Database**: `default`
- **Username**: `admin` (or any string)
- **Password**: `admin` (or any string)
- **URL**: `jdbc:hive2://161.118.185.218:10000`

Test the connection and run SQL:
```sql
SELECT * FROM nessie.ecommerce.orders_silver LIMIT 10;
```
