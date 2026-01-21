# Final Execution Guide - Production Deployment

**Direct Path to Production | No Local Testing | Firebolt 412M Records**

---

## ⚡ Quick Start

**Timeline**: 2-3 days  
**Assumes**: Local testing already done  
**Goal**: Production deployment with Firebolt dataset

---

## 📋 Pre-Deployment Checklist

```yaml
✓ You have Oracle Cloud account (free tier)
✓ You have credit card for verification (no charges)
✓ You have 50+ GB free disk space
✓ You have stable internet connection
✓ You have 2-3 days to complete
```

---

## Day 1: Cloud Setup & Data Acquisition (4-5 hours)

### Part 1A: Oracle Cloud Account (30 min)

```bash
# 1. Sign up
open https://www.oracle.com/cloud/free/

# 2. Fill form:
#    - Cloud Account Name: lakehouse-prod
#    - Home Region: US East (Ashburn)
#    - Provide credit card (verification only, no charge)

# 3. Verify email and activate account

# 4. Login to Oracle Cloud Console
open https://cloud.oracle.com/
```

### Part 1B: Create VCN (15 min)

```bash
# Oracle Console: ☰ → Networking → Virtual Cloud Networks → Start VCN Wizard

# Settings:
VCN Name: lakehouse-vcn
VCN CIDR: 10.0.0.0/16
Public Subnet CIDR: 10.0.0.0/24

# Click "Next" → "Create"
```

### Part 1C: Add Security Rules (10 min)

```bash
# Click VCN → Default Security List → Add Ingress Rules

# Add these rules (one by one):
Rule 1: Port 22 (SSH), Source: 0.0.0.0/0
Rule 2: Port 8080 (Airflow), Source: 0.0.0.0/0
Rule 3: Port 19120 (Nessie), Source: 0.0.0.0/0
Rule 4: Port 8888 (Jupyter), Source: 0.0.0.0/0
Rule 5: Port 8081 (Spark), Source: 0.0.0.0/0
```

### Part 1D: Create VM1 - Airflow (20 min)

```bash
# Oracle Console: ☰ → Compute → Instances → Create Instance

Name: airflow-nessie
Image: Ubuntu 22.04 ARM64
Shape: VM.Standard.A1.Flex
  OCPU: 2
  Memory: 12 GB
VCN: lakehouse-vcn
Public IP: Yes
SSH Keys: Generate keypair
  [Download and save as: ~/.ssh/oracle-vm1.key]

# Click "Create"
# Note down Public IP: [VM1-PUBLIC-IP]
```

### Part 1E: Create VM2 - Spark (20 min)

```bash
# Repeat above with:
Name: spark-cluster
  [Download and save as: ~/.ssh/oracle-vm2.key]

# Note down Public IP: [VM2-PUBLIC-IP]
```

### Part 1F: Create Object Storage (10 min)

```bash
# Oracle Console: ☰ → Storage → Buckets → Create Bucket

Bucket Name: lakehouse-prod
Tier: Standard
Versioning: Enabled

# Click "Create"
```

### Part 1G: Generate S3 Keys (10 min)

```bash
# Click Profile Icon → User Settings → Customer Secret Keys → Generate

Name: lakehouse-s3-access

# ⚠️ COPY IMMEDIATELY (shown only once):
Access Key: [COPY]
Secret Key: [COPY]

# Save to file:
cat > ~/oracle-credentials.txt << EOF
ORACLE_ACCESS_KEY=[paste access key]
ORACLE_SECRET_KEY=[paste secret key]
ORACLE_NAMESPACE=[shown in bucket details]
ORACLE_REGION=us-ashburn-1
EOF

chmod 600 ~/oracle-credentials.txt
```

### Part 1H: Supabase Setup (15 min)

