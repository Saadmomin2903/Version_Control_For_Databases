# Complete Codebase Documentation

**Version Control for Databases - Lakehouse Implementation**

This document provides a comprehensive explanation of every file in the codebase, including detailed code analysis and architecture overview.

---

## 📁 Project Overview

This project implements a **Git-like version control system for databases** using:
- **Apache Iceberg**: ACID-compliant table format
- **Project Nessie**: Git-like catalog for data versioning
- **Apache Spark**: Distributed data processing
- **MinIO**: S3-compatible object storage
- **Docker**: Containerized infrastructure

### Architecture Pattern: Medallion Architecture

```
Bronze Layer (Raw)  →  Silver Layer (Cleaned)  →  Gold Layer (Aggregated)
     ↓                        ↓                          ↓
  bronze branch          silver branch               main branch
```

---

## 🗂️ Directory Structure

```
Version_Control_For_Databases/
├── docker-compose.yml          # Infrastructure setup
├── requirements.txt            # Python dependencies
├── QUICKSTART.md              # 5-minute quick start guide
├── SETUP_GUIDE.md             # Detailed setup tutorial
├── README.md                  # Project introduction
├── data/                      # Sample datasets
│   └── raw/
│       ├── orders.csv
│       └── customers.csv
├── scripts/                   # Data processing scripts
│   ├── bronze/               # Raw data ingestion
│   │   ├── ingest_orders_spark.py
│   │   └── ingest_customers_spark.py
│   ├── silver/               # Data transformation
│   │   ├── transform_orders_silver.py
│   │   └── transform_customers_silver.py
│   ├── gold/                 # Business aggregations
│   │   └── aggregate_customer_summary_gold.py
│   └── utils/                # Helper utilities
│       ├── create_nessie_branches.py
│       └── quality_checks.py
├── config/                   # Configuration files
├── notebooks/                # Jupyter notebooks
├── orchestration/            # Workflow orchestration
├── tests/                    # Test suite
└── plan/                     # Documentation
    ├── project_idea.md
    ├── lakehouse_implementation_guide.md
    └── complete_journey.md
```

---

## 🐳 Infrastructure Files

### docker-compose.yml

**Purpose**: Orchestrates all infrastructure services in Docker containers.

**Services Defined**:

#### 1. MinIO (Object Storage)
```yaml
minio:
  image: minio/minio:RELEASE.2024-11-07T00-52-20Z
  ports: 9000 (API), 9001 (Console)
  environment:
    MINIO_ROOT_USER: admin
    MINIO_ROOT_PASSWORD: password123
```

**What it does**:
- Provides S3-compatible object storage for Iceberg table data
- Stores Parquet files containing actual data
- Accessible via web UI at `http://localhost:9001`
- Storage path: `/data` (mounted as Docker volume `minio-data`)

**Key Configuration**:
- `path.style.access=true`: Uses path-style URLs (bucket/key vs subdomain)
- Console runs on port 9001 for web interface
- Health check ensures MinIO is ready before dependent services start

#### 2. PostgreSQL (Metadata Storage)
```yaml
postgres:
  image: postgres:16-alpine
  environment:
    POSTGRES_USER: admin
    POSTGRES_DB: metastore
```

**What it does**:
- Stores Nessie's catalog metadata (branches, commits, references)
- Provides **persistent storage** for Nessie (data survives container restarts)
- Uses JDBC connection for Nessie version store

**Why PostgreSQL?**:
- Ensures Nessie branches and metadata persist across restarts
- Production-grade reliability vs in-memory storage
- ACID guarantees for catalog operations

#### 3. Nessie (Catalog Server)
```yaml
nessie:
  image: projectnessie/nessie:0.67.0
  environment:
    NESSIE_VERSION_STORE_TYPE: JDBC
    QUARKUS_DATASOURCE_JDBC_URL: jdbc:postgresql://postgres:5432/metastore
```

**What it does**:
- Git-like catalog for managing Iceberg tables
- Tracks table versions across branches
- Provides REST API at port 19120
- Enables branch, merge, and time-travel operations

