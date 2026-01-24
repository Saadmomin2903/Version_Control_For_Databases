# Ultra-Detailed Production Guide - Part 4 of 4

**Docker Deployment & Pipeline Execution**

---

## 🎯 What You'll Accomplish in Part 4

By the end of this guide, you will have:
- ✅ Docker running on both VMs
- ✅ Airflow + Nessie deployed on VM1
- ✅ Spark cluster deployed on VM2
- ✅ Data uploaded to Oracle Storage
- ✅ Processing scripts configured
- ✅ **Production pipeline running with 412M records!**

**Time Required**: 4-6 hours  
**Prerequisites**: Parts 1-3 completed

---

## Step 11: Configure VM1 (Airflow + Nessie)

### Step 11.1: SSH into VM1

**From your local machine**:

```bash
# Use the private key from Part 2
ssh -i ~/.ssh/oracle-vm1.key ubuntu@[VM1-PUBLIC-IP]
```

**Replace**:
- `[VM1-PUBLIC-IP]` with your actual VM1 public IP
- Find it in `~/oracle-vm1-info.txt` or Oracle Console

**What you'll see**:
```
Welcome to Ubuntu 22.04.3 LTS (GNU/Linux 5.15.0-1045-oracle aarch64)

ubuntu@airflow-nessie:~$
```

---

### Step 11.2: Update System and Install Docker

**Update package list**:
```bash
sudo apt update
```

**What you'll see**:
```
Hit:1 http://ports.ubuntu.com/ubuntu-ports jammy InRelease
Get:2 http://ports.ubuntu.com/ubuntu-ports jammy-updates InRelease [119 kB]
...
Fetched 12.4 MB in 5s (2,487 kB/s)
Reading package lists... Done
```

**Upgrade packages**:
```bash
sudo apt upgrade -y
```

**What happens**:
```
Reading package lists... Done
Building dependency tree... Done
...
The following packages will be upgraded:
  base-files libssl3 openssh-client ...
XX upgraded, 0 newly installed, 0 to remove

# This takes 2-5 minutes
# Press Enter if prompted
```

**Install Docker**:
```bash
sudo apt install -y docker.io docker-compose-plugin git curl wget vim
```

**What you'll see**:
```
Reading package lists... Done
Building dependency tree... Done
The following NEW packages will be installed:
  containerd docker.io runc ...
...
Setting up docker.io (XX.XX.XX) ...
```

**Add Ubuntu user to Docker group**:
```bash
sudo usermod -aG docker ubuntu
```

**What this does**:
```
- Adds ubuntu user to docker group
- Allows running docker without sudo
- Takes effect after re-login
```

**Verify Docker group**:
```bash
groups ubuntu
# Should show: ubuntu adm dialout ... docker
```

**Apply group changes** (logout/login):
```bash
exit
# Back on local machine now

# SSH back in
ssh -i ~/.ssh/oracle-vm1.key ubuntu@[VM1-PUBLIC-IP]
```

**Verify Docker works**:
```bash
docker --version
# Should show: Docker version 24.0.X

docker ps
# Should show: CONTAINER ID   IMAGE ...  (empty table)
```

---

### Step 11.3: Clone Repository

**Navigate to home directory**:
```bash
cd /home/ubuntu
pwd
# Should show: /home/ubuntu
```

**Clone your lakehouse repo**:
```bash
git clone https://github.com/[youruser]/lakehouse.git
```

**Replace**:
- `[youruser]` with your actual GitHub username
- Example: `git clone https://github.com/john/lakehouse.git`

**What you'll see**:
```
Cloning into 'lakehouse'...
remote: Enumerating objects: 145, done.
remote: Counting objects: 100% (145/145), done.
...
Receiving objects: 100% (145/145), 125.50 KiB | 2.51 MiB/s, done.
Resolving deltas: 100% (65/65), done.
```

**Verify clone**:
```bash
cd lakehouse
ls -la
# Should show: docker-compose.yml, scripts/, README.md, etc.
```

---

### Step 11.4: Create Directory Structure

**Create required directories**:
```bash
# Still in /home/ubuntu/lakehouse

mkdir -p airflow/{dags,logs,plugins,config}
mkdir -p scripts/{bronze,silver,gold,utils}
mkdir -p data

# Set permissions
chmod -R 755 airflow scripts data
```

