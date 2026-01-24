# Team Project Plan - Production Lakehouse with ML & Analytics

**4-Member Team | Firebolt Dataset (412M records) | ML Models | Interactive Dashboards**

---

## 📋 Project Overview

**Goal**: Build production-grade data lakehouse with machine learning and analytics dashboards

**Dataset**: Firebolt E-Commerce (52 GB, 412M records)  
**Timeline**: 4 weeks  
**Team Size**: 4 members  
**Budget**: $0/month (free tier only)  
**Deliverables**: 
- Scalable data pipeline
- ML models (customer segmentation, churn prediction, product recommendations)
- Interactive dashboards
- Complete documentation

---

## 👥 Team Structure & Responsibilities

### **Member 1: Infrastructure & Data Engineering Lead** 
**Focus**: Cloud setup, Bronze layer, orchestration

### **Member 2: Data Quality & Silver Layer Lead**
**Focus**: Data transformation, quality assurance, Silver layer

### **Member 3: ML Engineering Lead**
**Focus**: Machine learning models, feature engineering, model deployment

### **Member 4: Analytics & Visualization Lead**
**Focus**: Gold layer aggregations, dashboards, business insights

---

## 📅 4-Week Timeline Overview

```
Week 1: Foundation Setup
├── Infrastructure provisioning (Member 1)
├── Data quality framework (Member 2)
├── ML environment setup (Member 3)
└── Dashboard framework (Member 4)

Week 2: Data Pipeline & Feature Engineering
├── Bronze layer complete (Member 1)
├── Silver layer complete (Member 2)
├── Feature engineering (Member 3)
└── Initial dashboards (Member 4)

Week 3: ML Models & Gold Layer
├── Orchestration (Member 1)
├── Advanced quality checks (Member 2)
├── ML models trained (Member 3)
└── Analytics dashboards (Member 4)

Week 4: Integration & Production
├── Production deployment (Member 1)
├── Data validation (Member 2)
├── Model deployment (Member 3)
└── Final dashboards (Member 4)
```

---

# Member 1: Infrastructure & Data Engineering Lead

**Primary Responsibility**: Cloud infrastructure, data ingestion, orchestration

## Week 1: Foundation (15-20 hours)

### Task 1.1: Oracle Cloud Setup
**Time**: 4 hours

```bash
# Deliverables:
- Oracle Cloud account created
- 2 VMs provisioned (airflow-nessie, spark-cluster)
- VCN configured with security rules
- Object storage bucket created (20 GB)
- S3 API keys generated

# Success Criteria:
✓ VMs accessible via SSH
✓ Storage bucket accepts uploads
✓ Network connectivity verified
```

**Documentation**: 
- `docs/INFRASTRUCTURE_SETUP.md` - Step-by-step setup guide
- `credentials/oracle-credentials.txt` - Access keys (encrypted)

### Task 1.2: Supabase PostgreSQL Setup
**Time**: 1 hour

```bash
# Deliverables:
- Supabase project created
- PostgreSQL database configured
- Connection tested
- Credentials shared with team (secure)

# Success Criteria:
✓ Database accessible from all VMs
✓ Connection pooling configured
✓ Backup schedule set
```

### Task 1.3: Docker Environment
**Time**: 3 hours

```bash
# Deliverables:
- Docker Compose for Nessie + Airflow (VM1)
- Docker Compose for Spark (VM2)
- Environment variables configured
- Health checks implemented

# Files Created:
- docker-compose-prod.yml (VM1)
- docker-compose-spark.yml (VM2)
- .env.prod
- .env.spark

# Success Criteria:
✓ All containers running
✓ Health checks passing
✓ Inter-container networking functional
```

### Task 1.4: Firebolt Dataset Download & Staging
**Time**: 4 hours

```bash
# Deliverables:
- Download Firebolt dataset (52 GB)
- Extract and validate
- Upload to Oracle Object Storage
- Create sample datasets for testing (10%, 25%, 50%)

# Files:
- transactions.csv (412M records)
- users.csv (customer data)
- products.csv (catalog)
- sessions.csv (web activity)

# Success Criteria:
✓ Full dataset downloaded
✓ Sample datasets created
✓ Upload to Oracle successful
✓ Data integrity verified (checksums)
```

### Task 1.5: Nessie Branch Strategy
**Time**: 2 hours

```bash
# Deliverables:
- Branch creation script
- Branch naming conventions
- Merge policies documented

# Branches:
- main (production)
- gold (staging)
- silver (validated data)
- bronze (raw data)
- dev (development)
- member1, member2, member3, member4 (personal branches)

# Success Criteria:
✓ All branches created
✓ Permissions configured
✓ Merge workflow tested
```

### Task 1.6: Monitoring Setup
**Time**: 2 hours

```bash
# Deliverables:
- Grafana Cloud account
- Grafana Agent installed on both VMs
- Basic dashboards created

# Metrics:
- System resources (CPU, RAM, disk)
- Docker container health
- Nessie API metrics
- Airflow job status

# Success Criteria:
✓ Metrics flowing to Grafana
✓ Alerts configured
✓ Dashboard accessible to team
```