**Version Store Configuration**:
- Type: `JDBC` (persistent) vs `IN_MEMORY` (ephemeral)
- Backend: PostgreSQL database
- Stores: branch references, commit logs, table snapshots

#### 4. Spark Notebook (Processing Engine)
```yaml
spark-notebook:
  image: alexmerced/spark33-notebook
  environment:
    AWS_ACCESS_KEY_ID: admin
    AWS_SECRET_ACCESS_KEY: password123
    NESSIE_URI: http://nessie:19120/api/v1
    WAREHOUSE: s3a://lakehouse/warehouse
```

**What it does**:
- Runs PySpark 3.3 for distributed data processing
- Provides Jupyter notebook interface at port 8888
- Executes Bronze/Silver/Gold transformation scripts
- Mounts local volumes for scripts and data

**Environment Variables Explained**:
- `AWS_*`: Credentials for MinIO (S3-compatible)
- `NESSIE_URI`: Catalog server endpoint
- `WAREHOUSE`: Base path for Iceberg table storage
- `AWS_S3_ENDPOINT`: Points to MinIO instead of real AWS

**Volumes**:
- `./scripts` → `/home/jovyan/scripts`: Python processing scripts
- `./data` → `/home/jovyan/data`: CSV source files

---

### requirements.txt

**Purpose**: Python package dependencies for local development.

**Key Dependencies**:

```python
# Iceberg Python client
pyiceberg==0.5.1          # Read/write Iceberg tables from Python

# Data processing
polars==0.20.0            # Fast DataFrame library
pandas==2.1.4             # Traditional DataFrame library
pyarrow==14.0.1           # Columnar format (Parquet)

# Storage clients
minio==7.2.0              # MinIO Python SDK
boto3==1.34.0             # AWS S3 client (works with MinIO)

# API interactions
requests==2.31.0          # HTTP client for Nessie API

# Configuration
python-dotenv==1.0.0      # Load .env files
pyyaml==6.0.1             # YAML parsing

# Testing
pytest==7.4.3             # Test framework
pytest-cov==4.1.0         # Code coverage
```

**Note**: These are for local Python scripts. Spark container has its own JVM-based dependencies.

---

## 📊 Data Processing Scripts

### Bronze Layer: Raw Data Ingestion

#### scripts/bronze/ingest_orders_spark.py

**Purpose**: Reads raw CSV files and writes to Iceberg tables on the `bronze` branch.

**Detailed Code Explanation**:

```python
# 1. Environment Configuration (Lines 12-17)
NESSIE_URI = os.getenv("NESSIE_URI", "http://nessie:19120/api/v1")
WAREHOUSE = os.getenv("WAREHOUSE", "s3a://lakehouse/warehouse")
```
- Uses environment variables from docker-compose
- Defaults ensure script works in container environment
- `s3a://` protocol for S3-compatible storage (MinIO)

```python
# 2. Spark Configuration (Lines 25-54)
conf = (
    pyspark.SparkConf()
        .setAppName('bronze-orders-ingestion')
        .set('spark.jars.packages', 
             'org.apache.iceberg:iceberg-spark-runtime-3.3_2.12:1.3.1,..'))
```

**JAR Dependencies**:
- `iceberg-spark-runtime`: Iceberg integration for Spark 3.3
- `nessie-spark-extensions`: Nessie catalog extensions
- `awssdk:bundle`: AWS SDK for S3 operations
- Version format: `iceberg-spark-runtime-3.3_2.12` means Spark 3.3, Scala 2.12

**Spark Extensions**:
```python
.set('spark.sql.extensions', 
     'org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions,
      org.projectnessie.spark.extensions.NessieSparkSessionExtensions')
```
- Registers SQL extensions for Iceberg DDL (CREATE TABLE, etc.)
- Enables Nessie-specific syntax like `table@branch`

**Catalog Configuration**:
```python
.set('spark.sql.catalog.nessie', 'org.apache.iceberg.spark.SparkCatalog')
.set('spark.sql.catalog.nessie.uri', NESSIE_URI)
.set('spark.sql.catalog.nessie.ref', 'bronze')  # Target branch
.set('spark.sql.catalog.nessie.catalog-impl', 'org.apache.iceberg.nessie.NessieCatalog')
```
- Defines a catalog named `nessie` accessible in SQL
- Points to Nessie server via HTTP
- `ref=bronze`: All writes go to bronze branch
- Catalog implementation handles version control operations

