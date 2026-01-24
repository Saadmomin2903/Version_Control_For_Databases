# Production Deployment Guide - Part 2

**Continuation: Phases 4-8**

This is Part 2 of the deployment guide. See `PRODUCTION_DEPLOYMENT_GUIDE.md` for Phases 1-3.

---

## Phase 4: VM1 Deployment (Airflow + Nessie)

**Time**: 1-2 hours  
**Goal**: Deploy Airflow and Nessie on VM1 with production configuration

### Step 4.1: Initial VM1 Setup

```bash
# SSH into VM1
ssh -i ~/.ssh/oracle-vm1.key ubuntu@[VM1-PUBLIC-IP]

# You should see Ubuntu welcome message
# ubuntu@airflow-nessie:~$
```

**Update system**:
```bash
# Run as ubuntu user
sudo apt update && sudo apt upgrade -y

# Install essential packages
sudo apt install -y \
    docker.io \
    docker-compose-plugin \
    git \
    curl \
    wget \
    vim \
    htop \
    python3-pip

# Add ubuntu to docker group
sudo usermod -aG docker ubuntu

# Apply group change (logout/login)
exit
ssh -i ~/.ssh/oracle-vm1.key ubuntu@[VM1-PUBLIC-IP]

# Verify Docker
docker --version
docker ps
```

### Step 4.2: Clone Repository and Setup Structure

```bash
# Create workspace
cd /home/ubuntu
git clone https://github.com/[youruser]/lakehouse.git
cd lakehouse

# Create directory structure
mkdir -p airflow/{dags,logs,plugins,config}
mkdir -p scripts/{bronze,silver,gold,utils}
mkdir -p data/brazilian-ecommerce

# Set permissions
chmod -R 755 airflow
chmod -R 755 scripts
```

### Step 4.3: Create Production Environment File

**Load your saved credentials**:
```bash
# Copy from local machine
scp -i ~/.ssh/oracle-vm1.key ~/oracle-credentials.txt ubuntu@[VM1-PUBLIC-IP]:~/
scp -i ~/.ssh/oracle-vm1.key ~/supabase-credentials.txt ubuntu@[VM1-PUBLIC-IP]:~/
```

**On VM1, create `.env.prod`**:
```bash
cd /home/ubuntu/lakehouse

# Generate Fernet key
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" > /tmp/fernet.key

# Create production environment file
cat > .env.prod << 'ENVEOF'
# Supabase PostgreSQL
SUPABASE_HOST=db.xxxxxxxxxxxxx.supabase.co
SUPABASE_PASSWORD=[your-supabase-password]
SUPABASE_CONNECTION=postgresql://postgres:[password]@db.xxxxx.supabase.co:5432/postgres?sslmode=require

# Airflow
AIRFLOW_UID=50000
AIRFLOW_GID=0
AIRFLOW_FERNET_KEY=[paste from /tmp/fernet.key]

# Oracle Object Storage
ORACLE_ACCESS_KEY=[from oracle-credentials.txt]
ORACLE_SECRET_KEY=[from oracle-credentials.txt]
ORACLE_NAMESPACE=[your-namespace]
ORACLE_REGION=us-ashburn-1
ORACLE_ENDPOINT=https://objectstorage.us-ashburn-1.oraclecloud.com

# Nessie
NESSIE_URI=http://nessie:19120/api/v1

# VM2 Private IP (we'll update this after VM2 setup)
VM2_PRIVATE_IP=10.0.0.x
ENVEOF

# Secure the file
chmod 600 .env.prod
```