---

## Week 2: Bronze Layer & Ingestion (12-15 hours)

### Task 1.7: Bronze Layer Ingestion Scripts
**Time**: 6 hours

```python
# Files to Create:
scripts/bronze/
├── ingest_transactions.py  # Main order/transaction data
├── ingest_users.py         # Customer data
├── ingest_products.py      # Product catalog
└── ingest_sessions.py      # Web session data

# Features:
- Partitioning by month (7 partitions)
- Parquet compression (Snappy)
- Schema validation
- Incremental loading support
- Error handling & logging

# Success Criteria:
✓ All 4 tables ingested to bronze branch
✓ Partitioning working correctly
✓ Data compressed efficiently (52 GB → ~15 GB)
✓ Ingestion time < 30 minutes
```

**Code Template**:
```python
# scripts/bronze/ingest_transactions.py
def ingest_transactions(spark, month=None):
    """
    Ingest transactions with monthly partitioning
    
    Args:
        month: Specific month to ingest (e.g., '2019-10') or None for all
    """
    # Read from Oracle Object Storage
    df = spark.read.csv(
        "oci://lakehouse-prod/raw/transactions.csv",
        header=True,
        inferSchema=True
    )
    
    # Add partition column
    df = df.withColumn("year_month", F.date_format("order_date", "yyyy-MM"))
    
    # Filter by month if specified
    if month:
        df = df.filter(F.col("year_month") == month)
    
    # Write to Iceberg with partitioning
    df.writeTo("nessie.ecommerce.transactions_bronze") \
        .using("iceberg") \
        .partitionedBy("year_month") \
        .tableProperty("write.parquet.compression-codec", "snappy") \
        .createOrReplace()
```

### Task 1.8: Data Pipeline Orchestration
**Time**: 6 hours

```python
# Files to Create:
airflow/dags/
├── daily_pipeline.py           # Main production pipeline
├── incremental_load.py         # Incremental loading
├── backfill_historical.py      # Historical data backfill
└── data_quality_checks.py      # QA pipeline

# DAG Structure:
daily_pipeline:
  1. Health checks (Nessie, Spark)
  2. Bronze ingestion (parallel)
     - ingest_transactions
     - ingest_users
     - ingest_products
     - ingest_sessions
  3. Silver transformation (Member 2's tasks)
  4. Gold aggregation (Member 4's tasks)
  5. ML feature generation (Member 3's tasks)
  6. Quality validation
  7. Promote to production
  8. Notifications

# Success Criteria:
✓ DAG runs end-to-end successfully
✓ Each task has retry logic
✓ Failure notifications working
✓ Execution time < 60 minutes
```

---

## Week 3: Advanced Orchestration (10-12 hours)

### Task 1.9: Incremental Loading Strategy
**Time**: 5 hours

```python
# Implement Change Data Capture (CDC)
# Features:
- Detect new data files
- Process only new/updated records
- Update existing partitions
- Maintain audit log

# Success Criteria:
✓ Only new data processed
✓ No duplicate records
✓ Audit trail maintained
```

### Task 1.10: Performance Optimization
**Time**: 5 hours

```yaml
Optimizations:
  - Spark configuration tuning
  - Partition pruning
  - Iceberg compaction
  - Cache frequently accessed tables
  - Connection pooling

Success Metrics:
  - Ingestion: 30 min → 15 min
  - Queries: 10s → 2s
  - Resource utilization: < 80%
```

---

## Week 4: Production Deployment (8-10 hours)

### Task 1.11: Production Cutover
**Time**: 4 hours

```bash
# Checklist:
✓ All services running
✓ SSL certificates installed
✓ Firewall rules configured
✓ Backups scheduled
✓ Monitoring active
✓ Documentation complete
```

### Task 1.12: Team Training & Handoff
**Time**: 4 hours

```bash
# Deliverables:
- Infrastructure runbook
- Troubleshooting guide
- Access management document
- Disaster recovery plan
```

---

# Member 2: Data Quality & Silver Layer Lead

**Primary Responsibility**: Data transformation, quality assurance, Silver layer

## Week 1: Quality Framework (12-15 hours)

### Task 2.1: Data Quality Framework
**Time**: 6 hours

```python
# Files to Create:
scripts/utils/
├── quality_checks.py           # Core quality framework
├── schema_validator.py         # Schema validation
├── data_profiler.py           # Data profiling
└── anomaly_detector.py        # Anomaly detection

# Quality Dimensions:
1. Completeness (null checks)
2. Validity (data type, format)
3. Accuracy (range checks, business rules)
4. Consistency (referential integrity)
5. Timeliness (data freshness)
6. Uniqueness (duplicate detection)

# Success Criteria:
✓ Framework supports all 6 dimensions
✓ Configurable thresholds
✓ Detailed quality reports
✓ Auto-remediation for common issues
```