**S3/MinIO Configuration**:
```python
.set('spark.sql.catalog.nessie.s3.endpoint', AWS_S3_ENDPOINT)
.set('spark.hadoop.fs.s3a.path.style.access', 'true')
.set('spark.hadoop.fs.s3a.connection.ssl.enabled', 'false')
```
- Custom S3 endpoint points to MinIO
- Path-style access: `http://minio:9000/bucket/key`
- SSL disabled for local development

```python
# 3. Data Reading (Lines 61-69)
df = spark.read.csv(
    "/home/jovyan/data/raw/orders.csv",
    header=True,          # First row contains column names
    inferSchema=True      # Auto-detect data types
)
```
- Reads mounted CSV file from Docker volume
- Infers schema: `order_id:string, total_amount:double, etc.`

```python
# 4. Namespace Creation (Lines 75-78)
spark.sql("CREATE NAMESPACE IF NOT EXISTS nessie.ecommerce")
```
- Namespace = database in Iceberg
- Format: `catalog.namespace.table`
- Creates logical grouping for tables

```python
# 5. Iceberg Table Write (Lines 81-85)
df.writeTo(table_name).using("iceberg").createOrReplace()
```
- `writeTo()`: DataFrame V2 API (supports Iceberg)
- `using("iceberg")`: Table format specification
- `createOrReplace()`: Idempotent operation (safe to re-run)

**What Happens Physically**:
1. Spark converts DataFrame to Parquet files
2. Parquet files written to MinIO: `s3a://lakehouse/warehouse/ecommerce/orders_bronze/data/`
3. Metadata file created: `metadata/v1.metadata.json`
4. Nessie records commit on `bronze` branch

```python
# 6. Verification (Lines 87-91)
result = spark.sql(f"SELECT COUNT(*) as count FROM {table_name}").collect()
```
- Reads back from Iceberg table to verify write
- `.collect()` brings result to driver

**Key Concepts**:
- **Branch Isolation**: Data written to `bronze` branch only
- **ACID Transactions**: Entire write is atomic (all or nothing)
- **Immutability**: Old data snapshots remain accessible

---

#### scripts/bronze/ingest_customers_spark.py

**Purpose**: Ingests customer data to bronze layer.

**Differences from orders ingestion**:
- Reads `customers.csv` instead of orders
- Table name: `customers_bronze`
- Same architecture and patterns

**Schema Inference Results**:
```
customer_id: string
name: string
email: string
signup_date: date
is_active: boolean
```

---

### Silver Layer: Data Transformation & Quality

#### scripts/silver/transform_orders_silver.py

**Purpose**: Reads from `bronze` branch, applies transformations, writes to `silver` branch.

**Detailed Code Explanation**:

```python
# 1. Import Quality Checker (Lines 15-17)
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from utils.quality_checks import QualityChecker
```
- Adds parent directory to Python path
- Imports custom quality validation framework

```python
# 2. Spark Configuration - Main Branch (Line 45)
.set('spark.sql.catalog.nessie.ref', 'main')
```
- **Why main?** Need to read from multiple branches
- Use `@branch` syntax to specify which branch per query
- Default branch doesn't restrict operations

```python
# 3. Cross-Branch Read (Line 64)
bronze_df = spark.sql("SELECT * FROM nessie.ecommerce.`orders_bronze@bronze`")
```
- **@branch Syntax**: Nessie-specific SQL extension
- Reads from `orders_bronze` table on `bronze` branch
- While connected to `main` branch by default
- Backticks required when using `@` in table names

**Transformation Logic**:

```python
# 4. Deduplication (Line 72)
silver_df = bronze_df.dropDuplicates(["order_id"])
```
- Removes duplicate orders by order_id
- Keeps first occurrence
- Common pattern: source systems may send duplicates