```bash
# 1. Sign up
open https://supabase.com/

# 2. Create project
Project Name: nessie-metadata
Password: [Generate strong password - SAVE IT!]
Region: East US

# 3. Get connection details (Settings → Database)
cat > ~/supabase-credentials.txt << EOF
SUPABASE_HOST=db.xxxxx.supabase.co
SUPABASE_PASSWORD=[your password]
SUPABASE_CONNECTION=postgresql://postgres:[password]@db.xxxxx.supabase.co:5432/postgres?sslmode=require
EOF

chmod 600 ~/supabase-credentials.txt
```

### Part 1I: Download Firebolt Dataset (2-3 hours)

```bash
# Create directory
cd ~/Documents/Version_Control_For_Databases
mkdir -p data/firebolt-raw
cd data/firebolt-raw

# Install AWS CLI
brew install awscli  # macOS
# or
sudo apt install awscli  # Linux

# Download all files (no credentials needed)
echo "Downloading transactions (~40 GB)..."
aws s3 cp s3://firebolt-publishing-public/samples/e_commerce/transactions.csv.gz . --no-sign-request

echo "Downloading users (~500 MB)..."
aws s3 cp s3://firebolt-publishing-public/samples/e_commerce/users.csv.gz . --no-sign-request

echo "Downloading products (~100 MB)..."
aws s3 cp s3://firebolt-publishing-public/samples/e_commerce/products.csv.gz . --no-sign-request

echo "Downloading sessions (~8 GB)..."
aws s3 cp s3://firebolt-publishing-public/samples/e_commerce/sessions.csv.gz . --no-sign-request

# Decompress (takes time!)
echo "Decompressing files..."
gunzip transactions.csv.gz &
gunzip users.csv.gz &
gunzip products.csv.gz &
gunzip sessions.csv.gz &
wait

echo "✓ Download complete!"
ls -lh
```

**✅ Day 1 Complete!** Cloud infrastructure ready, dataset downloaded

---

## Day 2: VM Configuration & Data Upload (4-6 hours)

### Part 2A: Configure VM1 (1 hour)

```bash
# SSH into VM1
chmod 600 ~/.ssh/oracle-vm1.key
ssh -i ~/.ssh/oracle-vm1.key ubuntu@[VM1-PUBLIC-IP]

# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
sudo apt install -y docker.io docker-compose-plugin git curl
sudo usermod -aG docker ubuntu
exit

# Re-login to apply group
ssh -i ~/.ssh/oracle-vm1.key ubuntu@[VM1-PUBLIC-IP]

# Clone your repo
cd /home/ubuntu
git clone https://github.com/[youruser]/lakehouse.git
cd lakehouse

# Create structure
mkdir -p airflow/{dags,logs,plugins,config}
mkdir -p scripts/{bronze,silver,gold,utils}
chmod -R 755 airflow scripts

# Generate Fernet key
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" > /tmp/fernet.key

# Create environment file
cat > .env.prod << 'ENVEOF'
# Supabase
SUPABASE_HOST=db.xxxxx.supabase.co
SUPABASE_PASSWORD=[paste your password]
SUPABASE_CONNECTION=postgresql://postgres:[password]@db.xxxxx.supabase.co:5432/postgres?sslmode=require

# Airflow
AIRFLOW_UID=50000
AIRFLOW_FERNET_KEY=[paste from /tmp/fernet.key]

# Oracle
ORACLE_ACCESS_KEY=[from oracle-credentials.txt]
ORACLE_SECRET_KEY=[from oracle-credentials.txt]
ORACLE_NAMESPACE=[your namespace]
ORACLE_REGION=us-ashburn-1
ORACLE_ENDPOINT=https://objectstorage.us-ashburn-1.oraclecloud.com

# VM2 Private IP (update after VM2 setup)
VM2_PRIVATE_IP=10.0.0.x
ENVEOF

chmod 600 .env.prod
```

**Create Docker Compose**:

