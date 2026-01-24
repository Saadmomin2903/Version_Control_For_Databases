# Cloud Migration Plan - Production Deployment

**Zero-Cost Production Lakehouse with Oracle Cloud + Supabase + Airflow + Grafana**

---

## 📋 Executive Summary

**Objective**: Migrate local development lakehouse to production cloud infrastructure at $0/month cost while maintaining enterprise-grade quality.

**Stack**:
- **Compute**: Oracle Cloud (Always Free - 2 VMs, 4 OCPU, 24 GB RAM)
- **Storage**: Oracle Object Storage (20 GB Free, S3-compatible)
- **Metadata DB**: Supabase PostgreSQL (500 MB Free)
- **Orchestration**: Apache Airflow 2.8.1
- **Monitoring**: Grafana Cloud (10k metrics/month)
- **Caching**: Upstash Redis (Optional, 256 MB)

**Timeline**: 2-3 weeks  
**Cost**: $0/month  
**Production-Grade**: ✅ Yes

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                  Oracle Cloud (Always Free)                     │
│                                                                 │
│  ┌──────────────────────┐  ┌───────────────────────────────┐   │
│  │  VM1: Control Plane  │  │  VM2: Processing Engine       │   │
│  │  2 OCPU, 12 GB RAM   │  │  2 OCPU, 12 GB RAM            │   │
│  │                      │  │                               │   │
│  │  • Airflow Web       │  │  • Spark Master               │   │
│  │  • Airflow Scheduler │  │  • Spark Worker               │   │
│  │  • Nessie Server     │  │  • Jupyter Notebook           │   │
│  │  • Nginx (SSL)       │  │                               │   │
│  └──────────────────────┘  └───────────────────────────────┘   │
│              │                          │                        │
│              └──────────┬───────────────┘                        │
│                         │                                        │
│              ┌──────────▼──────────┐                            │
│              │  Object Storage     │                            │
│              │  20 GB Free         │                            │
│              │  S3-Compatible API  │                            │
│              │  • Bronze parquet   │                            │
│              │  • Silver parquet   │                            │
│              │  • Gold parquet     │                            │
│              └─────────────────────┘                            │
└─────────────────────────────────────────────────────────────────┘
                         │
        ┌────────────────┴─────────────────┐
        │                                  │
┌───────▼────────┐              ┌──────────▼─────────┐
│  Supabase      │              │  Grafana Cloud     │
│  PostgreSQL    │              │  Free Tier         │
│                │              │                    │
│  • Nessie      │              │  • Dashboards      │
│    Metadata    │              │  • Alerts          │
│  • Catalog     │              │  • Logs            │
│  • Branches    │              │  • Metrics         │
│  • Commits     │              │                    │
└────────────────┘              └────────────────────┘
```

---

## 📅 Implementation Timeline

### **Week 1: Foundation Setup**
- Day 1-2: Oracle Cloud account + VM provisioning
- Day 3: Supabase + Grafana Cloud setup
- Day 4-5: VM1 configuration (Airflow + Nessie)
- Day 6-7: VM2 configuration (Spark cluster)

### **Week 2: Migration & Testing**
- Day 8-9: Migrate scripts and data
- Day 10-11: Airflow DAGs development
- Day 12-13: End-to-end testing
- Day 14: Production validation

### **Week 3: Monitoring & Optimization**
- Day 15-16: Grafana dashboards setup
- Day 17-18: Performance tuning
- Day 19-20: Documentation & handoff
- Day 21: Production go-live

---

## 🚀 Phase 1: Cloud Account Setup

### 1.1 Oracle Cloud Account

**Sign Up**: https://www.oracle.com/cloud/free/

**Resources to Provision**:

```yaml
Compute:
  VM1 (airflow-nessie):
    Shape: VM.Standard.A1.Flex
    OCPU: 2
    Memory: 12 GB
    Boot Volume: 50 GB
    OS: Ubuntu 22.04 LTS (ARM64)
    
  VM2 (spark-cluster):
    Shape: VM.Standard.A1.Flex
    OCPU: 2
    Memory: 12 GB
    Boot Volume: 50 GB
    OS: Ubuntu 22.04 LTS (ARM64)