**Code Example**:
```python
# scripts/utils/quality_checks.py
class DataQualityValidator:
    def __init__(self, df, table_name):
        self.df = df
        self.table_name = table_name
        self.results = []
    
    def check_completeness(self, required_columns, threshold=0.95):
        """
        Ensure required columns have >= threshold% non-null values
        """
        for col in required_columns:
            non_null_pct = self.df.filter(F.col(col).isNotNull()).count() / self.df.count()
            if non_null_pct < threshold:
                self.results.append({
                    'check': 'completeness',
                    'column': col,
                    'status': 'FAIL',
                    'non_null_pct': non_null_pct,
                    'threshold': threshold
                })
    
    def check_validity(self, column, data_type):
        """
        Validate data type and format
        """
        # Email format
        if data_type == 'email':
            invalid = self.df.filter(~F.col(column).rlike(
                r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            )).count()
        
        # Date range
        elif data_type == 'date':
            invalid = self.df.filter(
                (F.col(column) < '1900-01-01') |
                (F.col(column) > F.current_date())
            ).count()
    
    def check_accuracy(self, column, min_val=None, max_val=None):
        """
        Business rule validation
        """
        if min_val:
            violations = self.df.filter(F.col(column) < min_val).count()
        if max_val:
            violations = self.df.filter(F.col(column) > max_val).count()
    
    def generate_report(self):
        """
        Generate HTML quality report
        """
        return pd.DataFrame(self.results).to_html()
```

### Task 2.2: Schema Management
**Time**: 3 hours

```python
# Deliverables:
- Schema registry for all tables
- Schema evolution tracking
- Backward compatibility checks

# Tables to Manage:
1. transactions_bronze/silver
2. users_bronze/silver
3. products_bronze/silver
4. sessions_bronze/silver

# Success Criteria:
✓ Schema changes logged
✓ Breaking changes prevented
✓ Schema documentation auto-generated
```

### Task 2.3: Data Profiling
**Time**: 4 hours

```python
# Create profiling reports for:
- Statistical summaries (mean, median, std)
- Distribution analysis
- Correlation matrices
- Outlier detection
- Missing value patterns

# Output:
reports/
├── transactions_profile.html
├── users_profile.html
├── products_profile.html
└── sessions_profile.html

# Success Criteria:
✓ Profiles generated automatically
✓ Anomalies flagged
✓ Trends visualized
```

---

## Week 2: Silver Layer Transformation (15-18 hours)

### Task 2.4: Transactions Silver Script
**Time**: 5 hours

```python
# scripts/silver/transform_transactions.py

# Transformations:
1. Deduplication (remove duplicate order_ids)
2. Data type standardization
3. Null handling (imputation or removal)
4. Outlier treatment (cap extreme values)
5. Derived columns:
   - order_total (price + tax + shipping)
   - order_year_month
   - is_weekend
   - is_holiday
   - price_category (low/medium/high)
6. Quality scoring (1-100)
7. Referential integrity (join with users, products)

# Success Criteria:
✓ Deduplication: 412M → ~410M records
✓ Quality score: Avg > 95
✓ All nulls handled
✓ Processing time < 25 min
```

### Task 2.5: Users Silver Script
**Time**: 4 hours

```python
# scripts/silver/transform_users.py

# Transformations:
1. Email validation & standardization
2. Duplicate customer detection
3. Address parsing & standardization
4. Customer segmentation (RFM):
   - Recency (days since last order)
   - Frequency (number of orders)
   - Monetary (total spend)
5. Lifetime value calculation
6. Customer status (active/inactive/churned)

# Success Criteria:
✓ Email validity > 99%
✓ Unique customers identified
✓ RFM scores calculated
```

### Task 2.6: Products Silver Script
**Time**: 3 hours

```python
# scripts/silver/transform_products.py

# Transformations:
1. Category standardization
2. Price consistency checks
3. Brand name cleansing
4. Product hierarchy (category/subcategory)
5. Availability status
6. Product scoring (popularity, rating)

# Success Criteria:
✓ Categories normalized
✓ Pricing anomalies flagged
```

### Task 2.7: Sessions Silver Script
**Time**: 3 hours

```python
# scripts/silver/transform_sessions.py

# Transformations:
1. Session duration calculation
2. Page view aggregation
3. Bounce rate calculation
4. Conversion tracking
5. User journey mapping

# Success Criteria:
✓ Session metrics accurate
✓ Conversion funnel identified
```

---

## Week 3: Advanced Quality & Integration (12-15 hours)

### Task 2.8: Cross-Table Validation
**Time**: 5 hours

```python
# Referential Integrity Checks:
1. All transaction.user_id exists in users
2. All transaction.product_id exists in products
3. All session.user_id exists in users
4. Transaction amounts match payment records
5. Inventory counts consistent

# Success Criteria:
✓ 100% referential integrity
✓ Orphaned records < 0.1%
```

### Task 2.9: Data Quality Dashboard
**Time**: 5 hours