```bash
cat > docker-compose-prod.yml << 'DOCKEREOF'
version: '3.8'

x-airflow-common:
  &airflow-common
  image: apache/airflow:2.8.1-python3.11
  environment: &airflow-common-env
    AIRFLOW__CORE__EXECUTOR: LocalExecutor
    AIRFLOW__DATABASE__SQL_ALCHEMY_CONN: ${SUPABASE_CONNECTION}
    AIRFLOW__CORE__FERNET_KEY: ${AIRFLOW_FERNET_KEY}
    AIRFLOW__CORE__DAGS_ARE_PAUSED_AT_CREATION: 'true'
    AIRFLOW__CORE__LOAD_EXAMPLES: 'false'
    AIRFLOW__API__AUTH_BACKENDS: 'airflow.api.auth.backend.basic_auth'
  volumes:
    - ./airflow/dags:/opt/airflow/dags
    - ./airflow/logs:/opt/airflow/logs
    - ./scripts:/opt/airflow/scripts
  user: "50000:0"
  depends_on:
    nessie:
      condition: service_healthy

services:
  nessie:
    image: projectnessie/nessie:0.67.0
    container_name: nessie
    ports:
      - "19120:19120"
    environment:
      - NESSIE_VERSION_STORE_TYPE=JDBC
      - QUARKUS_DATASOURCE_JDBC_URL=${SUPABASE_CONNECTION}
      - QUARKUS_DATASOURCE_USERNAME=postgres
      - QUARKUS_DATASOURCE_PASSWORD=${SUPABASE_PASSWORD}
    restart: always
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:19120/api/v1/config"]
      interval: 30s
      timeout: 10s
      retries: 5
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  airflow-webserver:
    <<: *airflow-common
    container_name: airflow-webserver
    command: webserver
    ports:
      - "8080:8080"
    healthcheck:
      test: ["CMD", "curl", "--fail", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 5
    restart: always

  airflow-scheduler:
    <<: *airflow-common
    container_name: airflow-scheduler
    command: scheduler
    restart: always

  airflow-init:
    <<: *airflow-common
    container_name: airflow-init
    entrypoint: /bin/bash
    command:
      - -c
      - |
        mkdir -p /sources/{logs,dags,plugins,config}
        chown -R "50000:0" /sources/{logs,dags,plugins,config}
        exec /entrypoint airflow db init
        airflow users create --username admin --password admin123 --firstname Admin --lastname User --role Admin --email admin@lakehouse.local
    user: "0:0"
    volumes:
      - ./airflow:/sources
DOCKEREOF

# Initialize and start
source .env.prod
docker compose -f docker-compose-prod.yml up airflow-init
docker compose -f docker-compose-prod.yml up -d

# Verify
docker ps
# Should show: nessie, airflow-webserver, airflow-scheduler (all Up/healthy)

# Test Nessie
curl http://localhost:19120/api/v1/config
```

### Part 2B: Configure VM2 (1 hour)

```bash
# SSH into VM2
chmod 600 ~/.ssh/oracle-vm2.key
ssh -i ~/.ssh/oracle-vm2.key ubuntu@[VM2-PUBLIC-IP]

# Update
sudo apt update && sudo apt upgrade -y
sudo apt install -y docker.io git
sudo usermod -aG docker ubuntu
exit

# Re-login
ssh -i ~/.ssh/oracle-vm2.key ubuntu@[VM2-PUBLIC-IP]

# Clone repo
cd /home/ubuntu
git clone https://github.com/[youruser]/lakehouse.git
cd lakehouse
mkdir -p scripts/{bronze,silver,gold,utils} data

# Get VM1 private IP for .env
# (Run on VM1: hostname -I | awk '{print $1}')

# Create environment
cat > .env.spark << 'SPARKENV'
ORACLE_ACCESS_KEY=[your access key]
ORACLE_SECRET_KEY=[your secret key]
ORACLE_NAMESPACE=[your namespace]
ORACLE_REGION=us-ashburn-1
ORACLE_ENDPOINT=https://objectstorage.us-ashburn-1.oraclecloud.com
NESSIE_URI=http://[VM1-PRIVATE-IP]:19120/api/v1
WAREHOUSE=oci://[namespace]/lakehouse-prod/warehouse
SPARK_DRIVER_MEMORY=4g
SPARK_EXECUTOR_MEMORY=8g
SPARKENV

chmod 600 .env.spark
```