Storage:
  Object Storage:
    Bucket: lakehouse-prod
    Tier: Standard
    Encryption: Oracle-Managed
    Size: 20 GB (free tier limit)

Network:
  VCN: lakehouse-vcn
  Subnet: public-subnet (10.0.0.0/24)
  Security List:
    - Ingress: 22 (SSH), 8080 (Airflow), 19120 (Nessie), 443 (HTTPS)
    - Egress: All traffic
```

**Setup Steps**:
```bash
# 1. Create VCN
OCI Console → Networking → Virtual Cloud Networks → Create VCN
Name: lakehouse-vcn
CIDR: 10.0.0.0/16

# 2. Create Compute Instances
OCI Console → Compute → Instances → Create Instance
- Select Always Free eligible shape
- Download SSH key pair
- Note public IP addresses

# 3. Create Object Storage Bucket
OCI Console → Storage → Buckets → Create Bucket
- Enable versioning
- Enable auto-tiering (optional)

# 4. Generate API Keys for S3 access
OCI Console → User Settings → API Keys → Add API Key
- Download Customer Secret Keys
- Save Access Key and Secret Key
```

---

### 1.2 Supabase Setup

**Sign Up**: https://supabase.com/

**Create Project**:
```yaml
Project Name: lakehouse-nessie-metadata
Database Password: [strong-password]
Region: [closest to Oracle Cloud region]
Plan: Free (500 MB PostgreSQL)
```

**Connection Details**:
```bash
Host: db.xxxxxxxxxxxxx.supabase.co
Port: 5432
Database: postgres
User: postgres
Password: [your-password]
Connection String: postgresql://postgres:[password]@db.xxxxx.supabase.co:5432/postgres?sslmode=require
```

**Test Connection**:
```bash
psql "postgresql://postgres:[password]@db.xxxxx.supabase.co:5432/postgres?sslmode=require"
\l  # List databases
\dt # List tables (will be empty initially)
```

---

### 1.3 Grafana Cloud Setup

**Sign Up**: https://grafana.com/auth/sign-up/create-user

**Create Stack**:
```yaml
Stack Name: lakehouse-monitoring
Region: [closest to Oracle Cloud]
Plan: Free (10k metrics, 50 GB logs)
```

**Get Configuration**:
```bash
# Prometheus Remote Write URL
https://prometheus-prod-XX-prod-XX.grafana.net/api/prom/push

# Grafana Instance URL
https://yourcompanyname.grafana.net

# Get API Key
Grafana Cloud → Configuration → API Keys → Create API Key
```

---

## 🔧 Phase 2: VM Configuration

### 2.1 VM1 Setup (Airflow + Nessie)

**Initial Setup**:
```bash
# SSH into VM1
ssh -i ~/.ssh/oracle_key ubuntu@[vm1-public-ip]

# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
sudo apt install -y docker.io docker-compose-plugin git curl
sudo usermod -aG docker ubuntu
newgrp docker

# Install monitoring agent
curl -O https://grafana.com/api/agent/download
sudo ./install-agent.sh

# Clone repository
cd /home/ubuntu
git clone https://github.com/yourusername/lakehouse.git
cd lakehouse
```

**Docker Compose Configuration**:

Create `docker-compose-prod.yml`:
```yaml
version: '3.8'