```python
# 5. Data Quality Score (Lines 75-84)
silver_df = silver_df.withColumn(
    "data_quality_score",
    F.when(
        (F.col("order_id").isNotNull()) &
        (F.col("customer_id").isNotNull()) &
        (F.col("total_amount") > 0) &
        (F.col("status").isNotNull()),
        100
    ).otherwise(50)
)
```
- **Quality Scoring**: Numeric metric (50-100)
- Score 100: All critical fields present and valid
- Score 50: Missing or invalid data
- Used for downstream filtering and monitoring

```python
# 6. Processing Metadata (Lines 87-88)
silver_df = silver_df.withColumn("processed_at", F.current_timestamp())
silver_df = silver_df.withColumn("source_branch", F.lit("bronze"))
```
- `processed_at`: Audit timestamp (when transformation ran)
- `source_branch`: Data lineage tracking
- `F.lit()`: Creates literal column value

**Quality Checks**:

```python
# 7. Quality Validation (Lines 98-108)
checker = QualityChecker(silver_df, "orders_silver")
checker.check_row_count(min_expected=int(bronze_count * 0.90))
checker.check_nulls(["order_id", "customer_id"])
checker.check_duplicates(["order_id"])
checker.check_value_range("total_amount", min_val=0)
checker.validate(raise_on_failure=True)
```

**What Each Check Does**:
- `check_row_count`: Ensures at least 90% of bronze records remain (data loss detection)
- `check_nulls`: No nulls in critical ID columns
- `check_duplicates`: Verifies deduplication worked
- `check_value_range`: Business rule - no negative amounts
- `validate()`: Raises exception if any check fails (stops pipeline)

**Write-Audit-Publish Pattern**:

```python
# 8. Write to Silver Branch (Lines 114-130)
silver_df.createOrReplaceTempView("silver_temp")
spark.sql("""
    CREATE OR REPLACE TABLE nessie.ecommerce.`orders_silver@silver`
    USING iceberg
    AS SELECT * FROM silver_temp
""")
```

**Pattern Steps**:
1. **Write**: Create temp view from transformed DataFrame
2. **Audit**: Quality checks (already passed above)
3. **Publish**: Write to `silver` branch via SQL

**Why SQL instead of DataFrame API?**
- SQL supports `@branch` syntax directly
- More explicit branch targeting
- CREATE OR REPLACE is idempotent

```python
# 9. Verification (Line 134)
verify_count = spark.sql("SELECT COUNT(*) FROM nessie.ecommerce.`orders_silver@silver`").collect()[0]['cnt']
```
- Reads from silver branch to verify write succeeded
- Compares count to expected

**Data Flow Summary**:
```
CSV → Bronze Branch → Transformations → Quality Checks → Silver Branch
                      (dedupe, score)     (validate)
```

---

#### scripts/silver/transform_customers_silver.py

**Purpose**: Transforms customer data with email validation.

**Additional Transformations**:

```python
# Email Standardization (Line 74)
silver_df = silver_df.withColumn("email", F.lower(F.col("email")))
```
- Converts emails to lowercase
- Prevents duplicate customers due to case differences
- Example: `User@Example.com` → `user@example.com`

```python
# Email Validation (Lines 77-80)
silver_df = silver_df.withColumn(
    "email_valid",
    F.col("email").contains("@")
)
```
- Simple validation: email must contain `@`
- Adds boolean flag column
- More sophisticated validation could use regex

```python
# Multi-Tier Quality Score (Lines 83-96)
silver_df = silver_df.withColumn(
    "data_quality_score",
    F.when(all_fields_valid, 100)
     .when(basic_fields_valid, 75)
     .otherwise(50)
)
```
- 100: Perfect record (all fields valid)
- 75: Acceptable (ID and email present)
- 50: Poor quality (missing critical fields)

**Custom Quality Check**:
```python
# Email Validity Rate (Lines 120-125)
valid_emails = silver_df.filter(F.col("email_valid") == True).count()
email_validity_rate = (valid_emails / silver_count) * 100

if email_validity_rate < 95:
    raise Exception(f"Email validity rate {email_validity_rate:.1f}% below threshold")
```
- Business rule: At least 95% of emails must be valid
- Fails pipeline if too many invalid emails
- Prevents bad data from propagating

---

### Gold Layer: Business Aggregations