**Create Spark Docker Compose**:

```bash
cat > docker-compose-spark.yml << 'SPARKDOCKER'
version: '3.8'

services:
  spark-master:
    image: alexmerced/spark33-notebook
    container_name: spark-master
    ports:
      - "8888:8888"
      - "7077:7077"
      - "8081:8080"
    environment:
      - AWS_ACCESS_KEY_ID=${ORACLE_ACCESS_KEY}
      - AWS_SECRET_ACCESS_KEY=${ORACLE_SECRET_KEY}
      - AWS_S3_ENDPOINT=${ORACLE_ENDPOINT}
      - AWS_REGION=${ORACLE_REGION}
      - NESSIE_URI=${NESSIE_URI}
      - WAREHOUSE=${WAREHOUSE}
      - SPARK_DRIVER_MEMORY=${SPARK_DRIVER_MEMORY}
    volumes:
      - ./scripts:/home/jovyan/scripts
      - ./data:/home/jovyan/data
    restart: always

  spark-worker:
    image: alexmerced/spark33-notebook
    container_name: spark-worker
    environment:
      - SPARK_MODE=worker
      - SPARK_MASTER_URL=spark://spark-master:7077
      - SPARK_WORKER_CORES=2
      - SPARK_WORKER_MEMORY=10G
    depends_on:
      - spark-master
    restart: always
SPARKDOCKER

# Start Spark
source .env.spark
docker compose -f docker-compose-spark.yml up -d

# Verify
docker ps
docker logs spark-master | grep "Successfully started"
```

### Part 2C: Upload Data to Oracle (2-4 hours)

```bash
# On your LOCAL machine

# Configure AWS CLI for Oracle
aws configure set aws_access_key_id [YOUR_ORACLE_ACCESS_KEY]
aws configure set aws_secret_access_key [YOUR_ORACLE_SECRET_KEY]

# Strategy: Upload month-by-month
cd ~/Documents/Version_Control_For_Databases/data/firebolt-raw

# First, split transactions by month
python3 << 'SPLITPY'
import pandas as pd
from datetime import datetime

print("Splitting transactions by month...")
chunk_size = 10_000_000  # Process 10M rows at a time

for chunk in pd.read_csv('transactions.csv', chunksize=chunk_size, 
                         parse_dates=['order_date']):
    for month in chunk['order_date'].dt.to_period('M').unique():
        month_data = chunk[chunk['order_date'].dt.to_period('M') == month]
        filename = f'transactions_{month}.csv'
        
        # Append mode for chunks
        mode = 'a' if os.path.exists(filename) else 'w'
        header = not os.path.exists(filename)
        
        month_data.to_csv(filename, mode=mode, index=False, header=header)
        print(f"Added {len(month_data):,} records to {filename}")

print("✓ Split complete!")
SPLITPY

# Upload monthly files
for file in transactions_2019-*.csv transactions_2020-*.csv; do
    echo "Uploading $file..."
    aws s3 cp $file s3://lakehouse-prod/raw/firebolt/ \
        --endpoint-url https://objectstorage.us-ashburn-1.oraclecloud.com
done

# Upload other files
aws s3 cp users.csv s3://lakehouse-prod/raw/firebolt/ \
    --endpoint-url https://objectstorage.us-ashburn-1.oraclecloud.com
aws s3 cp products.csv s3://lakehouse-prod/raw/firebolt/ \
    --endpoint-url https://objectstorage.us-ashburn-1.oraclecloud.com
aws s3 cp sessions.csv s3://lakehouse-prod/raw/firebolt/ \
    --endpoint-url https://objectstorage.us-ashburn-1.oraclecloud.com

echo "✓ Upload complete!"
```