```python
# Create quality monitoring dashboard:
- Real-time quality scores
- Trend analysis (quality over time)
- Table-level metrics
- Failure alerts

# Tools: Grafana + Python metrics exporter

# Success Criteria:
✓ Dashboard auto-updates
✓ Alerts trigger on quality drop
```

### Task 2.10: Documentation
**Time**: 3 hours

```markdown
# Deliverables:
- Data dictionary (all tables, all columns)
- Transformation logic documentation
- Quality thresholds documentation
- SLA definitions
```

---

## Week 4: Production Validation (8-10 hours)

### Task 2.11: End-to-End Testing
**Time**: 5 hours

```bash
# Test Scenarios:
1. Happy path (perfect data)
2. Edge cases (nulls, duplicates)
3. Failure scenarios (bad data)
4. Performance testing (large volumes)
5. Concurrent load testing

# Success Criteria:
✓ All tests passing
✓ SLAs met
```

### Task 2.12: Runbook Creation
**Time**: 3 hours

```markdown
# Create operational runbook:
- How to investigate quality failures
- How to re-run failed jobs
- How to update quality rules
- Escalation procedures
```

---

# Member 3: ML Engineering Lead

**Primary Responsibility**: Machine learning models, feature engineering, model deployment

## Week 1: ML Environment & Feature Engineering (15-18 hours)

### Task 3.1: ML Environment Setup
**Time**: 4 hours

```bash
# Setup:
- Jupyter Notebook environment (on VM2)
- MLflow for experiment tracking
- S3 bucket for model artifacts
- Python ML libraries

# Libraries to Install:
pip install:
  - scikit-learn
  - xgboost
  - lightgbm
  - mlflow
  - shap (model explainability)
  - pandas
  - matplotlib
  - seaborn

# Success Criteria:
✓ Jupyter accessible
✓ MLflow tracking server running
✓ GPU support (if available)
```

### Task 3.2: Exploratory Data Analysis (EDA)
**Time**: 6 hours

```python
# Notebooks to Create:
notebooks/
├── 01_transactions_eda.ipynb
├── 02_users_eda.ipynb
├── 03_products_eda.ipynb
└── 04_sessions_eda.ipynb

# Analysis:
1. Distribution analysis
2. Correlation heatmaps
3. Time series trends
4. Customer behavior patterns
5. Product popularity analysis
6. Seasonal patterns

# Insights to Find:
- Peak shopping hours/days
- Customer lifetime value distribution
- Product category performance
- Churn indicators

# Success Criteria:
✓ Key insights documented
✓ Feature ideas identified
✓ Data quality issues reported
```

### Task 3.3: Feature Engineering Framework
**Time**: 6 hours

```python
# scripts/ml/feature_engineering.py

class FeatureEngineer:
    """
    Generate ML features from silver layer tables
    """
    
    def customer_features(self):
        """
        Customer-level features for churn/segmentation
        """
        features = {
            # Transaction features
            'total_orders': F.count('order_id'),
            'total_revenue': F.sum('order_total'),
            'avg_order_value': F.avg('order_total'),
            'max_order_value': F.max('order_total'),
            'min_order_value': F.min('order_total'),
            
            # Recency features
            'days_since_last_order': F.datediff(F.current_date(), F.max('order_date')),
            'days_since_first_order': F.datediff(F.current_date(), F.min('order_date')),
            
            # Frequency features
            'orders_per_month': F.count('order_id') / F.months_between(F.max('order_date'), F.min('order_date')),
            
            # Engagement features
            'total_sessions': F.count('session_id'),
            'pages_per_session': F.avg('page_views'),
            'bounce_rate': F.avg('is_bounce'),
            
            # Monetary features
            'lifetime_value': F.sum('order_total'),
            'avg_discount_used': F.avg('discount_amount'),
            
            # Behavioral features
            'preferred_category': F.mode('product_category'),
            'preferred_day_of_week': F.mode(F.dayofweek('order_date')),
            'is_weekend_shopper': F.when(F.avg(F.dayofweek('order_date')) > 5, 1).otherwise(0),
        }
        return features
    
    def product_features(self):
        """
        Product-level features for recommendations
        """
        pass
    
    def session_features(self):
        """
        Session-level features for conversion prediction
        """
        pass

# Success Criteria:
✓ 50+ features generated
✓ Features saved to feature store
✓ Feature importance documented
```

---

## Week 2: Model Development (18-20 hours)

### Task 3.4: Customer Segmentation Model (Unsupervised)
**Time**: 6 hours

```python
# Model: K-Means Clustering + RFM Analysis

# notebooks/models/customer_segmentation.ipynb

# Steps:
1. Load customer features from silver layer
2. RFM calculation:
   - Recency: Days since last purchase
   - Frequency: Number of orders
   - Monetary: Total spend
3. Feature scaling (StandardScaler)
4. Optimal cluster selection (Elbow method)
5. K-Means clustering (k=5)
6. Cluster profiling & interpretation
7. Segment naming:
   - Champions (high RFM)
   - Loyal (high frequency)
   - At Risk (high monetary, low recency)
   - Lost (low recency)
   - New Customers

# Deliverables:
- Trained model (models/customer_segmentation.pkl)
- Cluster profiles (reports/segments.html)
- Prediction script (scripts/ml/predict_segment.py)

# Success Criteria:
✓ 5 distinct, interpretable segments
✓ Silhouette score > 0.4
✓ Segment sizes balanced (10-30% each)
```