**Verify structure**:
```bash
tree -L 2
# Should show:
# .
# ├── airflow
# │   ├── dags
# │   ├── logs
# │   ├── plugins
# │   └── config
# ├── scripts
# │   ├── bronze
# │   ├── silver
# │   ├── gold
# │   └── utils
# └── data
```

---

### Step 11.5: Create Environment File

**Install Python cryptography** (for Fernet key):
```bash
sudo apt install -y python3-pip
pip3 install cryptography
```

**Generate Fernet key**:
```bash
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

**What you'll see**:
```
mL6F_9Kp3Xw8vN2jH7bQ5tR4yU1oI6eW0sA9dC8fG3=
```

**Copy this key** - you'll use it in next step!

**Create `.env.prod` file**:
```bash
cat > .env.prod << 'ENVEOF'
# Supabase PostgreSQL
SUPABASE_HOST=db.xxxxxxxxxxxxx.supabase.co
SUPABASE_PASSWORD=[your-supabase-password]
SUPABASE_CONNECTION=postgresql://postgres:[password]@db.xxxxx.supabase.co:5432/postgres?sslmode=require

# Airflow
AIRFLOW_UID=50000
AIRFLOW_GID=0
AIRFLOW_FERNET_KEY=[paste-fernet-key-here]

# Oracle Object Storage
ORACLE_ACCESS_KEY=[your-oracle-access-key]
ORACLE_SECRET_KEY=[your-oracle-secret-key]
ORACLE_NAMESPACE=[your-namespace]
ORACLE_REGION=us-ashburn-1
ORACLE_ENDPOINT=https://objectstorage.us-ashburn-1.oraclecloud.com

# Nessie
NESSIE_URI=http://nessie:19120/api/v1

# VM2 Private IP (we'll update this later)
VM2_PRIVATE_IP=10.0.0.x
ENVEOF
```

**Edit the file** to replace placeholders:
```bash
vim .env.prod
# Or use: nano .env.prod
```

**What to replace**:
```
SUPABASE_HOST → from ~/supabase-credentials.txt
SUPABASE_PASSWORD → from ~/supabase-credentials.txt  
SUPABASE_CONNECTION → from ~/supabase-credentials.txt
AIRFLOW_FERNET_KEY → the key you just generated
ORACLE_ACCESS_KEY → from ~/oracle-s3-credentials.txt
ORACLE_SECRET_KEY → from ~/oracle-s3-credentials.txt
ORACLE_NAMESPACE → from ~/oracle-s3-credentials.txt
```

**Tip for copying from local to VM**:
```bash
# On local machine:
cat ~/supabase-credentials.txt
# Copy the values

# Then paste them into VM1's .env.prod file
```

**Secure the file**:
```bash
chmod 600 .env.prod
```

**Verify**:
```bash
cat .env.prod
# Should show all values filled in (no [placeholders])
```

---

### Step 11.6: Create Docker Compose for Production

**Create `docker-compose-prod.yml`**:
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
  volumes:
    - ./airflow/dags:/opt/airflow/dags
    - ./airflow/logs:/opt/airflow/logs
    - ./airflow/plugins:/opt/airflow/plugins
    - ./scripts:/opt/airflow/scripts
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
        airflow users create \
          --username admin \
          --password admin123 \
          --firstname Admin \
          --lastname User \
          --role Admin \
          --email admin@lakehouse.local
    environment:
      <<: *airflow-common-env
    user: "0:0"
    volumes:
      - ./airflow:/sources
DOCKEREOF
```

---

### Step 11.7: Initialize and Start Services

**Load environment variables**:
```bash
source .env.prod
```

**Initialize Airflow** (creates DB schema in Supabase):
```bash
docker compose -f docker-compose-prod.yml up airflow-init
```

**What you'll see**:
```
[+] Running 1/0
 ⠿ Container airflow-init  Created
Attaching to airflow-init
airflow-init  | Initializing Airflow database...
airflow-init  | DB: postgresql://postgres:***@db.xxx.supabase.co:5432/postgres
airflow-init  | [2024-01-19 12:30:45] {db.py:1109} INFO - Creating tables
airflow-init  | INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
...
airflow-init  | Admin user admin created
airflow-init  | 2.8.1
airflow-init exited with code 0
```

**✅ Success indicators**:
```
✓ "Creating tables" message shown
✓ "Admin user admin created"
✓ "exited with code 0"
✓ No errors about connection
```

**Start all services**:
```bash
docker compose -f docker-compose-prod.yml up -d
```