### Step 4.4: Create Production Docker Compose

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
    AIRFLOW__WEBSERVER__EXPOSE_CONFIG: 'true'
    AIRFLOW__API__AUTH_BACKENDS: 'airflow.api.auth.backend.basic_auth,airflow.api.auth.backend.session'
    # Spark connection
    SPARK_MASTER_URL: spark://${VM2_PRIVATE_IP}:7077
    NESSIE_URI: ${NESSIE_URI}
  volumes:
    - ./airflow/dags:/opt/airflow/dags
    - ./airflow/logs:/opt/airflow/logs
    - ./airflow/plugins:/opt/airflow/plugins
    - ./airflow/config:/opt/airflow/config
    - ./scripts:/opt/airflow/scripts
    - ./data:/opt/airflow/data
  user: "${AIRFLOW_UID:-50000}:${AIRFLOW_GID:-0}"
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
      - QUARKUS_LOG_LEVEL=INFO
      - QUARKUS_HTTP_ACCESS_LOG_ENABLED=true
    restart: always
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:19120/api/v1/config"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 40s
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
    networks:
      - lakehouse-network

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
      start_period: 60s
    restart: always
    networks:
      - lakehouse-network

  airflow-scheduler:
    <<: *airflow-common
    container_name: airflow-scheduler
    command: scheduler
    healthcheck:
      test: ["CMD", "curl", "--fail", "http://localhost:8974/health"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 60s
    restart: always
    networks:
      - lakehouse-network

  airflow-init:
    <<: *airflow-common
    container_name: airflow-init
    entrypoint: /bin/bash
    command:
      - -c
      - |
        mkdir -p /sources/logs /sources/dags /sources/plugins /sources/config
        chown -R "${AIRFLOW_UID}:${AIRFLOW_GID}" /sources/{logs,dags,plugins,config}
        exec /entrypoint airflow db init
        airflow users create \
          --username admin \
          --firstname Admin \
          --lastname User \
          --role Admin \
          --email admin@lakehouse.local \
          --password admin123
    environment:
      <<: *airflow-common-env
    user: "0:0"
    volumes:
      - ./airflow:/sources

networks:
  lakehouse-network:
    driver: bridge
DOCKEREOF
```

### Step 4.5: Initialize and Start Services

```bash
# Load environment variables
source .env.prod

# Initialize Airflow (creates DB schema in Supabase)
docker compose -f docker-compose-prod.yml up airflow-init

# Wait for "Airflow is ready" message
# This creates tables in Supabase for Airflow metadata

# Start all services
docker compose -f docker-compose-prod.yml up -d

# Check status
docker compose -f docker-compose-prod.yml ps

# Expected output:
# NAME                  STATUS              PORTS
# nessie                Up (healthy)        0.0.0.0:19120->19120/tcp
# airflow-webserver     Up (healthy)        0.0.0.0:8080->8080/tcp
# airflow-scheduler     Up (healthy)
```

### Step 4.6: Verify Deployments

**Test Nessie**:
```bash
# From VM1
curl http://localhost:19120/api/v1/config

# Should return JSON with Nessie version info
```

**Test Airflow**:
```bash
# From your local machine browser
open http://[VM1-PUBLIC-IP]:8080

# Login credentials:
# Username: admin
# Password: admin123
#
# ⚠️ Change password immediately:
# Click "Admin" → "Users" → Edit admin → Change password
```

**Verify Supabase tables created**:
```bash
# From local machine
psql "postgresql://postgres:[password]@db.xxxxx.supabase.co:5432/postgres?sslmode=require"

\dt  # List tables

# Should see Airflow tables:
# - dag
# - dag_run
# - task_instance
# - log
# etc.

# And Nessie tables:
# - nessie (will be created on first use)

\q
```

**✅ Step 4.6 Complete!** Services running on VM1:
- ✅ Nessie API (port 19120)
- ✅ Airflow Web UI (port 8080)
- ✅ Airflow Scheduler (backend)

---

## Phase 5: VM2 Deployment (Spark)

**Time**: 1 hour  
**Goal**: Deploy Spark cluster on VM2

### Step 5.1: Initial VM2 Setup

```bash
# SSH into VM2
ssh -i ~/.ssh/oracle-vm2.key ubuntu@[VM2-PUBLIC-IP]

# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
sudo apt install -y docker.io git curl
sudo usermod -aG docker ubuntu

# Logout/login
exit
ssh -i ~/.ssh/oracle-vm2.key ubuntu@[VM2-PUBLIC-IP]

# Verify
docker --version
```

### Step 5.2: Clone Repository

```bash
cd /home/ubuntu
git clone https://github.com/[youruser]/lakehouse.git
cd lakehouse

# Create directories
mkdir -p scripts/{bronze,silver,gold,utils}
mkdir -p data/brazilian-ecommerce
```

### Step 5.3: Create Spark Environment File

```bash
cat > .env.spark << 'SPARKENVEOF'
# Oracle Object Storage (S3-compatible)
ORACLE_ACCESS_KEY=[your-access-key]
ORACLE_SECRET_KEY=[your-secret-key]
ORACLE_NAMESPACE=[your-namespace]
ORACLE_REGION=us-ashburn-1
ORACLE_ENDPOINT=https://objectstorage.us-ashburn-1.oraclecloud.com

# Nessie (VM1 private IP)
NESSIE_URI=http://[VM1-PRIVATE-IP]:19120/api/v1

# Warehouse location
WAREHOUSE=oci://[namespace]/lakehouse-prod/warehouse

# Spark config
SPARK_DRIVER_MEMORY=4g
SPARK_EXECUTOR_MEMORY=8g
SPARK_WORKER_CORES=2
SPARK_WORKER_MEMORY=10G
SPARKENVEOF

chmod 600 .env.spark
```

**Get VM1 Private IP**:
```bash
# On VM1:
hostname -I | awk '{print $1}'
# Example output: 10.0.0.4

# Update .env.spark with this IP
```

### Step 5.4: Create Spark Docker Compose

```bash
cat > docker-compose-spark.yml << 'SPARKDOCKEREOF'
version: '3.8'

services:
  spark-master:
    image: alexmerced/spark33-notebook
    container_name: spark-master
    hostname: spark-master
    ports:
      - "8888:8888"  # Jupyter
      - "7077:7077"  # Spark Master
      - "8081:8080"  # Spark UI
    environment:
      - SPARK_MODE=master
      - SPARK_MASTER_HOST=0.0.0.0
      - SPARK_MASTER_PORT=7077
      - SPARK_MASTER_WEBUI_PORT=8080
      - SPARK_DRIVER_MEMORY=${SPARK_DRIVER_MEMORY}
      # Oracle Object Storage
      - AWS_ACCESS_KEY_ID=${ORACLE_ACCESS_KEY}
      - AWS_SECRET_ACCESS_KEY=${ORACLE_SECRET_KEY}
      - AWS_S3_ENDPOINT=${ORACLE_ENDPOINT}
      - AWS_REGION=${ORACLE_REGION}
      # Nessie
      - NESSIE_URI=${NESSIE_URI}
      - WAREHOUSE=${WAREHOUSE}
    volumes:
      - ./scripts:/home/jovyan/scripts
      - ./data:/home/jovyan/data
    restart: always
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s
    networks:
      - spark-network

  spark-worker:
    image: alexmerced/spark33-notebook
    container_name: spark-worker
    hostname: spark-worker
    environment:
      - SPARK_MODE=worker
      - SPARK_MASTER_URL=spark://spark-master:7077
      - SPARK_WORKER_CORES=${SPARK_WORKER_CORES}
      - SPARK_WORKER_MEMORY=${SPARK_WORKER_MEMORY}
      - SPARK_EXECUTOR_MEMORY=${SPARK_EXECUTOR_MEMORY}
    depends_on:
      spark-master:
        condition: service_healthy
    restart: always
    networks:
      - spark-network

networks:
  spark-network:
    driver: bridge
SPARKDOCKEREOF
```

### Step 5.5: Start Spark Cluster

```bash
# Load environment
source .env.spark

# Start Spark
docker compose -f docker-compose-spark.yml up -d

# Check status
docker compose -f docker-compose-spark.yml ps

# View logs
docker logs spark-master
docker logs spark-worker

# Expected:
# spark-master: "Successfully started service 'sparkMaster'"
# spark-worker: "Successfully registered with master"
```

### Step 5.6: Verify Spark Cluster

**Test from browser**:
```bash
# Jupyter Notebook
open http://[VM2-PUBLIC-IP]:8888

# Spark Master UI
open http://[VM2-PUBLIC-IP]:8081
# Should show 1 worker connected
```

**Test from Spark shell**:
```bash
docker exec -it spark-master bash

# Inside container:
pyspark

# In PySpark shell:
>>> sc
# Should show SparkContext
>>> sc.master
# Should show: 'spark://spark-master:7077'
>>> exit()
```

**✅ Phase 5 Complete!** Spark cluster running on VM2:
- ✅ Spark Master (port 7077)
- ✅ Spark Worker (1 worker, 2 cores, 10GB RAM)
- ✅ Jupyter Notebook (port 8888)
- ✅ Spark UI (port 8081)

---

## Phase 6: Data Migration

**Time**: 1-2 hours  
**Goal**: Upload data and scripts to cloud VMs

### Step 6.1: Upload Brazilian E-Commerce Dataset

**From your local machine**:

```bash
# Compress dataset
cd ~/Documents/Version_Control_For_Databases/data/brazilian-ecommerce
tar -czf brazilian-ecommerce.tar.gz *.csv

# Upload to VM2
scp -i ~/.ssh/oracle-vm2.key \
    brazilian-ecommerce.tar.gz \
    ubuntu@[VM2-PUBLIC-IP]:/home/ubuntu/lakehouse/data/

# SSH into VM2 and extract
ssh -i ~/.ssh/oracle-vm2.key ubuntu@[VM2-PUBLIC-IP]

cd /home/ubuntu/lakehouse/data
tar -xzf brazilian-ecommerce.tar.gz -C brazilian-ecommerce/
rm brazilian-ecommerce.tar.gz

# Verify
ls -lh brazilian-ecommerce/
# Should see all CSV files
```

### Step 6.2: Upload Processing Scripts

```bash
# From local machine:
cd ~/Documents/Version_Control_For_Databases

# Upload bronze scripts
scp -i ~/.ssh/oracle-vm2.key \
    scripts/bronze/ingest_brazilian_orders.py \
    scripts/bronze/ingest_brazilian_customers.py \
    ubuntu@[VM2-PUBLIC-IP]:/home/ubuntu/lakehouse/scripts/bronze/

# Upload silver scripts
scp -i ~/.ssh/oracle-vm2.key \
    scripts/silver/transform_orders_silver.py \
    scripts/silver/transform_customers_silver.py \
    ubuntu@[VM2-PUBLIC-IP]:/home/ubuntu/lakehouse/scripts/silver/

# Upload gold script
scp -i ~/.ssh/oracle-vm2.key \
    scripts/gold/aggregate_customer_summary_gold.py \
    ubuntu@[VM2-PUBLIC-IP]:/home/ubuntu/lakehouse/scripts/gold/

# Upload utils
scp -i ~/.ssh/oracle-vm2.key \
    scripts/utils/create_nessie_branches.py \
    scripts/utils/promote_to_production.py \
    scripts/utils/quality_checks.py \
    ubuntu@[VM2-PUBLIC-IP]:/home/ubuntu/lakehouse/scripts/utils/
```

### Step 6.3: Update Script Configurations for Oracle Object Storage

**On VM2**, update scripts to use Oracle instead of MinIO:

```bash
ssh -i ~/.ssh/oracle-vm2.key ubuntu@[VM2-PUBLIC-IP]
cd /home/ubuntu/lakehouse/scripts/bronze

# Edit ingest_brazilian_orders.py
# Replace environment variables section:
vim ingest_brazilian_orders.py
```

**Update these lines**:
```python
# Change from:
AWS_S3_ENDPOINT = os.getenv("AWS_S3_ENDPOINT", "http://minio:9000")

# To:
AWS_S3_ENDPOINT = os.getenv("AWS_S3_ENDPOINT", "https://objectstorage.us-ashburn-1.oraclecloud.com")

# Also update:
.set('spark.hadoop.fs.s3a.connection.ssl.enabled', 'true')  # Changed from 'false'
.set('spark.hadoop.fs.s3a.path.style.access', 'false')  # Changed from 'true'
```

**Repeat for all scripts**:
- `ingest_brazilian_customers.py`
- `transform_orders_silver.py`
- `transform_customers_silver.py`
- `aggregate_customer_summary_gold.py`

**Or use sed to batch update**:
```bash
cd /home/ubuntu/lakehouse/scripts

# Update endpoint
find . -name "*.py" -type f -exec sed -i \
  's|http://minio:9000|https://objectstorage.us-ashburn-1.oraclecloud.com|g' {} +

# Update SSL
find . -name "*.py" -type f -exec sed -i \
  "s|'spark.hadoop.fs.s3a.connection.ssl.enabled', 'false'|'spark.hadoop.fs.s3a.connection.ssl.enabled', 'true'|g" {} +

# Update path style
find . -name "*.py" -type f -exec sed -i \
  "s|'spark.hadoop.fs.s3a.path.style.access', 'true'|'spark.hadoop.fs.s3a.path.style.access', 'false'|g" {} +
```

### Step 6.4: Test Oracle Object Storage Connection

```bash
# On VM2, test S3 connectivity
docker exec spark-master python3 << TESTPY
import boto3

s3 = boto3.client(
    's3',
    endpoint_url='https://objectstorage.us-ashburn-1.oraclecloud.com',
    aws_access_key_id='[your-access-key]',
    aws_secret_access_key='[your-secret-key]'
)

# List buckets
print("Buckets:", [b['Name'] for b in s3.list_buckets()['Buckets']])

# Test write
s3.put_object(Bucket='lakehouse-prod', Key='test.txt', Body=b'Hello from Spark!')
print("✓ Write successful")

# Test read
obj = s3.get_object(Bucket='lakehouse-prod', Key='test.txt')
print("✓ Read successful:", obj['Body'].read())
TESTPY
```

**✅ Phase 6 Complete!** Data and scripts migrated:
- ✅ Brazilian E-Commerce dataset on VM2
- ✅ All processing scripts uploaded
- ✅ Scripts configured for Oracle Object Storage
- ✅ Oracle S3 connectivity tested

---

## Phase 7: Production Pipeline Testing

**Time**: 2-3 hours  
**Goal**: Run end-to-end pipeline on production infrastructure

### Step 7.1: Create Nessie Branches

```bash
# SSH to VM2
ssh -i ~/.ssh/oracle-vm2.key ubuntu@[VM2-PUBLIC-IP]

# Create branches
docker exec spark-master python3 /home/jovyan/scripts/utils/create_nessie_branches.py

# Verify from VM1 (Nessie running there)
ssh -i ~/.ssh/oracle-vm1.key ubuntu@[VM1-PUBLIC-IP]

curl http://localhost:19120/api/v1/trees | python3 -c \
  "import json, sys; print('Branches:', [r['name'] for r in json.load(sys.stdin)['references']])"

# Expected: Branches: ['main', 'bronze', 'silver', 'gold']
```

### Step 7.2: Run Bronze Layer

```bash
# On VM2:
cd /home/ubuntu/lakehouse

# Ingest orders
docker exec spark-master \
  python3 /home/jovyan/scripts/bronze/ingest_brazilian_orders.py

# Monitor output for:
# ✓ Loaded XX,XXX orders
# ✓ Transformed XX,XXX records
# ✓ Verified: XX,XXX records in orders_bronze

# Ingest customers
docker exec spark-master \
  python3 /home/jovyan/scripts/bronze/ingest_brazilian_customers.py

# Monitor output for:
# ✓ Loaded XX,XXX customers
# ✓ Verified: XX,XXX records in customers_bronze
```

**Verify Bronze layer**:
```bash
# From VM1:
curl -s http://localhost:19120/api/v1/trees/tree/bronze/entries | python3 << VERIFY
import json, sys
entries = json.load(sys.stdin).get('entries', [])
tables = [e for e in entries if e.get('type') == 'ICEBERG_TABLE']
print(f"Bronze tables: {len(tables)}")
for t in tables:
    print(f"  - {'.'.join(t['name']['elements'])}")
VERIFY

# Expected:
# Bronze tables: 2
#   - ecommerce.orders_bronze
#   - ecommerce.customers_bronze
```

### Step 7.3: Run Silver Layer

```bash
# On VM2:

# Transform orders
docker exec spark-master \
  python3 /home/jovyan/scripts/silver/transform_orders_silver.py

# Transform customers
docker exec spark-master \
  python3 /home/jovyan/scripts/silver/transform_customers_silver.py
```

**Verify Silver layer**:
```bash
# From VM1:
curl -s http://localhost:19120/api/v1/trees/tree/silver/entries | python3 << VERIFY
import json, sys
entries = json.load(sys.stdin).get('entries', [])
tables = [e for e in entries if e.get('type') == 'ICEBERG_TABLE']
print(f"Silver tables: {len(tables)}")
for t in tables:
    print(f"  - {'.'.join(t['name']['elements'])}")
VERIFY

# Expected:
# Silver tables: 2
#   - ecommerce.orders_silver
#   - ecommerce.customers_silver
```

### Step 7.4: Run Gold Layer (Staging)

```bash
# On VM2:
docker exec spark-master \
  python3 /home/jovyan/scripts/gold/aggregate_customer_summary_gold.py

# Monitor output for customer segments and revenue metrics
```

**Verify Gold staging**:
```bash
# From VM1:
curl -s http://localhost:19120/api/v1/trees/tree/gold/entries | python3 << VERIFY
import json, sys
entries = json.load(sys.stdin).get('entries', [])
tables = [e for e in entries if e.get('type') == 'ICEBERG_TABLE']
print(f"Gold (staging) tables: {len(tables)}")
for t in tables:
    print(f"  - {'.'.join(t['name']['elements'])}")
VERIFY

# Expected:
# Gold (staging) tables: 1
#   - ecommerce.customer_summary
```

### Step 7.5: Promote to Production

```bash
# On VM1:
ssh -i ~/.ssh/oracle-vm1.key ubuntu@[VM1-PUBLIC-IP]

cd /home/ubuntu/lakehouse
echo "yes" | python3 scripts/utils/promote_to_production.py

# Monitor output for:
# ✅ PROMOTION SUCCESSFUL!
# 📊 Main branch now points to gold's data
```

**Verify Production**:
```bash
curl -s http://localhost:19120/api/v1/trees/tree/main/entries | python3 << VERIFY
import json, sys
entries = json.load(sys.stdin).get('entries', [])
tables = [e for e in entries if e.get('type') == 'ICEBERG_TABLE']
print(f"Main (production) tables: {len(tables)}")
for t in tables:
    print(f"  - {'.'.join(t['name']['elements'])}")
VERIFY

# Expected:
# Main (production) tables: 1
#   - ecommerce.customer_summary
```

### Step 7.6: Verify Data in Oracle Object Storage

```bash
# Install AWS CLI on VM2
sudo apt install -y awscli

# Configure for Oracle
aws configure set aws_access_key_id [your-access-key]
aws configure set aws_secret_access_key [your-secret-key]
aws configure set region us-ashburn-1

# List warehouse files
aws s3 ls s3://lakehouse-prod/warehouse/ \
  --endpoint-url https://objectstorage.us-ashburn-1.oraclecloud.com \
  --recursive

# Should see Parquet files organized by table and branch
```

**✅ Phase 7 Complete!** Production pipeline validated:
- ✅ Bronze layer: 2 tables, ~100k records
- ✅ Silver layer: 2 tables, quality-checked
- ✅ Gold layer: 1 table, customer aggregations
- ✅ Production: Promoted to main branch
- ✅ Data persisted in Oracle Object Storage

---

## Phase 8: Monitoring Setup

**Time**: 1 hour  
**Goal**: Deploy Grafana monitoring for production observability

### Step 8.1: Sign Up for Grafana Cloud

```bash
# Open Grafana Cloud
open https://grafana.com/auth/sign-up/create-user

# Create account (free tier)
# Create stack: "lakehouse-monitoring"
# Region: US (closest to Oracle us-ashburn-1)
```

### Step 8.2: Get Grafana Cloud Credentials

```bash
# After stack created:
# Go to: Grafana Cloud Portal → Stack → Details

# Copy these values:
GRAFANA_PROMETHEUS_URL=https://prometheus-prod-XX.grafana.net/api/prom/push
GRAFANA_LOKI_URL=https://logs-prod-XX.grafana.net/loki/api/v1/push
GRAFANA_INSTANCE_ID=XXXXXX
GRAFANA_API_KEY=[Generate from "Generate now" button]
```

### Step 8.3: Install Grafana Agent on VM1

```bash
# SSH to VM1
ssh -i ~/.ssh/oracle-vm1.key ubuntu@[VM1-PUBLIC-IP]

# Download Grafana Agent
wget https://github.com/grafana/agent/releases/download/v0.38.1/grafana-agent-linux-arm64.zip
unzip grafana-agent-linux-arm64.zip
sudo mv grafana-agent-linux-arm64 /usr/local/bin/grafana-agent
sudo chmod +x /usr/local/bin/grafana-agent
rm grafana-agent-linux-arm64.zip

# Create config directory
sudo mkdir -p /etc/grafana-agent
```

**Create agent config**:
```bash
sudo nano /etc/grafana-agent/config.yaml
```

**Paste this configuration**:
```yaml
server:
  log_level: info

metrics:
  global:
    scrape_interval: 60s
    remote_write:
      - url: [YOUR_PROMETHEUS_URL]
        basic_auth:
          username: [YOUR_INSTANCE_ID]
          password: [YOUR_API_KEY]

  configs:
    - name: lakehouse-metrics
      scrape_configs:
        - job_name: 'nessie'
          static_configs:
            - targets: ['localhost:19120']
              labels:
                service: 'nessie'
                environment: 'production'
        
        - job_name: 'airflow'
          static_configs:
            - targets: ['localhost:8080']
              labels:
                service: 'airflow'
                environment: 'production'
        
        - job_name: 'node'
          static_configs:
            - targets: ['localhost:9100']
              labels:
                service: 'node-exporter'
                environment: 'production'

logs:
  configs:
    - name: lakehouse-logs
      clients:
        - url: [YOUR_LOKI_URL]
          basic_auth:
            username: [YOUR_INSTANCE_ID]
            password: [YOUR_API_KEY]
      positions:
        filename: /tmp/positions.yaml
      scrape_configs:
        - job_name: docker
          docker_sd_configs:
            - host: unix:///var/run/docker.sock
              refresh_interval: 5s
          relabel_configs:
            - source_labels: ['__meta_docker_container_name']
              regex: '/(.*)'
              target_label: 'container'
            - source_labels: ['__meta_docker_container_log_stream']
              target_label: 'stream'
```

**Save and create systemd service**:
```bash
sudo nano /etc/systemd/system/grafana-agent.service
```

**Paste**:
```ini
[Unit]
Description=Grafana Agent
After=network-online.target
Wants=network-online.target

[Service]
User=root
ExecStart=/usr/local/bin/grafana-agent -config.file=/etc/grafana-agent/config.yaml
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Start agent**:
```bash
sudo systemctl daemon-reload
sudo systemctl enable grafana-agent
sudo systemctl start grafana-agent
sudo systemctl status grafana-agent

# Should show: "active (running)"
```

### Step 8.4: Create Dashboard in Grafana

```bash
# Open your Grafana instance
open https://yourstack.grafana.net

# Login with your Grafana Cloud credentials
```

**Create Lakehouse Dashboard**:
1. Click **+** → **Dashboard** → **Add visualization**
2. Select **Prometheus** as data source
3. Add panels:

**Panel 1: Nessie Branch Count**
```promql
# Query:
count by (branch) (nessie_repository_commits_total)

# Panel settings:
Title: Nessie Branches
Visualization: Stat
```

**Panel 2: Docker Container Status**
```promql
# Query:
up{job="docker"}

# Panel settings:
Title: Container Health
Visualization: Stat
Legend: {{container}}
```

**Panel 3: Airflow DAG Runs**
```promql
# Query:
airflow_dagrun_duration_seconds_sum

# Panel settings:
Title: DAG Execution Time
Visualization: Time series
```

4. Click **Save dashboard**
5. Name: "Lakehouse Production"

### Step 8.5: Create Alerts

**Create alert rule**:
```yaml
Alert Name: Pipeline Failure
Condition: airflow_dagrun_failed_total > 0
For: 5m
Annotations:
  summary: "Production pipeline failed"
  description: "Check Airflow UI for details"

Contact Point: Email / Slack webhook
```

**✅ Phase 8 Complete!** Monitoring deployed:
- ✅ Grafana Agent collecting metrics
- ✅ Docker logs forwarded to Loki
- ✅ Production dashboard created
- ✅ Alerts configured

---

## 🎉 Deployment Complete!

### **Final Checklist**:

**Infrastructure**:
- ✅ Oracle Cloud VMs running (2x)
- ✅ Oracle Object Storage configured
- ✅ Supabase PostgreSQL connected
- ✅ Grafana Cloud monitoring active

**Services**:
- ✅ Nessie API (VM1:19120)
- ✅ Airflow Web UI (VM1:8080)
- ✅ Spark Master (VM2:7077)
- ✅ Jupyter Notebook (VM2:8888)

**Data Pipeline**:
- ✅ Brazilian E-Commerce dataset (100k+ orders)
- ✅ Bronze→Silver→Gold→Main workflow
- ✅ Quality gates functional
- ✅ Promotion script working

**Cost**: **$0/month** ✅

---

## Next Steps

1. **Schedule Daily Runs** - Create Airflow DAG
2. **Add More Datasets** - Expand to products, reviews
3. **Create BI Dashboards** - Query with Jupyter/Tableau
4. **Optimize Performance** - Tune Spark configs
5. **Document APIs** - For team access

**Congratulations!** You now have a production-grade data lakehouse processing real e-commerce data at zero cost! 🚀

---

**Document Version**: 2.0  
**Last Updated**: 2026-01-19  
**Status**: Production Ready