### Task 3.5: Churn Prediction Model (Supervised)
**Time**: 7 hours

```python
# Model: XGBoost Binary Classifier

# notebooks/models/churn_prediction.ipynb

# Target Variable:
churned = (days_since_last_order > 90) & (total_orders > 1)

# Features:
- RFM scores
- Order frequency trends
- Average order value
- Session engagement metrics
- Product category preferences
- Discount sensitivity

# Steps:
1. Label creation (churned = 1, active = 0)
2. Train/test split (80/20)
3. Feature engineering
4. XGBoost training
5. Hyperparameter tuning (GridSearchCV)
6. Model evaluation:
   - AUC-ROC score
   - Precision/Recall
   - F1 score
   - Feature importance
7. SHAP analysis (explainability)

# Deliverables:
- Trained model (models/churn_prediction.pkl)
- Feature importance chart
- SHAP summary plot
- Prediction API endpoint

# Success Criteria:
✓ AUC-ROC > 0.80
✓ Precision > 0.75
✓ Recall > 0.70
✓ Model interpretable (top features documented)
```

### Task 3.6: Product Recommendation Model (Collaborative Filtering)
**Time**: 7 hours

```python
# Model: Matrix Factorization (ALS) + Content-Based

# notebooks/models/product_recommendations.ipynb

# Approach: Hybrid recommendation
1. Collaborative Filtering (user-product interactions)
2. Content-Based (product attributes)
3. Weighted ensemble

# Implementation:
from pyspark.ml.recommendation import ALS

# Build user-product matrix
user_product = transactions.groupBy('user_id', 'product_id') \
    .agg(F.sum('quantity').alias('rating'))

# ALS model
als = ALS(
    maxIter=10,
    regParam=0.01,
    userCol='user_id',
    itemCol='product_id',
    ratingCol='rating'
)

model = als.fit(user_product)

# Generate top 10 recommendations per user
recommendations = model.recommendForAllUsers(10)

# Evaluation:
- Precision@K
- Recall@K
- NDCG score

# Success Criteria:
✓ Precision@10 > 0.15
✓ Recommendations diverse (not all same category)
✓ Cold start handling implemented
```

---

## Week 3: Model Deployment & Integration (12-15 hours)

### Task 3.7: MLflow Model Registry
**Time**: 4 hours

```python
# Setup MLflow tracking:
import mlflow
mlflow.set_tracking_uri("http://localhost:5000")

# Log models:
with mlflow.start_run():
    mlflow.log_param("model", "xgboost")
    mlflow.log_metric("auc", 0.85)
    mlflow.sklearn.log_model(model, "churn_model")

# Model versioning:
- Version 1: Baseline model
- Version 2: Improved features
- Version 3: Production model

# Success Criteria:
✓ All 3 models registered
✓ Version history tracked
✓ Production model tagged
```

### Task 3.8: Model Serving API
**Time**: 5 hours

```python
# Create FastAPI endpoints:
# scripts/ml/model_api.py

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class CustomerInput(BaseModel):
    customer_id: str
    recency: int
    frequency: int
    monetary: float

@app.post("/predict/churn")
def predict_churn(customer: CustomerInput):
    """Predict churn probability"""
    model = mlflow.pyfunc.load_model("models:/churn_model/production")
    proba = model.predict(customer.dict())
    return {"churn_probability": proba, "risk_level": "high" if proba > 0.7 else "low"}

@app.post("/predict/segment")
def predict_segment(customer: CustomerInput):
    """Predict customer segment"""
    model = load_model("customer_segmentation")
    segment = model.predict(customer.dict())
    return {"segment": segment, "profile": get_segment_profile(segment)}

@app.get("/recommend/{user_id}")
def get_recommendations(user_id: str, n: int = 10):
    """Get product recommendations"""
    recs = recommendation_model.recommend(user_id, n)
    return {"user_id": user_id, "recommendations": recs}

# Deploy as Docker container:
# Dockerfile
FROM python:3.11-slim
COPY requirements-ml.txt .
RUN pip install -r requirements-ml.txt
COPY scripts/ml ./app
CMD ["uvicorn", "app.model_api:app", "--host", "0.0.0.0", "--port", "8000"]

# Success Criteria:
✓ API serving models
✓ Response time < 100ms
✓ API documented (Swagger)
```

### Task 3.9: Batch Prediction Pipeline
**Time**: 4 hours