**What you'll see**:
```
[+] Running 4/4
 ⠿ Container nessie              Started
 ⠿ Container airflow-webserver   Started
 ⠿ Container airflow-scheduler   Started
 ⠿ Network lakehouse_default     Created
```

**Check container status**:
```bash
docker compose -f docker-compose-prod.yml ps
```

**Expected output**:
```
NAME                 STATUS              PORTS
nessie               Up (healthy)        0.0.0.0:19120->19120/tcp
airflow-webserver    Up (healthy)        0.0.0.0:8080->8080/tcp
airflow-scheduler    Up (healthy)
```

**All should show "Up (healthy)"** - wait 1-2 minutes if showing "starting"

---

### Step 11.8: Verify Services Running

**Test Nessie API** (from VM1):
```bash
curl http://localhost:19120/api/v1/config
```

**Expected output**:
```json
{
  "defaultBranch": "main",
  "minSupportedApiVersion": 1,
  "maxSupportedApiVersion": 2,
  "actualApiVersion": 2
}
```

**Test from local machine** (check firewall):
```bash
# From your local computer:
curl http://[VM1-PUBLIC-IP]:19120/api/v1/config
```

**Test Airflow Web UI**:
```bash
# From your local browser:
open http://[VM1-PUBLIC-IP]:8080
```

**What you'll see**:
- Airflow login page
- Username field
- Password field

**Login credentials**:
```
Username: admin
Password: admin123
```