#### scripts/gold/aggregate_customer_summary_gold.py

**Purpose**: Creates business-ready customer metrics by joining silver tables.

**Detailed Code Explanation**:

```python
# 1. Configuration (Line 40)
.set('spark.sql.catalog.nessie.ref', 'main')
```
- Gold layer writes to `main` branch (production)
- Reads from `silver` branch using `@silver` syntax

```python
# 2. Reading Silver Tables (Lines 59-67)
customers_df = spark.sql("SELECT * FROM nessie.ecommerce.`customers_silver@silver`")
orders_df = spark.sql("SELECT * FROM nessie.ecommerce.`orders_silver@silver`")
```
- Reads validated data from silver branch
- Both tables have passed quality checks
- Cross-branch read while connected to main

**Business Logic**:

```python
# 3. Filter Completed Orders (Line 74)
completed_orders = orders_df.filter(F.col("status") == "completed")
```
- Only count revenue from completed orders
- Excludes: pending, cancelled, refunded
- Business rule for accurate revenue calculation

```python
# 4. Aggregate Metrics (Lines 77-83)
customer_metrics = completed_orders.groupBy("customer_id").agg(
    F.count("order_id").alias("total_orders"),
    F.sum("total_amount").alias("total_revenue"),
    F.avg("total_amount").alias("avg_order_value"),
    F.min("order_date").alias("first_order_date"),
    F.max("order_date").alias("last_order_date")
)
```

**Metrics Calculated**:
- `total_orders`: Number of completed orders
- `total_revenue`: Sum of all order amounts (CLV proxy)
- `avg_order_value`: Average transaction size
- `first_order_date`: Customer acquisition date
- `last_order_date`: Recency metric

```python
# 5. Customer Lifetime Value (Lines 86-89)
customer_metrics = customer_metrics.withColumn(
    "customer_lifetime_value",
    F.col("total_revenue")
)
```
- CLV = total revenue (simplified model)
- Production: Would include predicted future value

```python
# 6. Rounding for Readability (Lines 92-98)
customer_metrics = customer_metrics.withColumn(
    "total_revenue", F.round(F.col("total_revenue"), 2)
)
```
- Rounds financial values to 2 decimal places
- Prevents floating-point precision issues in reports

```python
# 7. Join with Customer Details (Lines 107-111)
customer_summary = customers_df.join(
    customer_metrics,
    on="customer_id",
    how="left"
)
```
- **LEFT JOIN**: Keeps all customers, even with no orders
- Ensures complete customer list
- Nulls filled in next step

```python
# 8. Fill Nulls for Zero-Order Customers (Lines 114-119)
customer_summary = customer_summary.fillna({
    "total_orders": 0,
    "total_revenue": 0.0,
    "avg_order_value": 0.0,
    "customer_lifetime_value": 0.0
})
```
- Customers with no orders get zeros instead of nulls
- Enables downstream analytics without null handling

**Customer Segmentation**:

```python
# 9. RFM-Based Segmentation (Lines 122-129)
customer_summary = customer_summary.withColumn(
    "customer_segment",
    F.when(F.col("customer_lifetime_value") >= 1000, "Premium")
     .when(F.col("customer_lifetime_value") >= 500, "Gold")
     .when(F.col("customer_lifetime_value") >= 100, "Silver")
     .when(F.col("customer_lifetime_value") > 0, "Bronze")
     .otherwise("No Orders")
)
```

**Segment Definitions**:
- **Premium**: CLV ≥ $1,000 (top customers)
- **Gold**: CLV $500-999
- **Silver**: CLV $100-499
- **Bronze**: CLV $1-99
- **No Orders**: CLV = $0 (inactive)

**Use Cases**:
- Targeted marketing campaigns
- Loyalty program tiering
- Customer health monitoring
- Churn risk analysis

```python
# 10. Processing Metadata (Line 132)
customer_summary = customer_summary.withColumn("aggregated_at", F.current_timestamp())
```
- Tracks when aggregation ran
- Useful for audit trails and debugging

**Analytics Outputs**:

```python
# 11. Segment Distribution (Lines 143-145)
customer_summary.groupBy("customer_segment").count().orderBy(
    F.desc("count")
).show()
```
- Shows how many customers in each segment
- Executive dashboard metric