```python
# Create Airflow DAG for batch predictions:
# airflow/dags/ml_predictions.py

@dag(schedule="0 3 * * *")  # 3 AM daily
def ml_predictions_pipeline():
    
    @task
    def generate_customer_features():
        """Generate features for all customers"""
        spark = get_spark_session()
        features = FeatureEngineer().customer_features()
        features.write.mode("overwrite").saveAsTable("ml.customer_features")
    
    @task
    def predict_churn():
        """Run churn predictions for all customers"""
        model = mlflow.pyfunc.load_model("models:/churn_model/production")
        features = spark.table("ml.customer_features")
        predictions = model.predict(features)
        predictions.write.mode("overwrite").saveAsTable("ml.churn_predictions")
    
    @task
    def predict_segments():
        """Run segmentation for all customers"""
        pass
    
    @task
    def generate_recommendations():
        """Generate recommendations for all users"""
        pass
    
    generate_customer_features() >> predict_churn()

# Success Criteria:
✓ Predictions run daily
✓ Results saved to tables
✓ Execution time < 20 min
```

---

## Week 4: Production & Monitoring (10-12 hours)

### Task 3.10: A/B Testing Framework
**Time**: 4 hours

```python
# Implement experiment tracking:
- Control group (no recommendations)
- Treatment group (ML recommendations)
- Metrics: conversion rate, revenue lift

# Success Criteria:
✓ A/B test framework functional
✓ Metrics tracked automatically
```

### Task 3.11: Model Monitoring
**Time**: 4 hours

```python
# Monitor:
1 Model performance drift
2. Feature distribution drift
3. Prediction latency
4. API error rates

# Alerts:
- AUC drops below 0.75
- Feature drift detected
- API latency > 200ms

# Success Criteria:
✓ Monitoring dashboard created
✓ Alerts firing correctly
```

### Task 3.12: Documentation
**Time**: 3 hours

```markdown
# Deliverables:
- Model cards (one per model)
- API documentation
- Feature documentation
- Retraining guide
```

---

# Member 4: Analytics & Visualization Lead

**Primary Responsibility**: Gold layer, dashboards, business insights

## Week 1: Dashboard Framework (12-15 hours)

### Task 4.1: Dashboard Technology Selection
**Time**: 2 hours

```yaml
Options Evaluated:
  Option 1: Streamlit (Python)
    Pros: Easy, Python-native, free hosting
    Cons: Less polished than commercial tools
    
  Option 2: Metabase (Open-source)
    Pros: SQL-native, beautiful UI
    Cons: Requires hosting
    
  Option 3: Apache Superset
    Pros: Feature-rich, scalable
    Cons: Complex setup
    
  Option 4: Plotly Dash
    Pros: Interactive, professional
    Cons: Learning curve

# Recommendation: Streamlit + Plotly
# Reason: Fast development, professional output, free

# Success Criteria:
✓ Framework selected
✓ POC dashboard created
✓ Team approved
```

### Task 4.2: Dashboard Infrastructure
**Time**: 4 hours

```bash
# Setup:
1. Streamlit app on VM2 (port 8501)
2. Database connection to Supabase (via Nessie)
3. Authentication (optional)
4. Caching for performance

# Files:
dashboards/
├── app.py                  # Main dashboard app
├── pages/
│   ├── 01_overview.py      # Executive summary
│   ├── 02_sales.py         # Sales analytics
│   ├── 03_customers.py     # Customer insights
│   ├── 04_products.py      # Product performance
│   └── 05_ml.py            # ML insights
├── utils/
│   ├── data_loader.py      # Query Iceberg tables
│   ├── charts.py           # Reusable chart functions
│   └── metrics.py          # KPI calculations
└── requirements.txt

# Success Criteria:
✓ Dashboard accessible at http://[VM2]:8501
✓ Data loading < 5 seconds
✓ Responsive design
```

### Task 4.3: Gold Layer Schema Design
**Time**: 4 hours

```sql
-- Design aggregated tables for fast queries

-- Table 1: Daily Sales Summary
CREATE TABLE gold.daily_sales AS
SELECT 
    order_date,
    COUNT(DISTINCT user_id) as customers,
    COUNT(order_id) as orders,
    SUM(order_total) as revenue,
    AVG(order_total) as avg_order_value,
    SUM(CASE WHEN is_first_order THEN 1 ELSE 0 END) as new_customers
FROM silver.transactions
GROUP BY order_date;

-- Table 2: Customer Segments Summary
CREATE TABLE gold.customer_segments AS
SELECT 
    segment,
    COUNT(customer_id) as customer_count,
    AVG(lifetime_value) as avg_ltv,
    AVG(total_orders) as avg_orders,
    SUM(lifetime_value) as total_value
FROM ml.customer_segments
GROUP BY segment;

-- Table 3: Product Performance
CREATE TABLE gold.product_performance AS
SELECT 
    product_id,
    product_name,
    category,
    COUNT(DISTINCT user_id) as unique_buyers,
    COUNT(order_id) as times_purchased,
    SUM(quantity) as total_quantity_sold,
    SUM(revenue) as total_revenue,
    AVG(rating) as avg_rating
FROM silver.transactions t
JOIN silver.products p USING(product_id)
GROUP BY product_id, product_name, category;

-- Success Criteria:
✓ 10+ gold tables created
✓ Queries < 2 seconds
✓ Daily refresh scheduled
```