x-airflow-common:
  &airflow-common
  image: apache/airflow:2.8.1-python3.11
  environment: &airflow-common-env
    AIRFLOW__CORE__EXECUTOR: LocalExecutor
    AIRFLOW__DATABASE__SQL_ALCHEMY_CONN: postgresql+psycopg2://postgres:${SUPABASE_PASSWORD}@db.xxxxx.supabase.co:5432/postgres
    AIRFLOW__CORE__FERNET_KEY: ${AIRFLOW_FERNET_KEY}
    AIRFLOW__CORE__DAGS_ARE_PAUSED_AT_CREATION: 'true'
    AIRFLOW__CORE__LOAD_EXAMPLES: 'false'
    AIRFLOW__WEBSERVER__EXPOSE_CONFIG: 'true'
    AIRFLOW__WEBSERVER__RBAC: 'true'
    AIRFLOW__API__AUTH_BACKENDS: 'airflow.api.auth.backend.basic_auth'
    # Custom configs
    SPARK_MASTER_URL: spark://[vm2-private-ip]:7077
    NESSIE_URI: http://nessie:19120/api/v1
  volumes:
    - ./airflow/dags:/opt/airflow/dags
    - ./airflow/logs:/opt/airflow/logs
    - ./airflow/plugins:/opt/airflow/plugins
    - ./airflow/config:/opt/airflow/config
    - ./scripts:/opt/airflow/scripts
  user: "${AIRFLOW_UID:-50000}:0"
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
      - QUARKUS_DATASOURCE_JDBC_URL=jdbc:postgresql://db.xxxxx.supabase.co:5432/postgres?sslmode=require
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
    restart: always

  airflow-scheduler:
    <<: *airflow-common
    container_name: airflow-scheduler
    command: scheduler
    healthcheck:
      test: ["CMD-SHELL", 'airflow jobs check --job-type SchedulerJob']
      interval: 30s
      timeout: 10s
      retries: 5
    restart: always

  airflow-init:
    <<: *airflow-common
    container_name: airflow-init
    entrypoint: /bin/bash
    command:
      - -c
      - |
        mkdir -p /sources/logs /sources/dags /sources/plugins /sources/config
        chown -R "${AIRFLOW_UID}:0" /sources/{logs,dags,plugins,config}
        exec /entrypoint airflow version
    environment:
      <<: *airflow-common-env
    user: "0:0"
    volumes:
      - ./airflow:/sources

networks:
  default:
    name: lakehouse-network
```

**Environment Configuration**:

Create `.env.prod`:
```bash
# Supabase
SUPABASE_PASSWORD=your-strong-password

# Airflow
AIRFLOW_UID=50000
AIRFLOW_FERNET_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")

# Oracle Cloud
ORACLE_ACCESS_KEY=your-oracle-access-key
ORACLE_SECRET_KEY=your-oracle-secret-key
ORACLE_NAMESPACE=your-oracle-namespace
ORACLE_REGION=us-ashburn-1

# Grafana
GRAFANA_API_KEY=your-grafana-api-key
GRAFANA_PROMETHEUS_URL=https://prometheus-prod-XX.grafana.net/api/prom/push
```

**Directory Structure**:
```bash
mkdir -p airflow/{dags,logs,plugins,config}
chmod -R 755 airflow
```

**Start Services**:
```bash
# Initialize Airflow
docker compose -f docker-compose-prod.yml up airflow-init

# Start all services
docker compose -f docker-compose-prod.yml up -d

# Check status
docker compose -f docker-compose-prod.yml ps

# View logs
docker compose -f docker-compose-prod.yml logs -f
```

**Access Airflow**:
```
URL: http://[vm1-public-ip]:8080
Username: admin
Password: admin (change immediately!)
```

---

### 2.2 VM2 Setup (Spark Cluster)

**Initial Setup**:
```bash
# SSH into VM2
ssh -i ~/.ssh/oracle_key ubuntu@[vm2-public-ip]

# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
sudo apt install -y docker.io git
sudo usermod -aG docker ubuntu
newgrp docker

# Clone repository
cd /home/ubuntu
git clone https://github.com/yourusername/lakehouse.git
cd lakehouse
```

**Spark Docker Compose**:

Create `docker-compose-spark.yml`:
```yaml
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
      - SPARK_MASTER_HOST=spark-master
      - SPARK_MASTER_PORT=7077
      - SPARK_MASTER_WEBUI_PORT=8080
      # Oracle Object Storage (S3-compatible)
      - AWS_ACCESS_KEY_ID=${ORACLE_ACCESS_KEY}
      - AWS_SECRET_ACCESS_KEY=${ORACLE_SECRET_KEY}
      - AWS_S3_ENDPOINT=https://objectstorage.${ORACLE_REGION}.oraclecloud.com
      - AWS_REGION=${ORACLE_REGION}
      # Nessie
      - NESSIE_URI=http://[vm1-private-ip]:19120/api/v1
      - WAREHOUSE=oci://${ORACLE_NAMESPACE}/lakehouse-prod/warehouse
      # Memory
      - SPARK_DRIVER_MEMORY=4g
      - SPARK_EXECUTOR_MEMORY=8g
    volumes:
      - ./scripts:/home/jovyan/scripts
      - ./data:/home/jovyan/data
      - ./airflow/dags:/home/jovyan/dags
    restart: always
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080"]
      interval: 30s
      timeout: 10s
      retries: 3

  spark-worker:
    image: alexmerced/spark33-notebook
    container_name: spark-worker
    hostname: spark-worker
    environment:
      - SPARK_MODE=worker
      - SPARK_MASTER_URL=spark://spark-master:7077
      - SPARK_WORKER_CORES=2
      - SPARK_WORKER_MEMORY=10G
      - SPARK_EXECUTOR_MEMORY=8G
    depends_on:
      - spark-master
    restart: always