```python
# 12. Top Customers (Lines 148-151)
customer_summary.select(
    "customer_id", "name", "total_orders", "total_revenue", 
    "customer_lifetime_value", "customer_segment"
).orderBy(F.desc("customer_lifetime_value")).limit(5).show()
```
- Identifies VIP customers
- Supports account management strategies

**Write to Production**:

```python
# 13. Write to Main Branch (Lines 169-174)
spark.sql("""
    CREATE OR REPLACE TABLE nessie.ecommerce.customer_summary
    USING iceberg
    AS SELECT * FROM customer_summary_temp
""")
```
- **No @branch syntax**: Writes to default branch (main)
- Production-ready gold table
- Accessible to BI tools

**Business KPIs**:

```python
# 14. Calculate Business Metrics (Lines 182-191)
business_metrics = spark.sql("""
    SELECT 
        COUNT(*) as total_customers,
        SUM(total_orders) as total_orders,
        ROUND(SUM(total_revenue), 2) as total_revenue,
        ROUND(AVG(customer_lifetime_value), 2) as avg_customer_value,
        COUNT(CASE WHEN total_orders > 0 THEN 1 END) as active_customers,
        COUNT(CASE WHEN total_orders = 0 THEN 1 END) as inactive_customers
    FROM customer_summary_temp
""")
```

**KPIs Explained**:
- `total_customers`: Full customer base
- `active_customers`: Made at least 1 order
- `inactive_customers`: Never purchased
- `total_revenue`: Company total revenue
- `avg_customer_value`: Average CLV per customer

**Sample Output**:
```
Total Customers: 200
Active Customers: 151
Inactive Customers: 49
Total Orders: 1000
Total Revenue: $132,289.46
Avg Customer Value: $661.45
```

---

## 🔧 Utility Scripts

### scripts/utils/create_nessie_branches.py

**Purpose**: Creates bronze, silver, gold branches via Nessie HTTP API.

**Detailed Code Explanation**:

```python
# 1. Wait for Nessie (Lines 14-27)
def wait_for_nessie(max_retries=30):
    for i in range(max_retries):
        try:
            response = requests.get(f"{NESSIE_URL}/config", timeout=2)
            if response.status_code == 200:
                return True
        except:
            pass
        time.sleep(2)
```
- Polls Nessie `/config` endpoint until healthy
- Max 30 retries × 2 seconds = 60 seconds timeout
- Prevents race condition when Nessie is starting

```python
# 2. Get Branch Hash (Lines 41-53)
def get_branch_hash(branch_name):
    response = requests.get(f"{NESSIE_URL}/trees")
    for ref in data.get("references", []):
        if ref["name"] == branch_name:
            return ref["hash"]
```
- Fetches current commit hash of a branch
- Hash required to create new branches (parent reference)
- Format: SHA-256 hex string

**Nessie API Explained**:

```python
# 3. Create Branch V1 API (Lines 55-86)
def create_branch_v1(branch_name, source_hash):
    # Try format 1
    response = requests.put(
        f"{NESSIE_URL}/trees/branch/{branch_name}",
        json={"hash": source_hash}
    )
    
    # Try format 2
    response = requests.post(
        f"{NESSIE_URL}/trees/tree",
        json={"name": branch_name, "type": "BRANCH", "hash": source_hash}
    )
```

**Why Two Formats?**
- Nessie v1 API has multiple endpoint variations
- Different versions support different formats
- Script tries both for compatibility

**Branch Creation Parameters**:
- `name`: Branch name (bronze/silver/gold)
- `type`: "BRANCH" (vs "TAG")
- `hash`: Parent commit (typically main branch hash)

```python
# 4. Main Execution (Lines 88-142)
main_hash = get_branch_hash("main")

for branch_name in BRANCHES:
    if branch_name in existing_branches:
        print(f"○ Branch '{branch_name}' already exists")
    else:
        create_branch_v1(branch_name, main_hash)
```

**Branch Inheritance**:
- All branches created from `main` branch
- Start with same commit history
- Diverge as tables are created/modified