---

## Week 2: Dashboard Development (18-20 hours)

### Task 4.4: Executive Overview Dashboard
**Time**: 5 hours

```python
# pages/01_overview.py

import streamlit as st
import plotly.express as px

st.title("📊 Executive Overview")

# KPI Cards
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Total Revenue", "$12.5M", "+23% MoM")
with col2:
    st.metric("Active Customers", "142K", "+5.2%")
with col3:
    st.metric("Avg Order Value", "$87.23", "-2.1%")
with col4:
    st.metric("Churn Rate", "12.3%", "-1.5%")

# Revenue Trend
revenue_trend = load_data("SELECT order_date, SUM(revenue) FROM gold.daily_sales GROUP BY 1")
fig = px.line(revenue_trend, x='order_date', y='revenue', title='Revenue Trend')
st.plotly_chart(fig)

# Customer Segmentation Pie Chart
segments = load_data("SELECT segment, customer_count FROM gold.customer_segments")
fig = px.pie(segments, names='segment', values='customer_count', title='Customer Distribution')
st.plotly_chart(fig)

# Top Products Table
top_products = load_data("SELECT * FROM gold.product_performance ORDER BY total_revenue DESC LIMIT 10")
st.dataframe(top_products)

# Success Criteria:
✓ 6+ visualizations
✓ Interactive filters
✓ Auto-refresh every 5 minutes
```

### Task 4.5: Sales Analytics Dashboard
**Time**: 5 hours

```python
# pages/02_sales.py

# Features:
1. Sales by time period (daily/weekly/monthly)
2. Sales by category
3. Sales by region
4. Seasonality analysis
5. Cohort analysis
6. Funnel analysis

# Charts:
- Time series (revenue, orders)
- Heatmap (day of week × hour)
- Waterfall (revenue components)
- Sunburst (category hierarchy)
- Sankey (conversion funnel)

# Filters:
- Date range picker
- Category selector
- Region selector
- Customer segment filter

# Success Criteria:
✓ 8+ charts
✓ All filters functional
✓ Export to CSV/PDF
```

### Task 4.6: Customer Analytics Dashboard
**Time**: 4 hours

```python
# pages/03_customers.py

# Features:
1. Customer lifetime value distribution
2. RFM segmentation
3. Churn analysis
4. Customer acquisition trends
5. Cohort retention
6. Geographic distribution

# ML Integration:
- Churn risk scores (from Member 3's model)
- Predicted CLV
- Recommended actions per segment

# Success Criteria:
✓ ML predictions displayed
✓ Actionable insights surfaced
✓ Drill-down capability
```

### Task 4.7: Product Analytics Dashboard
**Time**: 4 hours

```python
# pages/04_products.py

# Features:
1. Product performance ranking
2. Category analysis
3. Inventory turnover
4. Price elasticity analysis
5. Cross-sell/upsell opportunities
6. Product recommendations (from ML model)

# Charts:
- Scatter (price vs demand)
- Bar (top/bottom performers)
- Network (product associations)
- Treemap (category contribution)

# Success Criteria:
✓ Product recommendations integrated
✓ Inventory alerts shown
```

---

## Week 3: Advanced Analytics (15-18 hours)

### Task 4.8: ML Insights Dashboard
**Time**: 6 hours

```python
# pages/05_ml.py

# Display ML model outputs:
1. Customer Segmentation
   - Segment profiles
   - Segment trends over time
   - Migration matrix (segment changes)

2. Churn Predictions
   - Churn risk distribution
   - High-risk customer list
   - Churn drivers (SHAP values)
   - Retention recommendations

3. Product Recommendations
   - Personalized recs preview
   - Recommendation coverage
   - Recommendation diversity
   - A/B test results

# Interactivity:
- Select customer to see predictions
- Compare segments
- Drill into churn drivers

# Success Criteria:
✓ All 3 models visualized
✓ Explanations provided (SHAP)
✓ Actionable recommendations
```

### Task 4.9: Gold Layer Aggregation Scripts
**Time**: 6 hours

```python
# scripts/gold/aggregate_sales.py
# scripts/gold/aggregate_customers.py
# scripts/gold/aggregate_products.py
# scripts/gold/aggregate_ml_insights.py

# Features:
- Incremental aggregation
- Partitioned by date
- Windowing functions for trends
- Pre-calculated metrics

# Success Criteria:
✓ All gold tables populated
✓ Aggregation time < 10 min
✓ Data freshness < 1 hour
```

### Task 4.10: Real-Time Monitoring Dashboard
**Time**: 4 hours

```python
# pages/06_monitoring.py

# System Health:
- Pipeline status
- Data freshness
- Quality scores
- Model performance
- API latency

# Data Quality Metrics:
- Completeness by table
- Null rates
- Duplicate rates
- Anomaly alerts

# Success Criteria:
✓ Real-time updates
✓ Alerts visible
✓ Drill-down to issues
```

---