networks:
  default:
    name: spark-network
```

**Create `.env.spark`**:
```bash
ORACLE_ACCESS_KEY=your-access-key
ORACLE_SECRET_KEY=your-secret-key
ORACLE_NAMESPACE=your-namespace
ORACLE_REGION=us-ashburn-1
```

**Start Spark**:
```bash
docker compose -f docker-compose-spark.yml up -d

# Verify
docker ps
docker logs spark-master
docker logs spark-worker
```

**Test Spark**:
```bash
# Access Jupyter
http://[vm2-public-ip]:8888

# Access Spark UI
http://[vm2-public-ip]:8081
```

---

## 📊 Phase 3: Grafana Monitoring Setup

### 3.1 Install Grafana Agent

**On VM1**:
```bash
# Download and install
wget https://github.com/grafana/agent/releases/latest/download/grafana-agent-linux-arm64.zip
unzip grafana-agent-linux-arm64.zip
sudo mv grafana-agent /usr/local/bin/
sudo chmod +x /usr/local/bin/grafana-agent

# Create config
sudo mkdir -p /etc/grafana-agent
sudo nano /etc/grafana-agent/config.yaml
```

**Agent Configuration** (`/etc/grafana-agent/config.yaml`):
```yaml
server:
  log_level: info

metrics:
  global:
    scrape_interval: 60s
    remote_write:
      - url: https://prometheus-prod-XX.grafana.net/api/prom/push
        basic_auth:
          username: YOUR_INSTANCE_ID
          password: YOUR_API_KEY

  configs:
    - name: lakehouse-metrics
      scrape_configs:
        # Nessie metrics
        - job_name: 'nessie'
          static_configs:
            - targets: ['localhost:19120']
        
        # Airflow metrics
        - job_name: 'airflow'
          static_configs:
            - targets: ['localhost:8080']
        
        # Docker metrics
        - job_name: 'docker'
          static_configs:
            - targets: ['localhost:9323']

logs:
  configs:
    - name: lakehouse-logs
      clients:
        - url: https://logs-prod-XX.grafana.net/loki/api/v1/push
          basic_auth:
            username: YOUR_INSTANCE_ID
            password: YOUR_API_KEY
      positions:
        filename: /tmp/positions.yaml
      scrape_configs:
        - job_name: docker
          docker_sd_configs:
            - host: unix:///var/run/docker.sock
          relabel_configs:
            - source_labels: ['__meta_docker_container_name']
              target_label: 'container'
```

**Start Agent**:
```bash
# Create systemd service
sudo nano /etc/systemd/system/grafana-agent.service
```

```ini
[Unit]
Description=Grafana Agent
After=network-online.target

[Service]
ExecStart=/usr/local/bin/grafana-agent -config.file=/etc/grafana-agent/config.yaml
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable grafana-agent
sudo systemctl start grafana-agent
sudo systemctl status grafana-agent
```

---

### 3.2 Grafana Dashboards

**Import Pre-Built Dashboards**:

1. **Airflow Dashboard** (ID: 12250)
2. **Docker Dashboard** (ID: 193)
3. **Node Exporter** (ID: 1860)

**Custom Lakehouse Dashboard**:

Create in Grafana UI with panels for:
- Records processed (bronze/silver/gold)
- Pipeline execution time
- Data quality scores
- Branch metrics (commits, merges)
- Storage usage
- Error rates

**Alert Rules**:
```yaml
alerts:
  - name: Pipeline Failure
    condition: pipeline_failed == 1
    for: 5m
    annotations:
      summary: "Lakehouse pipeline failed"
    
  - name: High Error Rate
    condition: error_rate > 0.05
    for: 10m
    annotations:
      summary: "Data quality issues detected"
  
  - name: Storage Usage
    condition: storage_used > 18GB
    for: 1h
    annotations:
      summary: "Approaching storage limit"
