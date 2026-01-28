# 🚀 Lakehouse Project - Complete Implementation Roadmap

**Project**: Version Control for Databases  
**Team**: Data Engineering + ML  
**Date**: 2026-01-25  
**Status**: Multi-VM Spark Cluster ✅ Operational

---

## 📋 Table of Contents

1. [Current State](#current-state)
2. [Phase 1: Data Quality & Validation](#phase-1-data-quality--validation)
3. [Phase 2: Orchestration with Airflow](#phase-2-orchestration-with-airflow)
4. [Phase 3: Query Engine with Trino](#phase-3-query-engine-with-trino)
5. [Phase 4: Observability Stack](#phase-4-observability-stack)
6. [Phase 5: Metadata & Governance](#phase-5-metadata--governance)
7. [Phase 6: BI Dashboards](#phase-6-bi-dashboards)
8. [Phase 7: ML Team Integration](#phase-7-ml-team-integration)
9. [VM Allocation Strategy](#vm-allocation-strategy)

---

## Current State

### ✅ What's Already Working

| Component | VM | Status |
|-----------|-----|--------|
| Spark Master | VM1 (10.0.0.148) | ✅ Running (Gold Build Active) |
| Spark Worker | VM2 (10.0.0.108) | ✅ Running (300M Records in Shuffle) |
| Nessie Catalog | VM1 | ✅ Running (19120) - Main/Gold Active |
| Bronze Layer | Iceberg | ✅ Complete (301,758,993 Records) |
| Silver Layer | Iceberg | ✅ Complete (300,298,449 Records) |
| Notebooks | VM2 | ✅ Interactive Medallion Tutorials Live |
| Gold Layer | Iceberg | 🔄 ACTIVE: Production Aggregations |

### 🔧 Network Configuration

```
VM1 (10.0.0.148): network_mode: host, ports 7077, 8080, 8888, 19120
VM2 (10.0.0.108): network_mode: host, ports 8081, 8082
Firewall: Ports 7077, 30000-50000 open between VMs
```

---

## Phase 1: Data Quality & Validation

### 📦 Service: Great Expectations

**Purpose**: Validate data quality at each layer merge

### Step 1.1: Install Great Expectations on VM1

```bash
# SSH to VM1
ssh -i ~/.ssh/oracle-vm1.key ubuntu@140.238.224.207

# Enter Spark container
docker exec -it lakehouse-spark bash

# Install Great Expectations
pip install great_expectations

# Initialize
great_expectations init
```

### Step 1.2: Create Expectation Suite for Silver Layer

Create file: `scripts/quality/silver_expectations.py`

```python
import great_expectations as gx
from great_expectations.core.batch import RuntimeBatchRequest

def validate_silver_orders(spark_df):
    """Validate Silver layer orders before merge"""
    
    context = gx.get_context()
    
    # Create expectation suite
    suite = context.add_or_update_expectation_suite("silver_orders_suite")
    
    # Define expectations
    expectations = [
        # No null order_ids
        {"expectation_type": "expect_column_values_to_not_be_null",
         "kwargs": {"column": "order_id"}},
        
        # No null customer_ids  
        {"expectation_type": "expect_column_values_to_not_be_null",
         "kwargs": {"column": "customer_id"}},
        
        # Positive prices
        {"expectation_type": "expect_column_values_to_be_between",
         "kwargs": {"column": "price", "min_value": 0}},
        
        # Valid order dates
        {"expectation_type": "expect_column_values_to_not_be_null",
         "kwargs": {"column": "order_date"}},
        
        # Row count sanity check (not dropping >50%)
        {"expectation_type": "expect_table_row_count_to_be_between",
         "kwargs": {"min_value": 1000}}
    ]
    
    # Add expectations to suite
    for exp in expectations:
        suite.add_expectation(gx.expectations.ExpectationConfiguration(**exp))
    
    # Validate
    results = context.run_validation_operator(
        "action_list_operator",
        assets_to_validate=[batch],
        run_id="silver_validation"
    )
    
    return results["success"]
```

### Step 1.3: Integrate with WAP Pattern

Update `scripts/silver/build_silver_layer.py`:

```python
from quality.silver_expectations import validate_silver_orders

# After transformation, before merge
if validate_silver_orders(transformed_df):
    # Write to Silver branch
    transformed_df.writeTo("nessie.ecommerce_silver.orders").append()
    print("✅ Validation passed, data written to Silver")
else:
    raise Exception("❌ Data quality validation failed!")
```

---

## Phase 2: Orchestration with Airflow

### 📦 Service: Apache Airflow

**Purpose**: Orchestrate Bronze → Silver → Gold pipelines

### Step 2.1: Add Airflow to VM1 docker-compose

Add to `docker-compose-production.yml`:

```yaml
  # Airflow Webserver
  airflow-webserver:
    image: apache/airflow:2.8.0
    container_name: lakehouse-airflow
    network_mode: host
    environment:
      - AIRFLOW__CORE__EXECUTOR=LocalExecutor
      - AIRFLOW__DATABASE__SQL_ALCHEMY_CONN=${SUPABASE_JDBC_URL}
      - AIRFLOW__CORE__LOAD_EXAMPLES=False
      - AIRFLOW__WEBSERVER__SECRET_KEY=your-secret-key
    volumes:
      - ./airflow/dags:/opt/airflow/dags
      - ./scripts:/opt/airflow/scripts
      - /var/run/docker.sock:/var/run/docker.sock
    ports:
      - "8089:8080"  # Airflow UI
    command: >
      bash -c "airflow db init &&
               airflow users create --username admin --password admin --firstname Admin --lastname User --role Admin --email admin@example.com &&
               airflow webserver"
    restart: unless-stopped
    
  airflow-scheduler:
    image: apache/airflow:2.8.0
    container_name: lakehouse-airflow-scheduler
    network_mode: host
    environment:
      - AIRFLOW__CORE__EXECUTOR=LocalExecutor
      - AIRFLOW__DATABASE__SQL_ALCHEMY_CONN=${SUPABASE_JDBC_URL}
    volumes:
      - ./airflow/dags:/opt/airflow/dags
      - ./scripts:/opt/airflow/scripts
      - /var/run/docker.sock:/var/run/docker.sock
    command: airflow scheduler
    restart: unless-stopped
```

### Step 2.2: Create Medallion Pipeline DAG

Create file: `airflow/dags/medallion_pipeline.py`

```python
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta

default_args = {
    'owner': 'lakehouse',
    'depends_on_past': False,
    'start_date': datetime(2026, 1, 1),
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'medallion_pipeline',
    default_args=default_args,
    description='Bronze → Silver → Gold ETL Pipeline',
    schedule_interval='@daily',
    catchup=False,
)

# Task 1: Build Bronze Layer
bronze_task = BashOperator(
    task_id='build_bronze_layer',
    bash_command='docker exec lakehouse-spark python3 /home/jovyan/scripts/bronze/build_bronze_layer.py',
    dag=dag,
)

# Task 2: Build Silver Layer (with quality validation)
silver_task = BashOperator(
    task_id='build_silver_layer',
    bash_command='docker exec lakehouse-spark python3 /home/jovyan/scripts/silver/build_silver_layer.py',
    dag=dag,
)

# Task 3: Build Gold Layer
gold_task = BashOperator(
    task_id='build_gold_layer',
    bash_command='docker exec lakehouse-spark python3 /home/jovyan/scripts/gold/build_gold_layer.py',
    dag=dag,
)

# Task 4: Send Slack notification
notify_task = BashOperator(
    task_id='notify_completion',
    bash_command='curl -X POST -H "Content-Type: application/json" -d \'{"text":"✅ Medallion pipeline completed!"}\' ${SLACK_WEBHOOK_URL}',
    dag=dag,
)

# Dependencies
bronze_task >> silver_task >> gold_task >> notify_task
```

### Step 2.3: Deploy Airflow

```bash
# On VM1
cd ~/Version_Control_For_Databases
mkdir -p airflow/dags
# Copy DAG file
docker-compose -f docker-compose-production.yml up -d airflow-webserver airflow-scheduler

# Access UI: http://140.238.224.207:8089
```

---

## Phase 3: Query Engine with Trino

### 📦 Service: Trino

**Purpose**: SQL queries for analysts, BI tools, ML feature extraction

### Step 3.1: Add Trino to VM1 or VM2

Create `docker-compose-trino.yml`:

```yaml
version: '3.8'

services:
  trino:
    image: trinodb/trino:435
    container_name: lakehouse-trino
    network_mode: host
    volumes:
      - ./trino/catalog:/etc/trino/catalog
      - ./trino/config:/etc/trino
    ports:
      - "8085:8080"  # Trino UI
    environment:
      - TRINO_COORDINATOR=true
    restart: unless-stopped
```

### Step 3.2: Configure Iceberg + Nessie Catalog

Create `trino/catalog/iceberg.properties`:

```properties
connector.name=iceberg
iceberg.catalog.type=nessie
iceberg.nessie.uri=http://10.0.0.148:19120/api/v1
iceberg.nessie.ref=main
iceberg.nessie.default-warehouse-dir=s3a://lakehouse-prod/warehouse
iceberg.file-format=PARQUET

# S3 / Oracle Object Storage
fs.native-s3.enabled=true
s3.endpoint=https://axqryfqntzfy.compat.objectstorage.ap-mumbai-1.oraclecloud.com
s3.region=ap-mumbai-1
s3.aws-access-key=${ORACLE_ACCESS_KEY}
s3.aws-secret-key=${ORACLE_SECRET_KEY}
s3.path-style-access=true
```

### Step 3.3: Query Data with Trino

```bash
# Start Trino CLI
docker exec -it lakehouse-trino trino

# Query Iceberg tables
SHOW CATALOGS;
USE iceberg.ecommerce_gold;
SHOW TABLES;

-- Query Gold layer
SELECT * FROM daily_sales_summary LIMIT 10;

-- Time travel query
SELECT * FROM daily_sales_summary 
FOR VERSION AS OF 'commit_hash_here';

-- Query specific Nessie branch
SET SESSION iceberg.nessie_ref = 'silver';
SELECT * FROM iceberg.ecommerce_silver.orders LIMIT 10;
```

---

## Phase 4: Observability Stack

### 📦 Services: Prometheus + Grafana

**Purpose**: Monitor DAGs, job durations, data volumes

### Step 4.1: Add Prometheus & Grafana

Create `docker-compose-monitoring.yml`:

```yaml
version: '3.8'

services:
  prometheus:
    image: prom/prometheus:v2.48.0
    container_name: lakehouse-prometheus
    network_mode: host
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
    ports:
      - "9090:9090"
    restart: unless-stopped

  grafana:
    image: grafana/grafana:10.2.2
    container_name: lakehouse-grafana
    network_mode: host
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin123
    volumes:
      - grafana-data:/var/lib/grafana
    ports:
      - "3000:3000"
    restart: unless-stopped

volumes:
  grafana-data:
```

### Step 4.2: Configure Prometheus Targets

Create `monitoring/prometheus.yml`:

```yaml
global:
  scrape_interval: 15s

scrape_configs:
  # Spark Master metrics
  - job_name: 'spark-master'
    static_configs:
      - targets: ['10.0.0.148:4040']

  # Spark Worker metrics
  - job_name: 'spark-worker'
    static_configs:
      - targets: ['10.0.0.108:8081']

  # Airflow metrics
  - job_name: 'airflow'
    static_configs:
      - targets: ['10.0.0.148:8089']

  # Custom lakehouse metrics
  - job_name: 'lakehouse-metrics'
    static_configs:
      - targets: ['10.0.0.148:9091']
```

### Step 4.3: Custom Metrics Exporter

Create `scripts/metrics/exporter.py`:

```python
from prometheus_client import start_http_server, Gauge
import time

# Define metrics
ROW_COUNT = Gauge('lakehouse_table_row_count', 'Row count per table', ['table', 'layer'])
NULL_PERCENTAGE = Gauge('lakehouse_null_percentage', 'Null % per column', ['table', 'column'])
LAST_COMMIT_TS = Gauge('lakehouse_last_commit_timestamp', 'Last Nessie commit', ['branch'])
JOB_DURATION = Gauge('lakehouse_job_duration_seconds', 'ETL job duration', ['job_name'])

def collect_metrics():
    """Collect and expose metrics"""
    # Query Spark/Iceberg for table stats
    # Update Prometheus gauges
    ROW_COUNT.labels(table='orders', layer='gold').set(100000)
    
if __name__ == '__main__':
    start_http_server(9091)
    while True:
        collect_metrics()
        time.sleep(60)
```

### Step 4.4: Import Grafana Dashboards

Access Grafana: `http://140.238.224.207:3000`

1. Login (admin/admin123)
2. Add Prometheus data source
3. Import dashboards:
   - Spark Dashboard: ID 7890
   - Airflow Dashboard: ID 14050

---

## Phase 5: Metadata & Governance

### 📦 Service: OpenMetadata

**Purpose**: Data lineage, ownership, PII tagging

### Step 5.1: Deploy OpenMetadata

```yaml
# docker-compose-metadata.yml
version: '3.8'

services:
  openmetadata:
    image: openmetadata/server:1.3.0
    container_name: lakehouse-openmetadata
    network_mode: host
    environment:
      - DB_HOST=db.xxxxx.supabase.co
      - DB_PORT=5432
      - DB_USER=postgres
      - DB_PASSWORD=${SUPABASE_PASSWORD}
    ports:
      - "8585:8585"
    restart: unless-stopped
```

### Step 5.2: Configure Iceberg Connector

In OpenMetadata UI:
1. Add Service → Iceberg
2. Configure Nessie catalog connection
3. Run metadata ingestion

### Step 5.3: Add Data Lineage

Track:
- Bronze → Silver transformations
- Silver → Gold aggregations
- Column-level lineage

---

## Phase 6: BI Dashboards

### 📦 Service: Apache Superset

**Purpose**: Visualize Gold layer for business users

### Step 6.1: Deploy Superset

```yaml
# docker-compose-bi.yml
version: '3.8'

services:
  superset:
    image: apache/superset:3.0.0
    container_name: lakehouse-superset
    network_mode: host
    environment:
      - SUPERSET_SECRET_KEY=your-secret-key
    ports:
      - "8088:8088"
    command: >
      bash -c "superset db upgrade &&
               superset fab create-admin --username admin --password admin123 --firstname Admin --lastname User --email admin@example.com &&
               superset init &&
               superset run -h 0.0.0.0 -p 8088"
    restart: unless-stopped
```

### Step 6.2: Connect to Trino

1. Access: `http://140.238.224.207:8088`
2. Add Database → Trino
3. Connection string: `trino://trino:10.0.0.148:8085/iceberg/ecommerce_gold`

### Step 6.3: Create Dashboards

- Daily Sales Summary
- Product Performance
- Customer Insights

---

## Phase 7: ML Team Integration

### 🧠 How ML Team Accesses the Lakehouse

This section is **critical for showcasing Nessie + Iceberg benefits to ML**.

### 7.1: Feature Engineering Workflow

```
┌─────────────────────────────────────────────────────────────┐
│                    ML TEAM WORKFLOW                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   1. Create feature branch from main                         │
│      ↓                                                       │
│   2. Read Gold layer tables                                  │
│      ↓                                                       │
│   3. Create ML features (transform, aggregate)               │
│      ↓                                                       │
│   4. Write features to feature_store schema                  │
│      ↓                                                       │
│   5. Train model on versioned features                       │
│      ↓                                                       │
│   6. If model performs well → merge to main                  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 7.2: Python SDK for ML Access

Create `scripts/ml/lakehouse_client.py`:

```python
"""
ML Team Lakehouse Client
Provides easy access to versioned data for feature engineering and model training.
"""

from pyspark.sql import SparkSession
import os

class LakehouseClient:
    """Client for ML team to access versioned lakehouse data"""
    
    def __init__(self, branch: str = "main"):
        self.branch = branch
        self.spark = self._create_spark_session()
    
    def _create_spark_session(self) -> SparkSession:
        """Create Spark session connected to Nessie + Iceberg"""
        return SparkSession.builder \
            .appName(f"ML-{self.branch}") \
            .config("spark.master", "spark://10.0.0.148:7077") \
            .config("spark.sql.catalog.nessie", "org.apache.iceberg.spark.SparkCatalog") \
            .config("spark.sql.catalog.nessie.catalog-impl", "org.apache.iceberg.nessie.NessieCatalog") \
            .config("spark.sql.catalog.nessie.uri", "http://10.0.0.148:19120/api/v1") \
            .config("spark.sql.catalog.nessie.ref", self.branch) \
            .config("spark.sql.catalog.nessie.warehouse", os.environ['WAREHOUSE']) \
            .getOrCreate()
    
    def read_gold_table(self, table_name: str):
        """Read table from Gold layer"""
        return self.spark.table(f"nessie.ecommerce_gold.{table_name}")
    
    def read_silver_table(self, table_name: str):
        """Read table from Silver layer"""
        return self.spark.table(f"nessie.ecommerce_silver.{table_name}")
    
    def create_feature_branch(self, branch_name: str):
        """Create new branch for feature experiments"""
        self.spark.sql(f"CREATE BRANCH {branch_name} FROM main IN nessie")
        self.branch = branch_name
        self._refresh_session()
    
    def time_travel(self, commit_hash: str):
        """Query data at specific point in time"""
        return self.spark.sql(f"""
            SELECT * FROM nessie.ecommerce_gold.orders 
            VERSION AS OF '{commit_hash}'
        """)
    
    def write_features(self, df, feature_name: str):
        """Write ML features to feature store schema"""
        df.writeTo(f"nessie.feature_store.{feature_name}").createOrReplace()
    
    def list_commits(self, limit: int = 10):
        """List recent Nessie commits for reproducibility"""
        return self.spark.sql(f"SHOW LOG IN nessie LIMIT {limit}")
    
    def merge_to_main(self):
        """Merge current branch to main after successful model training"""
        self.spark.sql(f"MERGE BRANCH {self.branch} INTO main IN nessie")


# Example Usage
if __name__ == "__main__":
    # Initialize client
    client = LakehouseClient(branch="main")
    
    # Create feature experiment branch
    client.create_feature_branch("feature_experiment_v1")
    
    # Read Gold data
    orders = client.read_gold_table("daily_sales_summary")
    products = client.read_gold_table("product_performance")
    
    # Create ML features
    features = orders.join(products, "product_id") \
        .select("product_id", "total_revenue", "avg_rating")
    
    # Write to feature store
    client.write_features(features, "product_revenue_features")
    
    print("✅ Features created on branch: feature_experiment_v1")
```

### 7.3: Jupyter Notebook for ML Team

Create `notebooks/ml_feature_engineering.ipynb`:

```python
# Cell 1: Setup
from scripts.ml.lakehouse_client import LakehouseClient

# Connect to lakehouse
client = LakehouseClient(branch="main")
print(f"Connected to Nessie, branch: {client.branch}")

# Cell 2: Create experiment branch
client.create_feature_branch("ml_experiment_2026_01_25")

# Cell 3: Load Gold layer data
orders = client.read_gold_table("daily_sales_summary")
customers = client.read_gold_table("customer_insights")

orders.show(5)

# Cell 4: Time Travel - Compare with last week
last_week_orders = client.time_travel("commit_hash_from_last_week")
current_orders = orders

# Detect data drift
drift = current_orders.count() - last_week_orders.count()
print(f"Row count change: {drift}")

# Cell 5: Feature Engineering
from pyspark.ml.feature import VectorAssembler

# Create feature vector
assembler = VectorAssembler(
    inputCols=["total_revenue", "order_count"], 
    outputCol="features"
)
feature_df = assembler.transform(orders)

# Cell 6: Save features to feature store
client.write_features(feature_df, "sales_prediction_features")

# Cell 7: List commits for reproducibility
commits = client.list_commits(5)
commits.show()

# Cell 8: After successful model training, merge to main
# client.merge_to_main()  # Uncomment when ready
```

### 7.4: ML Benefits Showcase

| Feature | How Nessie+Iceberg Helps | Benefit |
|---------|--------------------------|---------|
| **Feature Versioning** | Each feature set tied to Nessie commit | Reproduce any experiment |
| **Parallel Experiments** | Multiple branches simultaneously | No conflicts between researchers |
| **Data Drift Detection** | Time-travel queries | Compare current vs historical |
| **Model Reproducibility** | Query exact data used for training | Audit trail for compliance |
| **A/B Testing** | Feature branches for different models | Test without affecting production |
| **Rollback** | Revert to previous feature version | Fix bad model inputs |

### 7.5: Visualization Access for ML

ML team can use Superset for:
1. Connect to Trino → Gold layer
2. Create custom feature exploration dashboards
3. Monitor model input distributions

---

## VM Allocation Strategy

### Recommended Distribution

| VM | Services | Resources |
|----|----------|-----------|
| **VM1 (Master)** | Spark Master, Nessie, Jupyter, Airflow | 4 vCPU, 16GB RAM |
| **VM2 (Worker)** | Spark Worker (2 executors) | 2 vCPU, 8GB RAM |
| **VM3 (Services)** | Trino, Superset, Grafana, Prometheus | 2 vCPU, 8GB RAM |
| **VM4 (Optional)** | Additional Spark Worker | 2 vCPU, 8GB RAM |

### If Only 2 VMs Available

| VM | Services |
|----|----------|
| **VM1** | Everything except Spark Worker |
| **VM2** | Spark Worker + Trino (light) |

---

## 📋 Implementation Checklist

### Week 1: Data Quality + Orchestration
- [ ] Install Great Expectations
- [ ] Create expectation suites for Bronze, Silver, Gold
- [ ] Deploy Airflow
- [ ] Create medallion_pipeline DAG
- [ ] Test end-to-end pipeline
## Phase 4: Consumption Layer (VM3 Setup - NOW SPARK THRIFT)
- [x] Create VM3 (Query Engine)
- [x] **Pivot:** Deploy Spark Thrift Server (Replaces Trino due to compatibility)
- [x] Validate JDBC connection on port 10000
- [x] Verify read access to Nessie tables
- [ ] Connect local DBeaver to VM3
### Week 2: Query Engine + ML Access
- [x] Create LakehouseClient for ML team
- [x] Create example ML notebook
- [x] Test feature engineering workflow

### Week 3: Observability + BI
- [x] Deploy Prometheus + Grafana
- [x] Create custom metrics exporter (via Node Exporter/Spark Metrics)
- [x] Import Spark/Airflow dashboards
- [x] Deploy Superset
- [x] Create Gold layer dashboards

### Week 4: Governance + Polish
- [x] Deploy OpenMetadata
- [x] Run metadata ingestion
- [x] Add data lineage
- [x] Tag PII columns (Demonstrable in UI)
- [x] Create project presentation (Docs & Demo Guides)

---

## 🎯 Key Interview Talking Points

After implementing this:

1. **"Built production data lakehouse with Git-like version control"**
2. **"Implemented Write-Audit-Publish pattern with automated data quality"**
3. **"Enabled ML team parallel feature engineering with branch isolation"**
4. **"400M+ records with time-travel, rollback, and audit compliance"**
5. **"Full observability with Prometheus metrics and Grafana dashboards"**
6. **"Data governance with OpenMetadata lineage tracking"**

---

*Document created: 2026-01-25*
*Last updated: After successful Spark cluster deployment*