## Week 4: Polish & Deployment (10-12 hours)

### Task 4.11: Dashboard Enhancements
**Time**: 5 hours

```python
# Polish:
1. Consistent theme/branding
2. Loading states
3. Error handling
4. Mobile responsiveness
5. Dark mode support
6. Accessibility (WCAG)

# Performance:
- Query optimization
- Caching strategy
- Lazy loading
- Data pagination

# Success Criteria:
✓ Professional appearance
✓ Load time < 3 seconds
✓ 0 errors on 10 test scenarios
```

### Task 4.12: User Documentation
**Time**: 3 hours

```markdown
# Create:
- Dashboard user guide
- How to interpret metrics
- FAQ section
- Video walkthrough (5 min)

# Success Criteria:
✓ Non-technical users can navigate
✓ All metrics explained
```

### Task 4.13: Presentation Deck
**Time**: 3 hours

```powerpoint
# Create final presentation:
1. Project overview
2. Architecture diagram
3. Dataset highlights
4. Key insights/findings
5. ML model results
6. Dashboard demo
7. Technical achievements
8. Future enhancements

# Target: 15-20 slides

# Success Criteria:
✓ Tells compelling story
✓ Demonstrates technical depth
✓ Business value clear
```

---

## 🤝 Team Collaboration & Integration

### Integration Points

```yaml
Member 1 → Member 2:
  - Bronze tables available for Silver transformation
  - Nessie branches created

Member 2 → Member 3:
  - Clean features in Silver layer
  - Quality-validated data for ML

Member 3 → Member 4:
  - ML predictions in feature tables
  - Model APIs for dashboard integration

Member 4 → All:
  - Dashboard for monitoring
  - Data quality alerts
  - Business insights

All → Member 1:
  - Feedback on infrastructure
  - Feature requests
  - Bug reports
```

### Weekly Sync Meetings

```yaml
Monday Standup (30 min):
  - Progress updates
  - Blockers
  - Plan for week

Wednesday Review (45 min):
  - Demo completed work
  - Code review
  - Technical discussions

Friday Retrospective (30 min):
  - Wins/challenges
  - Learnings
  - Adjustments for next week
```

---

## 📊 Success Metrics

### Team-Level KPIs

```yaml
Week 1:
  ✓ Infrastructure running
  ✓ All team members have access
  ✓ Quality framework operational

Week 2:
  ✓ Bronze + Silver layers complete
  ✓ 1 ML model trained
  ✓ 1 dashboard deployed

Week 3:
  ✓ All 3 ML models trained
  ✓ Gold layer aggregations complete
  ✓ 5 dashboards live

Week 4:
  ✓ Production deployment complete
  ✓ ML models serving predictions
  ✓ Final presentation ready
  ✓ Documentation complete

Final Scorecard:
  - Data processed: 412M records ✓
  - Pipeline uptime: > 99% ✓
  - ML model accuracy: AUC > 0.80 ✓
  - Dashboard performance: < 3s load ✓
  - Cost: $0/month ✓
  - Team satisfaction: 4.5/5 ✓
```

---

## 📚 Deliverables Checklist

### Infrastructure (Member 1)
- [ ] Oracle Cloud environment
- [ ] Docker compose files
- [ ] Airflow DAGs
- [ ] Monitoring setup
- [ ] Documentation: Infrastructure Guide

### Data Pipeline (Member 2)
- [ ] Bronze layer (4 tables)
- [ ] Silver layer (4 tables)
- [ ] Quality framework
- [ ] Data profiling reports
- [ ] Documentation: Data Dictionary

### ML Models (Member 3)
- [ ] Customer segmentation model
- [ ] Churn prediction model
- [ ] Recommendation model
- [ ] Model API endpoints
- [ ] Documentation: Model Cards

### Analytics (Member 4)
- [ ] Gold layer (10+ tables)
- [ ] 6 dashboard pages
- [ ] Executive presentation
- [ ] Business insights report
- [ ] Documentation: User Guide

---

## 🎓 Learning Outcomes

### By End of Project, Each Member Will:

**Member 1 (Infra)**:
- Master cloud infrastructure (Oracle, Supabase)
- Learn Apache Airflow orchestration
- Understand Nessie/Iceberg architecture
- DevOps best practices

**Member 2 (Quality)**:
- Expert in data quality frameworks
- PySpark transformations
- Schema management
- Testing strategies

**Member 3 (ML)**:
- Hands-on ML model development
- Model deployment & serving
- MLOps best practices
- A/B testing

**Member 4 (Analytics)**:
- Advanced SQL & aggregations
- Dashboard development (Streamlit)
- Data storytelling
- Business intelligence

**All Members**:
- Production-scale data engineering
- Git-based collaboration
-  Agile methodology
- Technical presentation

---

**Project Status**: Ready to Execute  
**Total Effort**: ~200 person-hours over 4 weeks  
**ROI**: Portfolio-worthy project + Career-ready skills + $0 cost 🚀

---

*Good luck team! This is going to be an amazing project!* 🎉