```

---

## 🔄 Phase 4 Airflow DAGs Development

### 4.1 Production Pipeline DAG

Create `airflow/dags/lakehouse_production.py`:

```python
from airflow import DAG
from airflow.providers.ssh.operators.ssh import SSHOperator
from airflow.operators.python import PythonOperator, BranchPythonOperator
from airflow.operators.email import EmailOperator
from airflow.sensors.external_task import ExternalTaskSensor
from airflow.utils.task_group import TaskGroup
from datetime import datetime, timedelta
import requests
import logging

logger = logging.getLogger(__name__)

default_args = {
    'owner': 'data-engineering',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email': ['alerts@yourcompany.com'],
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
    'execution_timeout': timedelta(hours=2),
}

dag = DAG(
    'lakehouse_production_pipeline',
    default_args=default_args,
    description='Production lakehouse pipeline with quality gates',
    schedule_interval='0 2 * * *',  # 2 AM daily
    max_active_runs=1,
    catchup=False,
    tags=['production', 'lakehouse', 'medallion'],
)

# Helper functions
def check_nessie_health():
    """Verify Nessie is healthy before starting"""
    response = requests.get('http://[vm1-ip]:19120/api/v1/config')
    if response.status_code != 200:
        raise Exception("Nessie is not healthy!")
    logger.info("Nessie health check passed")
    return True

def validate_gold_quality(**context):
    """Quality gate before production promotion"""
    # Check table exists
    response = requests.get('http://[vm1-ip]:19120/api/v1/trees/tree/gold/entries')
    tables = [e for e in response.json().get('entries', []) if e['type'] == 'ICEBERG_TABLE']
    
    if len(tables) < 1:
        raise ValueError("No tables in gold branch!")
    
    # Add more quality checks here
    logger.info(f"Quality gate passed: {len(tables)} tables in gold")
    return 'promote_to_production'

def send_success_notification(**context):
    """Send success notification"""
    logger.info("Pipeline completed successfully!")
    # Add Slack/Discord webhook here
    return True

# Tasks
with TaskGroup('setup', dag=dag) as setup:
    health_check = PythonOperator(
        task_id='nessie_health_check',
        python_callable=check_nessie_health,
    )
    
    create_branches = SSHOperator(
        task_id='create_branches',
        ssh_conn_id='oracle_vm1',
        command='cd /home/ubuntu/lakehouse && python3 scripts/utils/create_nessie_branches.py',
    )
    
    health_check >> create_branches

with TaskGroup('bronze_ingestion', dag=dag) as bronze:
    ingest_orders = SSHOperator(
        task_id='ingest_orders',
        ssh_conn_id='oracle_vm2',
        command='docker exec spark-master python3 /home/jovyan/scripts/bronze/ingest_orders_spark.py',
    )
    
    ingest_customers = SSHOperator(
        task_id='ingest_customers',
        ssh_conn_id='oracle_vm2',
        command='docker exec spark-master python3 /home/jovyan/scripts/bronze/ingest_customers_spark.py',
    )

with TaskGroup('silver_transformation', dag=dag) as silver:
    transform_orders = SSHOperator(
        task_id='transform_orders',
        ssh_conn_id='oracle_vm2',
        command='docker exec spark-master python3 /home/jovyan/scripts/silver/transform_orders_silver.py',
    )
    
    transform_customers = SSHOperator(
        task_id='transform_customers',
        ssh_conn_id='oracle_vm2',
        command='docker exec spark-master python3 /home/jovyan/scripts/silver/transform_customers_silver.py',
    )

with TaskGroup('gold_aggregation', dag=dag) as gold:
    aggregate = SSHOperator(
        task_id='aggregate_customer_summary',
        ssh_conn_id='oracle_vm2',
        command='docker exec spark-master python3 /home/jovyan/scripts/gold/aggregate_customer_summary_gold.py',
    )

quality_gate = BranchPythonOperator(
    task_id='quality_gate',
    python_callable=validate_gold_quality,
    dag=dag,
)