**Idempotency**:
- Safe to run multiple times
- Skips existing branches
- No errors if branches already exist

---

### scripts/utils/quality_checks.py

**Purpose**: Reusable data quality validation framework.

**Class Architecture**:

```python
class QualityChecker:
    def __init__(self, df: DataFrame, table_name: str):
        self.df = df
        self.table_name = table_name
        self.checks_passed = []
        self.checks_failed = []
```
- **Builder Pattern**: Chain check methods
- Accumulates results for comprehensive reporting
- Separates check execution from validation

**Check Methods**:

#### Row Count Validation
```python
def check_row_count(self, min_expected: int, max_expected: int = None):
    count = self.df.count()
    
    if count < min_expected:
        self.checks_failed.append({
            'check': 'row_count',
            'reason': f'Row count {count} below minimum {min_expected}'
        })
```
- **Use Case**: Detect data loss or unexpected volume changes
- **Example**: Silver should have ≥ 90% of bronze rows
- **Prevents**: Empty tables from breaking downstream

#### Null Validation
```python
def check_nulls(self, required_columns: List[str]):
    for col_name in required_columns:
        null_count = self.df.filter(F.col(col_name).isNull()).count()
        if null_count > 0:
            self.checks_failed.append({
                'check': 'null_check',
                'column': col_name,
                'reason': f'{null_count} null values found'
            })
```
- **Use Case**: Enforce NOT NULL constraints
- **Example**: `order_id`, `customer_id` must be present
- **Prevents**: Orphaned records, join failures

#### Duplicate Validation
```python
def check_duplicates(self, key_columns: List[str]):
    total_count = self.df.count()
    distinct_count = self.df.select(key_columns).distinct().count()
    duplicate_count = total_count - distinct_count
```
- **Use Case**: Ensure primary key uniqueness
- **Example**: Each `order_id` should appear once
- **Prevents**: Double-counting in aggregations

#### Value Range Validation
```python
def check_value_range(self, column: str, min_val=None, max_val=None):
    if min_val is not None:
        below_min = self.df.filter(F.col(column) < min_val).count()
```
- **Use Case**: Business rule enforcement
- **Example**: `total_amount` must be ≥ 0
- **Prevents**: Incorrect calculations, negative revenue

**Reporting**:

```python
def generate_report(self):
    print("✓ PASSED CHECKS: {len(self.checks_passed)}")
    for check in self.checks_passed:
        print(f"  ✓ {check['check']}: {details}")
    
    print("✗ FAILED CHECKS: {len(self.checks_failed)}")
    pass_rate = (len(self.checks_passed) / total * 100)
```

**Sample Output**:
```
==============================================================
QUALITY CHECK REPORT: orders_silver
==============================================================
✓ PASSED CHECKS: 4
  ✓ row_count: value=950, range=900 to unlimited
  ✓ null_check: column=order_id, nulls=0
  ✓ duplicate_check: keys=['order_id'], duplicates=0
  ✓ value_range: column=total_amount, range=0 to None

SUMMARY: 4/4 checks passed (100.0%)
==============================================================
```

**Exception Handling**:

```python
def validate(self, raise_on_failure=True):
    if self.checks_failed:
        if raise_on_failure:
            raise QualityCheckException(
                f"{len(self.checks_failed)} quality checks failed"
            )
```
- **Fail-Fast**: Stops pipeline on quality issues
- **Prevents**: Bad data from reaching gold layer
- **Enables**: Audit trail of what failed

---

## 📚 Documentation Files

### QUICKSTART.md

**Purpose**: Get from zero to working lakehouse in 5 minutes.

**Key Sections**:

1. **Prerequisites**: Docker, Python 3
2. **8-Step Workflow**:
   - Clone repo
   - Start services (`docker compose up -d`)
   - Create branches
   - Create namespace on silver
   - Bronze ingestion (2 tables)
   - Silver transformation (2 tables)
   - Gold aggregation (1 table)
   - Verification

3. **Verification Commands**:
```bash
curl http://localhost:19120/api/v1/trees/tree/bronze/entries | \
  python3 -c "import json, sys; ..."
```
- Lists tables on each branch
- Confirms isolation working