**After login**:
- Airflow dashboard
- Empty DAGs list (we'll add them later)
- Top menu: DAGs, Security, Browse, etc.

---

## Step 12: Configure VM2 (Spark)

### Step 12.1: SSH into VM2

**From local machine** (open new terminal):
```bash
ssh -i ~/.ssh/oracle-vm2.key ubuntu@[VM2-PUBLIC-IP]
```

**What you'll see**:
```
Welcome to Ubuntu 22.04.3 LTS ...

ubuntu@spark-cluster:~$
```

---

### Step 12.2: Install Docker

**Same steps as VM1**:
```bash
sudo apt update
sudo apt upgrade -y
sudo apt install -y docker.io docker-compose-plugin git curl
sudo usermod -aG docker ubuntu

# Logout/login
exit
ssh -i ~/.ssh/oracle-vm2.key ubuntu@[VM2-PUBLIC-IP]

# Verify
docker --version
docker ps
```

---

### Step 12.3: Clone Repo and Setup

```bash
cd /home/ubuntu
git clone https://github.com/[youruser]/lakehouse.git
cd lakehouse

mkdir -p scripts/{bronze,silver,gold,utils} data
chmod -R 755 scripts data
```

---

### Step 12.4: Get VM1 Private IP

**On VM1** (SSH terminal):
```bash
hostname -I | awk '{print $1}'
```

**Output example**:
```
10.0.0.4
```

**Save this** - you'll use it in VM2's config!

---

### Step 12.5: Create Spark Environment

**On VM2**, create `.env.spark`:
```bash
cat > .env.spark << 'SPARKENV'
# Oracle Object Storage
ORACLE_ACCESS_KEY=[your-access-key]
ORACLE_SECRET_KEY=[your-secret-key]
ORACLE_NAMESPACE=[your-namespace]
ORACLE_REGION=us-ashburn-1
ORACLE_ENDPOINT=https://objectstorage.us-ashburn-1.oraclecloud.com

# Nessie (VM1 private IP)
NESSIE_URI=http://10.0.0.4:19120/api/v1

# Warehouse location
WAREHOUSE=oci://[namespace]/lakehouse-prod/warehouse

# Spark config
SPARK_DRIVER_MEMORY=4g
SPARK_EXECUTOR_MEMORY=8g
SPARK_WORKER_CORES=2
SPARK_WORKER_MEMORY=10G
SPARKENV
```

**Edit to replace placeholders**:
```bash
vim .env.spark

# Replace:
# - Oracle keys from credentials file
# - 10.0.0.4 with actual VM1 private IP
# - [namespace] with your Oracle namespace
```

**Secure**:
```bash
chmod 600 .env.spark
```

---

### Step 12.6: Create Spark Docker Compose

```bash
cat > docker-compose-spark.yml << 'SPARKDOCKER'
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
      - SPARK_DRIVER_MEMORY=${SPARK_DRIVER_MEMORY}
      - AWS_ACCESS_KEY_ID=${ORACLE_ACCESS_KEY}
      - AWS_SECRET_ACCESS_KEY=${ORACLE_SECRET_KEY}
      - AWS_S3_ENDPOINT=${ORACLE_ENDPOINT}
      - AWS_REGION=${ORACLE_REGION}
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
SPARKDOCKER
```

---

### Step 12.7: Start Spark Cluster

```bash
source .env.spark
docker compose -f docker-compose-spark.yml up -d
```

**What you'll see**:
```
[+] Running 3/3
 ⠿ Network lakehouse_default  Created
 ⠿ Container spark-master     Started
 ⠿ Container spark-worker     Started
```

**Check status**:
```bash
docker compose -f docker-compose-spark.yml ps

# Expected:
# spark-master   Up (healthy)   8888,7077,8081->8080
# spark-worker   Up             
```

**Check logs**:
```bash
docker logs spark-master | grep "Successfully started"
# Should show: "Successfully started service 'sparkMaster'"

docker logs spark-worker | grep "Successfully registered"
# Should show: "Successfully registered with master"
```

---

### Step 12.8: Verify Spark Web UIs

**From local browser**:
```
Spark Master UI:
  http://[VM2-PUBLIC-IP]:8081
  
  Should show:
    - 1 worker connected
    - 2 cores total
    - 10 GB RAM

Jupyter Notebook:
  http://[VM2-PUBLIC-IP]:8888
  
  Should show:
    - Jupyter file browser
    - scripts/ directory
    - New notebook button
```

---

## Step 13: Upload Data & Scripts

### Step 13.1: Upload Processing Scripts

**From your local machine**:

```bash
cd ~/Documents/Version_Control_For_Databases

# Upload to VM2
scp -i ~/.ssh/oracle-vm2.key -r scripts/* \
    ubuntu@[VM2-PUBLIC-IP]:/home/ubuntu/lakehouse/scripts/
```

**What you'll see**:
```
ingest_customers_spark.py          100%  5421   1.2MB/s
ingest_orders_spark.py             100%  5623   1.3MB/s
transform_customers_silver.py      100%  8234   1.4MB/s
...
```

---

### Step 13.2: Split Dataset by Month

**Onlocal machine**:

```bash
cd ~/Documents/Version_Control_For_Databases/data/firebolt-raw

# Create split script
cat > split_by_month.py << 'SPLITPY'
import pandas as pd
import os

print("Splitting transactions by month...")
chunk_size = 5_000_000  # 5M rows per chunk

month_files = {}

for chunk in pd.read_csv('transactions.csv', chunksize=chunk_size, 
                         parse_dates=['order_date']):
    for month in chunk['order_date'].dt.to_period('M').unique():
        month_str = str(month)
        filename = f'transactions_{month_str}.csv'
        
        month_data = chunk[chunk['order_date'].dt.to_period('M') == month]
        
        mode = 'a' if os.path.exists(filename) else 'w'
        header = not os.path.exists(filename)
        
        month_data.to_csv(filename, mode=mode, index=False, header=header)
        
        if filename not in month_files:
            month_files[filename] = 0
        month_files[filename] += len(month_data)
        
        print(f"{filename}: +{len(month_data):,} ({month_files[filename]:,} total)")

print("\n✓ Split complete!")
for filename, count in sorted(month_files.items()):
    print(f"{filename}: {count:,} records")
SPLITPY

# Run split (takes 10-15 minutes)
python3 split_by_month.py
```

**Expected output**:
```
Splitting transactions by month...
transactions_2019-10.csv: +60,123,456 records
transactions_2019-11.csv: +58,234,567 records
transactions_2019-12.csv: +62,345,678 records
transactions_2020-01.csv: +59,456,789 records
transactions_2020-02.csv: +55,567,890 records
transactions_2020-03.csv: +61,678,901 records
transactions_2020-04.csv: +54,789,012 records

✓ Split complete!
```

---

### Step 13.3: Upload to Oracle Storage

**Upload monthly files**:
```bash
# Configure endpoint shortcut
export ORACLE_ENDPOINT=https://objectstorage.us-ashburn-1.oraclecloud.com

# Upload first month (test)
aws s3 cp transactions_2019-10.csv s3://lakehouse-prod/raw/firebolt/ \
    --endpoint-url $ORACLE_ENDPOINT

# Monitor upload
# Expected time: 5-10 minutes per file
```

**Upload remaining months**:
```bash
for file in transactions_2019-*.csv transactions_2020-*.csv; do
    echo "Uploading $file..."
    aws s3 cp $file s3://lakehouse-prod/raw/firebolt/ \
        --endpoint-url $ORACLE_ENDPOINT
    echo "✓ $file uploaded"
done
```

**Upload other files**:
```bash
aws s3 cp users.csv s3://lakehouse-prod/raw/firebolt/ \
    --endpoint-url $ORACLE_ENDPOINT

aws s3 cp products.csv s3://lakehouse-prod/raw/firebolt/ \
    --endpoint-url $ORACLE_ENDPOINT

aws s3 cp sessions.csv s3://lakehouse-prod/raw/firebolt/ \
    --endpoint-url $ORACLE_ENDPOINT
```

**Verify all uploaded**:
```bash
aws s3 ls s3://lakehouse-prod/raw/firebolt/ \
    --endpoint-url $ORACLE_ENDPOINT \
    --human-readable

# Should show all files with sizes
```

---

## Step 14: Run Production Pipeline

### Step 14.1: Create Nessie Branches

**On VM2**:
```bash
ssh -i ~/.ssh/oracle-vm2.key ubuntu@[VM2-PUBLIC-IP]
cd /home/ubuntu/lakehouse

# Create branches script
docker exec spark-master python3 << 'CREATEBRANCHES'
import requests

NESSIE_URI = "http://10.0.0.4:19120/api/v1"

# Create branches
for branch in ['bronze', 'silver', 'gold']:
    resp = requests.post(
        f"{NESSIE_URI}/trees/branch/{branch}",
        json={"name": branch, "type": "BRANCH"}
    )
    print(f"✓ Created {branch}: {resp.status_code}")
CREATEBRANCHES
```

**Verify branches**:
```bash
# On VM1:
curl http://localhost:19120/api/v1/trees
```

---

### Step 14.2: Process Month-by-Month

**On VM2, create processing script**:
```bash
cat > process_month.sh << 'PROCSCRIPT'
#!/bin/bash
MONTH=$1

echo "========================================"
echo "Processing $MONTH"
echo "========================================"

# Bronze
echo "1. Bronze ingestion..."
docker exec spark-master python3 /home/jovyan/scripts/bronze/ingest_transactions.py --month=$MONTH

# Silver
echo "2. Silver transformation..."
docker exec spark-master python3 /home/jovyan/scripts/silver/transform_transactions.py --month=$MONTH

# Cleanup source
echo "3. Cleanup..."
aws s3 rm s3://lakehouse-prod/raw/firebolt/transactions_${MONTH}.csv \
    --endpoint-url https://objectstorage.us-ashburn-1.oraclecloud.com

echo "✓ $MONTH complete!"
PROCSCRIPT

chmod +x process_month.sh
```

**Process all months**:
```bash
for month in 2019-10 2019-11 2019-12 2020-01 2020-02 2020-03 2020-04; do
    ./process_month.sh $month
done
```

**Expected time**: 40-50 minutes per month = ~5-6 hours total

---

### Step 14.3: Run Gold & Promote

**After all months processed**:

```bash
# Gold aggregation
docker exec spark-master python3 /home/jovyan/scripts/gold/aggregate_customer_summary_gold.py

# Promote to production (on VM1)
ssh -i ~/.ssh/oracle-vm1.key ubuntu@[VM1-PUBLIC-IP]
cd /home/ubuntu/lakehouse
echo "yes" | python3 scripts/utils/promote_to_production.py
```

---

## ✅ Final Verification

**Check record counts**:
```bash
# On VM2:
docker exec -it spark-master pyspark

# In PySpark:
spark.sql("SELECT COUNT(*) FROM nessie.ecommerce.orders_bronze").show()
# Should show: 412,000,000

spark.sql("SELECT year_month, COUNT(*) FROM nessie.ecommerce.orders_bronze GROUP BY year_month ORDER BY year_month").show()
# Should show 7 months
```

---

## 🎉 Deployment Complete!

**You now have**:
```
✓ 412 million records processed
✓ Bronze → Silver → Gold → Production
✓ All services running
✓ Dashboards accessible
✓ Cost: $0/month
```

**Congratulations! Your production lakehouse is live!** 🚀

---

**Access your services**:
- Nessie API: `http://[VM1-IP]:19120`
- Airflow: `http://[VM1-IP]:8080`
- Spark UI: `http://[VM2-IP]:8081`
- Jupyter: `http://[VM2-IP]:8888`

**Ready for your project submission!** 🎓