**✅ Day 2 Complete!** VMs configured, data uploaded

---

## Day 3: Pipeline Execution & Production (4-6 hours)

### Part 3A: Create Processing Scripts (1 hour)

**On VM2**, create the Firebolt ingestion scripts:

```bash
ssh -i ~/.ssh/oracle-vm2.key ubuntu@[VM2-PUBLIC-IP]
cd /home/ubuntu/lakehouse/scripts/bronze

# Upload your existing scripts but update for Firebolt schema:
# Copy scripts from your local repo to VM2
```

**From your LOCAL machine**:

```bash
# Upload all updated scripts
scp -i ~/.ssh/oracle-vm2.key \
    scripts/bronze/*.py \
    scripts/silver/*.py \
    scripts/gold/*.py \
    scripts/utils/*.py \
    ubuntu@[VM2-PUBLIC-IP]:/home/ubuntu/lakehouse/scripts/

# The key change: Update paths in scripts to use Oracle Object Storage
# ssh to VM2 and run:
ssh -i ~/.ssh/oracle-vm2.key ubuntu@[VM2-PUBLIC-IP]

cd /home/ubuntu/lakehouse/scripts

# Update all scripts to use Oracle paths
find . -name "*.py" -exec sed -i \
    's|s3a://lakehouse|oci://lakehouse-prod|g' {} +

find . -name "*.py" -exec sed -i \
    "s|'spark.hadoop.fs.s3a.connection.ssl.enabled', 'false'|'spark.hadoop.fs.s3a.connection.ssl.enabled', 'true'|g" {} +
```

### Part 3B: Run Pipeline Month-by-Month (4-5 hours)

```bash
# On VM2:

# Process each month
for month in 2019-10 2019-11 2019-12 2020-01 2020-02 2020-03 2020-04; do
    echo "========================================="
    echo "Processing $month"
    echo "========================================="
    
    # Bronze layer
    echo "1. Bronze ingestion..."
    docker exec spark-master python3 /home/jovyan/scripts/bronze/ingest_transactions.py --month=$month
    
    # Silver layer
    echo "2. Silver transformation..."
    docker exec spark-master python3 /home/jovyan/scripts/silver/transform_transactions.py --month=$month
    
    # Delete source CSV to free space
    echo "3. Cleanup source..."
    aws s3 rm s3://lakehouse-prod/raw/firebolt/transactions_${month}.csv \
        --endpoint-url https://objectstorage.us-ashburn-1.oraclecloud.com
    
    echo "✓ $month complete!"
    echo ""
done

# Process users (once)
echo "Processing users..."
docker exec spark-master python3 /home/jovyan/scripts/bronze/ingest_users.py
docker exec spark-master python3 /home/jovyan/scripts/silver/transform_users.py

# Process products (once)
echo "Processing products..."
docker exec spark-master python3 /home/jovyan/scripts/bronze/ingest_products.py

# Gold layer aggregation
echo "Gold aggregation..."
docker exec spark-master python3 /home/jovyan/scripts/gold/aggregate_customer_summary_gold.py

echo "✅ ALL PROCESSING COMPLETE!"
```

### Part 3C: Promote to Production

```bash
# On VM1:
ssh -i ~/.ssh/oracle-vm1.key ubuntu@[VM1-PUBLIC-IP]
cd /home/ubuntu/lakehouse

echo "yes" | python3 scripts/utils/promote_to_production.py

# Verify production
curl -s http://localhost:19120/api/v1/trees/tree/main/entries | \
    python3 -c "import json, sys; print('Production tables:', [e['name']['elements'] for e in json.load(sys.stdin)['entries']])"
```

**✅ Day 3 Complete!** Pipeline running, production deployed!

---

## Final Verification

### Check All Components