promote = SSHOperator(
    task_id='promote_to_production',
    ssh_conn_id='oracle_vm1',
    command='cd /home/ubuntu/lakehouse && echo "yes" | python3 scripts/utils/promote_to_production.py',
    dag=dag,
)

notify = PythonOperator(
    task_id='send_notification',
    python_callable=send_success_notification,
    dag=dag,
)

# Define pipeline
setup >> bronze >> silver >> gold >> quality_gate >> promote >> notify
```

---

## ✅ Phase 5: Testing & Validation

### 5.1 Pre-Production Checklist

```bash
# 1. Test Nessie connection
curl http://[vm1-ip]:19120/api/v1/config

# 2. Test Supabase connection
psql "postgresql://postgres:[password]@db.xxxxx.supabase.co:5432/postgres?sslmode=require" -c "\dt"

# 3. Test Oracle Object Storage
aws s3 --endpoint-url https://objectstorage.[region].oraclecloud.com ls

# 4. Test Spark cluster
docker exec spark-master pyspark --version

# 5. Test Airflow
curl http://[vm1-ip]:8080/health

# 6. Run end-to-end test
./test_e2e.sh
```

### 5.2 Performance Benchmarks

**Target Metrics**:
```yaml
Bronze Layer:
  - 1M records ingestion: < 5 minutes
  
Silver Layer:
  - Transformation + quality: < 10 minutes
  
Gold Layer:
  - Aggregation: < 5 minutes
  
Total Pipeline:  
  - End-to-end: < 25 minutes
  - Success rate: > 99%
```

---

## 📊 Cost Analysis

### Monthly Cost Breakdown

| Service | Plan | Monthly Cost | Annual Cost |
|---------|------|--------------|-------------|
| **Oracle Cloud VMs (2x)** | Always Free | $0 | $0 |
| **Oracle Object Storage** | 20 GB Free | $0 | $0 |
| **Supabase PostgreSQL** | 500 MB Free | $0 | $0 |
| **Grafana Cloud** | Free Tier | $0 | $0 |
| **Upstash Redis** | 256 MB Free | $0 | $0 |
| **Domain (optional)** | Freenom/Cloudflare | $0 | $0 |
| **SSL Certificate** | Let's Encrypt | $0 | $0 |
| **Total** | - | **$0** | **$0** |

**Hidden Costs**: ⚠️ None! Completely free.

**Scaling Costs** (if you exceed free tier):
```yaml
Oracle Cloud:
  - Additional Compute: ~$0.01/OCPU-hour
  - Additional Storage: ~$0.0255/GB-month
  
Supabase:
  - Pro Plan: $25/month (8 GB database)
  
Grafana Cloud:
  - Pay-as-you-go: $0.18/GB logs
```

---

## 🔒 Security Checklist

```yaml
Network:
  ✓ Firewall rules configured
  ✓ Only necessary ports exposed
  ✓ VPN/Bastion host for SSH (optional)

Authentication:
  ✓ Strong passwords (20+ characters)
  ✓ SSH key-based authentication
  ✓ Airflow RBAC enabled
  ✓ Nessie authentication (if needed)

Encryption:
  ✓ SSL/TLS for all connections
  ✓ Data at rest encryption
  ✓ Secrets in environment variables

Monitoring:
  ✓ Failed login attempts logged
  ✓ Unusual activity alerts
  ✓ Resource usage monitoring
```

---

## 📈 Success Metrics

**After 1 Month**:
- [ ] 100% pipeline reliability
- [ ] < 30 minute end-to-end execution
- [ ] Zero data quality incidents
- [ ] < 50% resource utilization

**After 3 Months**:
- [ ] Processing 1M+ records/day
- [ ] < 1% error rate
- [ ] Automated monitoring & alerting
- [ ] Full documentation

---

## 🎯 Next Steps

1. **Week 1**: Complete Oracle + Supabase setup
2. **Week 2**: Deploy Airflow + Spark
3. **Week 3**: Production testing + monitoring
4. **Week 4**: Go-live with real data

**Ready to start?** Begin with Phase 1: Oracle Cloud account creation!

---

**Document Version**: 1.0  
**Last Updated**: 2026-01-19  
**Owner**: Data Engineering Team  
**Status**: Ready for Implementation