4. **Success Criteria**:
- Bronze: 2 tables, 1,200 records
- Silver: 2 tables, 1,200 validated records
- Gold: 1 table, 200 customer summaries
- All quality checks: 100% pass rate

### SETUP_GUIDE.md

**Purpose**: Comprehensive tutorial with detailed explanations.

**Coverage**:
- Manual setup from scratch
- Docker service explanations
- Sample data generation scripts
- Script implementation walkthroughs
- Testing and verification procedures
- Troubleshooting guide

**Audience**: Developers building similar systems

### plan/lakehouse_implementation_guide.md

**Purpose**: Technical specification and design decisions.

**Topics**:
- Architecture patterns
- Technology choices
- Data flow diagrams
- Best practices
- Production considerations

---

## 🔑 Key Concepts Explained

### Nessie Branch Syntax

**@branch notation**:
```sql
-- Read from specific branch
SELECT * FROM catalog.namespace.`table@branch`

-- Write to specific branch
CREATE TABLE catalog.namespace.`table@branch` AS ...
```

**Why backticks?**
- `@` is special character in SQL
- Backticks escape the table name
- Required for Nessie extensions

### Medallion Architecture

**Bronze Layer**:
- **Purpose**: Raw data ingestion
- **Quality**: No transformations
- **Schema**: As-is from source
- **Use**: Audit trail, reprocessing

**Silver Layer**:
- **Purpose**: Cleaned, validated data
- **Quality**: Deduplicated, standardized
- **Schema**: Type-safe, consistent
- **Use**: Analytics queries

**Gold Layer**:
- **Purpose**: Business aggregations
- **Quality**: Business-ready metrics
- **Schema**: Denormalized for BI
- **Use**: Dashboards, reports

### Write-Audit-Publish Pattern

**Pattern Steps**:
1. **Write**: Transform data to temp location
2. **Audit**: Run quality checks
3. **Publish**: Write to target branch if checks pass

**Benefits**:
- Prevents bad data from being published
- Atomic operations (all or nothing)
- Clear audit trail

### Iceberg Table Format

**Features**:
- **ACID Transactions**: Guaranteed consistency
- **Schema Evolution**: Add/modify columns safely
- **Time Travel**: Query historical snapshots
- **Partition Evolution**: Change partitioning without rewrites

**File Structure**:
```
warehouse/
  ecommerce/
    orders_bronze/
      data/
        00000-0-data.parquet
        00001-1-data.parquet
      metadata/
        v1.metadata.json
        v2.metadata.json
        snap-123.avro
```

### Version Control for Data

**Git-Like Operations**:
```bash
# Branch
Create bronze, silver, gold branches

# Commit
Each table write creates a commit

# Merge
Promote silver data to main

# History
Query any previous table state
```

---

## 🎯 Data Flow Summary

```
1. CSV Files
   ↓
2. Bronze Ingestion (PySpark)
   - Read CSV
   - Write to Iceberg
   - Commit to bronze branch
   ↓
3. Silver Transformation
   - Read from bronze@branch
   - Deduplicate
   - Validate quality
   - Write to silver@branch
   ↓
4. Gold Aggregation
   - Read from silver@branch
   - Join tables
   - Calculate metrics
   - Write to main branch
   ↓
5. BI Tools / Analytics
```

---

## 🔍 Production Considerations

**Scalability**:
- Spark cluster for distributed processing
- Partitioned Iceberg tables
- Compaction strategies

**Reliability**:
- Persistent Nessie catalog (PostgreSQL)
- Retry logic in scripts
- Quality check thresholds

**Security**:
- Authentication for Nessie API
- IAM roles for S3 access
- Encrypted communication

**Monitoring**:
- Quality check metrics
- Processing durations
- Data volume tracking

---

## 📖 Additional Resources

**Official Documentation**:
- [Apache Iceberg](https://iceberg.apache.org/)
- [Project Nessie](https://projectnessie.org/)
- [Apache Spark](https://spark.apache.org/)

**Related Concepts**:
- Data lakehouse architecture
- Data quality frameworks
- Modern data stack

---

*Last Updated: December 21, 2024*
*Version: 1.0*