```bash
# 1. Nessie API
curl http://[VM1-PUBLIC-IP]:19120/api/v1/config
# Should return JSON

# 2. Airflow
open http://[VM1-PUBLIC-IP]:8080
# Login: admin / admin123

# 3. Spark UI
open http://[VM2-PUBLIC-IP]:8081

# 4. Jupyter
open http://[VM2-PUBLIC-IP]:8888

# 5. Verify data
ssh -i ~/.ssh/oracle-vm2.key ubuntu@[VM2-PUBLIC-IP]
docker exec -it spark-master pyspark

# In PySpark:
>>> spark.sql("SELECT COUNT(*) FROM nessie.ecommerce.orders_bronze").show()
# Should show 412,000,000

>>> spark.sql("SELECT year_month, COUNT(*) FROM nessie.ecommerce.orders_bronze GROUP BY year_month").show()
# Should show 7 months
```

---

## 📊 Expected Results

```yaml
Data Processed:
  Transactions: 412,000,000 records
  Users: 2,500,000 records
  Products: 125,000 records
  
Storage Used:
  Bronze: ~7 GB
  Silver: ~6 GB
  Gold: ~500 MB
  Total: ~13.5 GB (within 20 GB limit ✅)

Processing Time:
  Per month: ~40-50 minutes
  Total (7 months): ~5-6 hours

Cost:
  Oracle Cloud: $0/month
  Supabase: $0/month
  Total: $0/month ✅
```

---

## 🎯 Project Submission Checklist

```yaml
Infrastructure:
  ✓ Oracle Cloud VMs running
  ✓ Supabase PostgreSQL connected
  ✓ Nessie catalog operational
  ✓ Airflow orchestration deployed
  ✓ Spark cluster active

Data Pipeline:
  ✓ 412M records ingested
  ✓ Bronze → Silver → Gold → Main
  ✓ Monthly partitioning implemented
  ✓ Quality checks passing

Documentation:
  ✓ README updated
  ✓ Architecture diagram
  ✓ Setup guide (this document)
  ✓ Code documented

Demo Ready:
  ✓ All services accessible
  ✓ Data queryable
  ✓ Dashboards (if time permits)
  ✓ Presentation slides
```

---

## 🚨 Common Issues & Fixes

### Storage Full (> 20 GB)
```bash
# Check usage
aws s3 ls s3://lakehouse-prod/raw/ --recursive --summarize \
    --endpoint-url https://objectstorage.us-ashburn-1.oraclecloud.com

# Delete raw CSVs
aws s3 rm s3://lakehouse-prod/raw/ --recursive \
    --endpoint-url https://objectstorage.us-ashburn-1.oraclecloud.com
```

### Service Not Starting
```bash
# Check logs
docker logs nessie
docker logs airflow-webserver
docker logs spark-master

# Restart
docker compose -f docker-compose-prod.yml restart
```

### SSH Connection Issues
```bash
# Check security rules allow port 22
# Check private key permissions
chmod 600 ~/.ssh/oracle-vm1.key
```

---

## 📝 Quick Reference

### VM1 (Airflow/Nessie)
```bash
IP: [VM1-PUBLIC-IP]
Services:
  - Nessie API: port 19120
  - Airflow Web: port 8080
SSH: ssh -i ~/.ssh/oracle-vm1.key ubuntu@[VM1-PUBLIC-IP]
```

### VM2 (Spark)
```bash
IP: [VM2-PUBLIC-IP]
Services:
  - Spark Master: port 7077
  - Spark UI: port 8081
  - Jupyter: port 8888
SSH: ssh -i ~/.ssh/oracle-vm2.key ubuntu@[VM2-PUBLIC-IP]
```

### Credentials
```bash
Oracle: ~/oracle-credentials.txt
Supabase: ~/supabase-credentials.txt
Airflow: admin / admin123 (change!)
```

---

**You're ready to submit! Total time: 2-3 days 🚀**

*Cost: $0/month | Records: 412 million | Production-grade: ✅*
