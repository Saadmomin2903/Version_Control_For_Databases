# Complete Implementation Guide: Git-Style Versioned Lakehouse
## Apache Iceberg + Project Nessie + Polars

---

## 📋 TABLE OF CONTENTS

1. [Project Overview](#overview)
2. [Knowledge Prerequisites](#knowledge)
3. [Prerequisites](#prerequisites)
4. [Phase 1: Infrastructure Setup](#phase1)
5. [Phase 2: Storage Configuration](#phase2)
6. [Phase 3: Python Environment](#phase3)
7. [Phase 4: Bronze Layer](#phase4)
8. [Phase 5: Silver Layer](#phase5)
9. [Phase 6: Gold Layer](#phase6)
10. [Phase 7: Quality Checks](#phase7)
11. [Phase 8: Orchestration](#phase8)
12. [Phase 9: Testing](#phase9)
13. [Phase 10: Production Deployment](#phase10)
14. [Quick Start Commands](#quickstart)
15. [Troubleshooting](#troubleshooting)

---

## 🎯 PROJECT OVERVIEW {#overview}

This guide implements a production-ready data lakehouse using:
- **Apache Iceberg**: Open table format with ACID transactions
- **Project Nessie**: Git-like version control for data
- **Polars**: Fast data transformation engine
- **MinIO**: S3-compatible object storage
- **Medallion Architecture**: Bronze → Silver → Gold layers

**Key Features:**
- Git-like branching for data
- Write-Audit-Publish pattern
- Time-travel queries
- Data quality gates
- Complete test coverage

---

## 📚 KNOWLEDGE PREREQUISITES {#knowledge}

Before starting this project, you should understand these concepts. Don't worry if you're not an expert - this guide will teach you as you go, but having a foundation will help significantly.

### 🎯 Essential Concepts (Must Know)

#### 1. **Python Programming**
**Why**: All scripts are written in Python

**What to Know:**
- Basic Python syntax (variables, functions, classes)
- Working with modules and imports
- File I/O operations
- Error handling (try/except)
- Working with dictionaries and lists

**Quick Check:**
```python
# Can you understand this?
import os
from datetime import datetime

def process_data(file_path):
    try:
        with open(file_path, 'r') as f:
            data = f.read()
        return data
    except FileNotFoundError:
        print(f"File not found: {file_path}")
        return None
```

**Learning Resources:**
- Python.org Tutorial: https://docs.python.org/3/tutorial/
- Real Python: https://realpython.com/
- **Time to Learn**: 1-2 weeks if beginner

---

#### 2. **Data Engineering Basics**
**Why**: This is a data engineering project

**What to Know:**
- **ETL/ELT**: Extract, Transform, Load processes
- **Data Pipelines**: Sequential data processing steps
- **Data Warehouses vs Data Lakes**: Different storage approaches
- **Data Quality**: Why it matters and how to check it

**Key Concepts:**
- **Raw Data**: Unprocessed data from source systems
- **Transformed Data**: Cleaned, validated, and enriched data
- **Analytics Data**: Aggregated data for reporting

**Learning Resources:**
- Data Engineering Podcast: https://www.dataengineeringpodcast.com/
- **Time to Learn**: 1 week of focused reading

---

#### 3. **Medallion Architecture**
**Why**: This project uses Bronze → Silver → Gold layers

**What to Know:**
- **Bronze Layer**: Raw, unprocessed data (as-is from source)
- **Silver Layer**: Cleaned, validated, and enriched data
- **Gold Layer**: Business-level aggregated data for analytics

**Analogy**: Think of it like refining oil:
- **Bronze** = Crude oil (raw)
- **Silver** = Refined oil (cleaned)
- **Gold** = Gasoline (ready to use)

**Visual Flow:**
```
Raw Data → Bronze → Silver → Gold
  CSV      Raw      Clean    Analytics
```

**Learning Resources:**
- Databricks Medallion Architecture: https://www.databricks.com/glossary/medallion-architecture
- **Time to Learn**: 1-2 hours of reading

---

#### 4. **Docker Basics**
**Why**: Infrastructure runs in Docker containers

**What to Know:**
- What Docker containers are
- Basic Docker commands:
  - `docker ps` - List running containers
  - `docker-compose up` - Start services
  - `docker logs` - View logs
- Understanding `docker-compose.yml` files

**Key Concepts:**
- **Container**: Isolated environment running an application
- **Image**: Template for creating containers
- **Volume**: Persistent storage for containers

**Learning Resources:**
- Docker Getting Started: https://docs.docker.com/get-started/
- Docker Compose Tutorial: https://docs.docker.com/compose/gettingstarted/
- **Time to Learn**: 2-3 hours hands-on

---

### 🔧 Important Concepts (Should Know)

#### 5. **Object Storage (S3/MinIO)**
**Why**: Data is stored in object storage

**What to Know:**
- **Object Storage**: Files stored as objects (not files in folders)
- **Buckets**: Containers for objects (like folders)
- **S3 API**: Standard interface for object storage
- **MinIO**: S3-compatible storage (we use it locally)

**Key Concepts:**
- Objects have keys (paths) and data
- Scalable and cost-effective
- Used by AWS S3, Google Cloud Storage, Azure Blob

**Learning Resources:**
- AWS S3 Documentation: https://docs.aws.amazon.com/s3/
- MinIO Quickstart: https://min.io/docs/minio/linux/index.html
- **Time to Learn**: 1-2 hours

---

#### 6. **DataFrames and Data Processing**
**Why**: We use Polars (similar to Pandas) for data transformations

**What to Know:**
- **DataFrame**: Tabular data structure (rows and columns)
- Basic operations:
  - Filtering rows
  - Selecting columns
  - Grouping and aggregating
  - Joining tables

**Example:**
```python
# Can you understand this?
df = pl.read_csv("data.csv")
filtered = df.filter(pl.col("amount") > 100)
grouped = filtered.group_by("category").agg(pl.sum("amount"))
```

**Learning Resources:**
- Polars User Guide: https://pola-rs.github.io/polars-book/
- Pandas Tutorial (similar concepts): https://pandas.pydata.org/docs/getting_started/
- **Time to Learn**: 1 week if new to data processing

---

#### 7. **Version Control (Git Concepts)**
**Why**: Nessie provides Git-like versioning for data

**What to Know:**
- **Branches**: Separate lines of development
- **Commits**: Snapshots of state
- **Merging**: Combining branches
- **Tags**: Marking important versions

**Key Difference:**
- **Git**: Versions code
- **Nessie**: Versions data (same concepts!)

**Learning Resources:**
- Git Basics: https://git-scm.com/book/en/v2/Getting-Started-Git-Basics
- **Time to Learn**: 2-3 hours

---

### 🚀 Advanced Concepts (Nice to Know)

#### 8. **Apache Iceberg**
**Why**: We use Iceberg as the table format

**What to Know:**
- **Table Format**: How data is organized and stored
- **ACID Transactions**: Atomic, Consistent, Isolated, Durable
- **Schema Evolution**: Changing table structure over time
- **Time Travel**: Querying data at a point in time

**Key Benefits:**
- Better performance for large datasets
- Schema evolution without breaking changes
- Time-travel queries

**Learning Resources:**
- Iceberg Documentation: https://iceberg.apache.org/docs/
- **Time to Learn**: 2-3 hours (you'll learn as you build)

---

#### 9. **REST APIs**
**Why**: Nessie uses REST API for operations

**What to Know:**
- **HTTP Methods**: GET, POST, PUT, DELETE
- **JSON**: Data format for API responses
- **Endpoints**: URLs for different operations

**Example:**
```python
# Can you understand this?
import requests
response = requests.get("http://localhost:19120/api/v2/config")
data = response.json()
```

**Learning Resources:**
- REST API Tutorial: https://restfulapi.net/
- **Time to Learn**: 1-2 hours

---

#### 10. **Data Quality**
**Why**: We implement quality checks

**What to Know:**
- **Data Validation**: Checking data meets requirements
- **Null Checks**: Ensuring required fields have values
- **Uniqueness**: Checking for duplicates
- **Range Checks**: Validating values are in expected ranges

**Learning Resources:**
- Data Quality Best Practices: https://www.datacamp.com/tutorial/data-quality
- **Time to Learn**: 1-2 hours

---

### 📊 Learning Path Recommendation

#### **If You're a Complete Beginner:**
1. **Week 1**: Learn Python basics (variables, functions, file I/O)
2. **Week 2**: Learn DataFrames (Pandas or Polars)
3. **Week 3**: Learn Docker basics
4. **Week 4**: Read about data engineering concepts
5. **Then**: Start this project!

#### **If You Know Python:**
1. **Day 1**: Learn Docker basics (2-3 hours)
2. **Day 2**: Learn about Medallion Architecture (1 hour)
3. **Day 3**: Learn Polars basics (2-3 hours)
4. **Then**: Start this project!

#### **If You're Experienced:**
1. **1-2 hours**: Review Iceberg and Nessie concepts
2. **Then**: Start this project!

---

### 🎓 Quick Learning Checklist

Before starting, you should be able to:

- [ ] Write a Python function that reads a CSV file
- [ ] Understand what a Docker container is
- [ ] Explain the difference between Bronze, Silver, and Gold layers
- [ ] Know what a DataFrame is and basic operations
- [ ] Understand what version control (Git) does
- [ ] Know what object storage (S3) is

**If you can check 4+ items, you're ready to start!**

---

### 💡 Learning While Building

**Good News**: You don't need to master everything before starting!

This guide is designed to teach you as you build:
- Each phase explains concepts as you implement them
- Code examples are well-commented
- Troubleshooting section helps when stuck

**Strategy:**
1. **Start with basics**: Learn Python and Docker if needed
2. **Begin the project**: Follow the guide step-by-step
3. **Learn as you go**: When you encounter something new, pause and learn it
4. **Iterate**: Build, test, learn, improve

---

### 📚 Recommended Learning Order

**Before Starting Project:**
1. ✅ Python basics (if needed)
2. ✅ Docker basics
3. ✅ Medallion Architecture concept

**During Project:**
- Learn Iceberg as you use it
- Learn Nessie as you use it
- Learn Polars as you transform data

**After Project:**
- Deep dive into Iceberg internals
- Learn advanced Nessie features
- Optimize for production

---

### 🆘 Where to Get Help

**If You're Stuck:**
1. **This Guide**: Check troubleshooting section
2. **Official Docs**: Links provided throughout
3. **Stack Overflow**: Tag questions with technology name
4. **Community**: Join Apache Iceberg/Nessie Slack/Discord

**Common Questions:**
- "I don't understand X concept" → Check learning resources above
- "Code doesn't work" → Check troubleshooting section
- "Want to learn more" → Follow links in resources section

---

### ✅ Ready to Start?

**Minimum Requirements:**
- Basic Python knowledge
- Understanding of what Docker is
- Willingness to learn as you go

**Ideal Requirements:**
- Comfortable with Python
- Know Docker basics
- Understand data processing concepts
- Familiar with data engineering terms

**Remember**: This is a learning project! It's okay to not know everything upfront. The guide will teach you along the way.

---

## ✅ PREREQUISITES {#prerequisites}

### Required Software Installation

#### Step 1: Install Docker Desktop
```bash
# Download and install from:
# https://www.docker.com/products/docker-desktop

# Verify installation:
docker --version
# Expected: Docker version 24.0.0 or higher

# Start Docker Desktop application
# Wait for Docker to be running (whale icon in system tray)
```

#### Step 2: Verify Python Installation
```bash
# Check Python version (must be 3.9 or higher)
python --version
# OR
python3 --version

# If Python is not installed:
# macOS: brew install python@3.11
# Linux: sudo apt-get install python3.9 python3-pip
# Windows: Download from python.org
```

#### Step 3: Install Git
```bash
# Verify Git installation
git --version

# If not installed:
# macOS: brew install git
# Linux: sudo apt-get install git
# Windows: Download from git-scm.com
```

#### Step 4: Install curl (for health checks)
```bash
# Verify curl installation
curl --version

# macOS/Linux: Usually pre-installed
# Windows: Included with Git for Windows
```

### System Requirements
- **RAM**: 8GB minimum, 16GB recommended
- **Disk Space**: 50GB free (for Docker images and data)
- **CPU**: Multi-core processor (4+ cores recommended)
- **OS**: macOS 10.15+, Linux (Ubuntu 20.04+), Windows 10/11

### Pre-Setup Verification Checklist
```bash
# Run these commands to verify everything is ready:
docker --version          # ✓ Docker installed
python --version          # ✓ Python 3.9+
git --version            # ✓ Git installed
curl --version           # ✓ curl available
docker ps                # ✓ Docker daemon running
```

---

## 🔐 CREDENTIAL MANAGEMENT {#credentials}

**IMPORTANT**: Before starting, decide on your credentials. For production, use strong passwords!

### Step 0.1: Create Environment Variables File

Create `.env` file in project root (this file should NOT be committed to git):

```bash
# Create .env file
cat > .env << EOF
# MinIO Configuration
MINIO_ROOT_USER=admin
MINIO_ROOT_PASSWORD=password123
S3_ENDPOINT=http://localhost:9000
S3_ACCESS_KEY=admin
S3_SECRET_KEY=password123
S3_BUCKET=lakehouse

# Nessie Configuration
NESSIE_URI=http://localhost:19120/api/v2
NESSIE_VERSION_STORE_TYPE=in-memory

# Project Configuration
NAMESPACE=ecommerce
BRONZE_BRANCH=bronze
SILVER_BRANCH=silver
GOLD_BRANCH=gold
EOF
```

**Security Note**: 
- For **development**: You can use simple passwords like `password123`
- For **production**: Generate strong passwords:
  ```bash
  # Generate secure password (Linux/Mac)
  openssl rand -base64 32
  
  # Or use a password manager
  ```

### Step 0.2: Create .gitignore

```bash
# Create .gitignore to protect sensitive files
cat > .gitignore << EOF
# Environment variables
.env
.env.local
.env.*.local

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
env/
ENV/
.venv

# IDE
.vscode/
.idea/
*.swp
*.swo

# Data
data/raw/*.csv
data/raw/*.parquet
*.db
*.sqlite

# Logs
logs/*.log
*.log

# OS
.DS_Store
Thumbs.db

# Docker
.dockerignore
EOF
```

---

## 🚀 PHASE 1: INFRASTRUCTURE SETUP {#phase1}

### Step 1.1: Create Project Structure

```bash
# Navigate to your workspace
cd ~/Documents  # or your preferred location

# Create main directory
mkdir -p lakehouse-project
cd lakehouse-project

# Create complete directory structure
mkdir -p config
mkdir -p data/raw
mkdir -p data/bronze
mkdir -p data/silver
mkdir -p data/gold
mkdir -p scripts/bronze
mkdir -p scripts/silver
mkdir -p scripts/gold
mkdir -p scripts/utils
mkdir -p logs
mkdir -p tests
mkdir -p notebooks
mkdir -p orchestration/dags

# Verify structure
tree -L 2  # If tree is installed
# OR
find . -type d -maxdepth 2 | sort
```

**Expected Output:**
```
.
├── config
├── data
│   ├── bronze
│   ├── gold
│   ├── raw
│   └── silver
├── logs
├── notebooks
├── orchestration
│   └── dags
├── scripts
│   ├── bronze
│   ├── gold
│   ├── silver
│   └── utils
└── tests
```

### Step 1.2: Create docker-compose.yml

Create `docker-compose.yml` in the project root:

```yaml
version: '3.8'

services:
  minio:
    image: minio/minio:latest
    container_name: lakehouse-minio
    ports:
      - "${MINIO_API_PORT:-9000}:9000"
      - "${MINIO_CONSOLE_PORT:-9001}:9001"
    environment:
      MINIO_ROOT_USER: ${MINIO_ROOT_USER:-admin}
      MINIO_ROOT_PASSWORD: ${MINIO_ROOT_PASSWORD:-password123}
    command: server /data --console-address ":9001"
    volumes:
      - minio-data:/data
    networks:
      - lakehouse-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
      interval: 30s
      timeout: 20s
      retries: 3
      start_period: 10s
    restart: unless-stopped

  nessie:
    image: projectnessie/nessie:latest
    container_name: lakehouse-nessie
    ports:
      - "${NESSIE_PORT:-19120}:19120"
    environment:
      QUARKUS_HTTP_PORT: 19120
      NESSIE_VERSION_STORE_TYPE: ${NESSIE_VERSION_STORE_TYPE:-in-memory}
    networks:
      - lakehouse-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:19120/api/v2/config"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 15s
    restart: unless-stopped

volumes:
  minio-data:
    driver: local

networks:
  lakehouse-network:
    driver: bridge
```

**Key Points:**
- Uses environment variables from `.env` file (with defaults)
- Health checks ensure services are ready before use
- `restart: unless-stopped` keeps services running after reboot
- Named volumes persist data between container restarts

### Step 1.3: Start Infrastructure

#### Step 1.3.1: Load Environment Variables and Start Services

```bash
# Ensure you're in the project root directory
cd ~/Documents/lakehouse-project  # Adjust path as needed

# Verify docker-compose.yml exists
ls -la docker-compose.yml

# Start services in detached mode
docker-compose up -d

# Expected output:
# Creating network "lakehouse-project_lakehouse-network" ... done
# Creating volume "lakehouse-project_minio-data" ... done
# Creating lakehouse-minio ... done
# Creating lakehouse-nessie ... done
```

#### Step 1.3.2: Verify Services Are Running

```bash
# Check container status
docker-compose ps

# Expected output (both should show "Up"):
# NAME                STATUS          PORTS
# lakehouse-minio     Up (healthy)    0.0.0.0:9000->9000/tcp, 0.0.0.0:9001->9001/tcp
# lakehouse-nessie    Up (healthy)    0.0.0.0:19120->19120/tcp
```

#### Step 1.3.3: Check Service Logs

```bash
# Check Nessie logs (should see "started in X.XXXs")
docker-compose logs nessie | tail -20

# Check MinIO logs (should see "API: http://0.0.0.0:9000")
docker-compose logs minio | tail -20

# Follow logs in real-time (Ctrl+C to exit)
docker-compose logs -f
```

#### Step 1.3.4: Test Service Connectivity

```bash
# Test Nessie API
curl http://localhost:19120/api/v2/config

# Expected: JSON response with Nessie configuration
# If you get "Connection refused", wait 10-15 seconds and try again

# Test MinIO health endpoint
curl http://localhost:9000/minio/health/live

# Expected: Empty response (200 OK)
```

#### Step 1.3.5: Access MinIO Console

1. **Open browser** and navigate to: `http://localhost:9001`
2. **Login credentials**:
   - Username: `admin` (or your MINIO_ROOT_USER from .env)
   - Password: `password123` (or your MINIO_ROOT_PASSWORD from .env)
3. **Verify**: You should see the MinIO dashboard

#### Step 1.3.6: Troubleshooting Service Startup

If services don't start:

```bash
# Check if ports are already in use
lsof -i :9000   # Check MinIO API port
lsof -i :9001   # Check MinIO Console port
lsof -i :19120  # Check Nessie port

# If ports are in use, either:
# 1. Stop the conflicting service
# 2. Change ports in docker-compose.yml and .env

# View detailed error logs
docker-compose logs

# Restart services
docker-compose restart

# Complete reset (WARNING: deletes all data)
docker-compose down -v
docker-compose up -d
```

---

## ⚙️ PHASE 2: STORAGE CONFIGURATION {#phase2}

### Step 2.1: Create config/iceberg_config.py

Create `config/iceberg_config.py` with environment variable support:

```python
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# MinIO/S3 Configuration (from .env or defaults)
S3_ENDPOINT = os.getenv("S3_ENDPOINT", "http://localhost:9000")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY", "admin")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY", "password123")
S3_BUCKET = os.getenv("S3_BUCKET", "lakehouse")

# Nessie Configuration
NESSIE_URI = os.getenv("NESSIE_URI", "http://localhost:19120/api/v2")

# Iceberg Catalog Configuration
CATALOG_CONFIG = {
    "type": "rest",
    "uri": NESSIE_URI,
    "warehouse": f"s3://{S3_BUCKET}/warehouse",
    "s3.endpoint": S3_ENDPOINT,
    "s3.access-key-id": S3_ACCESS_KEY,
    "s3.secret-access-key": S3_SECRET_KEY,
    "s3.path-style-access": "true",
    # Additional S3 settings for MinIO compatibility
    "s3.region": "us-east-1",  # MinIO doesn't care about region, but required
}

# Project Configuration
NAMESPACE = os.getenv("NAMESPACE", "ecommerce")
BRONZE_BRANCH = os.getenv("BRONZE_BRANCH", "bronze")
SILVER_BRANCH = os.getenv("SILVER_BRANCH", "silver")
GOLD_BRANCH = os.getenv("GOLD_BRANCH", "gold")

# Print configuration (without secrets) for verification
def print_config():
    print("=" * 60)
    print("LAKEHOUSE CONFIGURATION")
    print("=" * 60)
    print(f"S3 Endpoint: {S3_ENDPOINT}")
    print(f"S3 Bucket: {S3_BUCKET}")
    print(f"Nessie URI: {NESSIE_URI}")
    print(f"Namespace: {NAMESPACE}")
    print(f"Branches: {BRONZE_BRANCH}, {SILVER_BRANCH}, {GOLD_BRANCH}")
    print("=" * 60)

if __name__ == "__main__":
    print_config()
```

**Test the configuration:**
```bash
# Verify config loads correctly
python config/iceberg_config.py

# Expected output:
# ============================================================
# LAKEHOUSE CONFIGURATION
# ============================================================
# S3 Endpoint: http://localhost:9000
# S3 Bucket: lakehouse
# Nessie URI: http://localhost:19120/api/v2
# Namespace: ecommerce
# Branches: bronze, silver, gold
# ============================================================
```

### Step 2.2: Create scripts/utils/storage_utils.py

```python
from pyiceberg.catalog import load_catalog
from pyiceberg.schema import Schema
from pyiceberg.types import NestedField, StringType, IntegerType, TimestampType, DoubleType, BooleanType
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from config.iceberg_config import CATALOG_CONFIG, NAMESPACE

def get_catalog(branch="main"):
    config = CATALOG_CONFIG.copy()
    config["ref"] = branch
    return load_catalog("nessie", **config)

def create_namespace(catalog, namespace=NAMESPACE):
    try:
        catalog.create_namespace(namespace)
        print(f"✓ Created namespace: {namespace}")
    except Exception as e:
        if "already exists" in str(e).lower():
            print(f"✓ Namespace exists: {namespace}")
        else:
            raise

def table_exists(catalog, namespace, table_name):
    try:
        catalog.load_table(f"{namespace}.{table_name}")
        return True
    except:
        return False

def create_table_if_not_exists(catalog, namespace, table_name, schema):
    full_name = f"{namespace}.{table_name}"
    if table_exists(catalog, namespace, table_name):
        print(f"✓ Table exists: {full_name}")
        return catalog.load_table(full_name)
    
    table = catalog.create_table(identifier=full_name, schema=schema)
    print(f"✓ Created table: {full_name}")
    return table

# Schema Definitions
ORDERS_SCHEMA = Schema(
    NestedField(1, "order_id", StringType(), required=True),
    NestedField(2, "customer_id", StringType(), required=True),
    NestedField(3, "order_date", TimestampType(), required=True),
    NestedField(4, "total_amount", DoubleType(), required=True),
    NestedField(5, "status", StringType(), required=True),
    NestedField(6, "created_at", TimestampType(), required=True),
)

CUSTOMERS_SCHEMA = Schema(
    NestedField(1, "customer_id", StringType(), required=True),
    NestedField(2, "name", StringType(), required=True),
    NestedField(3, "email", StringType(), required=True),
    NestedField(4, "signup_date", TimestampType(), required=True),
    NestedField(5, "is_active", BooleanType(), required=True),
)
```

### Step 2.3: Setup MinIO and Nessie

#### Step 2.3.1: Create scripts/utils/setup_minio.py

```python
import sys
import os
from minio import Minio
from minio.error import S3Error

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from config.iceberg_config import S3_ENDPOINT, S3_ACCESS_KEY, S3_SECRET_KEY, S3_BUCKET

def setup_minio():
    """Create MinIO bucket if it doesn't exist"""
    print("=" * 60)
    print("SETTING UP MINIO")
    print("=" * 60)
    
    # Extract host and port from endpoint
    endpoint = S3_ENDPOINT.replace("http://", "").replace("https://", "")
    
    try:
        # Initialize MinIO client
        client = Minio(
            endpoint,
            access_key=S3_ACCESS_KEY,
            secret_key=S3_SECRET_KEY,
            secure=False  # Set to True for HTTPS
        )
        
        print(f"✓ Connected to MinIO at {S3_ENDPOINT}")
        
        # Check if bucket exists
        if client.bucket_exists(S3_BUCKET):
            print(f"✓ Bucket '{S3_BUCKET}' already exists")
else:
            # Create bucket
            client.make_bucket(S3_BUCKET)
            print(f"✓ Created bucket: {S3_BUCKET}")
        
        # Verify bucket is accessible
        if client.bucket_exists(S3_BUCKET):
            print(f"✓ Bucket '{S3_BUCKET}' is accessible")
            return True
        else:
            print(f"✗ Failed to verify bucket '{S3_BUCKET}'")
            return False
            
    except S3Error as e:
        print(f"✗ MinIO S3 Error: {e}")
        return False
    except Exception as e:
        print(f"✗ Error connecting to MinIO: {e}")
        print(f"  Endpoint: {S3_ENDPOINT}")
        print(f"  Bucket: {S3_BUCKET}")
        return False

if __name__ == "__main__":
    success = setup_minio()
    sys.exit(0 if success else 1)
```

#### Step 2.3.2: Create scripts/utils/setup_nessie.py

```python
import sys
import os
import requests
import time

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from config.iceberg_config import NESSIE_URI, BRONZE_BRANCH, SILVER_BRANCH, GOLD_BRANCH

def wait_for_nessie(max_retries=10, delay=2):
    """Wait for Nessie to be ready"""
    print("Waiting for Nessie to be ready...")
    for i in range(max_retries):
        try:
            response = requests.get(f"{NESSIE_URI}/config", timeout=5)
            if response.status_code == 200:
                print("✓ Nessie is ready")
                return True
        except requests.exceptions.RequestException:
            pass
        print(f"  Attempt {i+1}/{max_retries}...")
        time.sleep(delay)
    return False

def create_branch(branch_name, base_branch="main"):
    """Create a Nessie branch"""
    payload = {
        "name": branch_name,
        "type": "BRANCH",
        "hash": None  # Create from main branch
    }
    
    try:
        response = requests.post(
            f"{NESSIE_URI}/trees",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        if response.status_code in [200, 201]:
            print(f"✓ Created branch: {branch_name}")
            return True
        elif response.status_code == 409:
            print(f"✓ Branch '{branch_name}' already exists")
            return True
        else:
            print(f"✗ Failed to create branch '{branch_name}': {response.status_code}")
            print(f"  Response: {response.text}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"✗ Error creating branch '{branch_name}': {e}")
        return False

def list_branches():
    """List all Nessie branches"""
    try:
        response = requests.get(f"{NESSIE_URI}/trees", timeout=10)
        if response.status_code == 200:
            branches = response.json().get("references", [])
            return branches
        return []
    except Exception as e:
        print(f"✗ Error listing branches: {e}")
        return []

def setup_nessie():
    """Setup Nessie branches"""
    print("=" * 60)
    print("SETTING UP NESSIE")
    print("=" * 60)
    
    # Wait for Nessie to be ready
    if not wait_for_nessie():
        print("✗ Nessie is not accessible. Check if container is running.")
        return False
    
    # Create branches
    branches_to_create = [BRONZE_BRANCH, SILVER_BRANCH, GOLD_BRANCH]
    success = True
    
    for branch in branches_to_create:
        if not create_branch(branch):
            success = False
    
    # List all branches
    print("\n" + "=" * 60)
    print("AVAILABLE BRANCHES")
    print("=" * 60)
    all_branches = list_branches()
    for b in all_branches:
        branch_type = b.get('type', 'UNKNOWN')
        branch_name = b.get('name', 'UNNAMED')
        print(f"  - {branch_name} ({branch_type})")
    
    return success

if __name__ == "__main__":
    success = setup_nessie()
    sys.exit(0 if success else 1)
```

#### Step 2.3.3: Run Setup Scripts

```bash
# Ensure virtual environment is activated
source venv/bin/activate  # Linux/Mac
# OR
venv\Scripts\activate     # Windows

# Setup MinIO bucket
python scripts/utils/setup_minio.py

# Expected output:
# ============================================================
# SETTING UP MINIO
# ============================================================
# ✓ Connected to MinIO at http://localhost:9000
# ✓ Created bucket: lakehouse
# ✓ Bucket 'lakehouse' is accessible

# Setup Nessie branches
python scripts/utils/setup_nessie.py

# Expected output:
# ============================================================
# SETTING UP NESSIE
# ============================================================
# Waiting for Nessie to be ready...
# ✓ Nessie is ready
# ✓ Created branch: bronze
# ✓ Created branch: silver
# ✓ Created branch: gold
# ============================================================
# AVAILABLE BRANCHES
# ============================================================
#   - main (BRANCH)
#   - bronze (BRANCH)
#   - silver (BRANCH)
#   - gold (BRANCH)
```

---

## 🐍 PHASE 3: PYTHON ENVIRONMENT {#phase3}

### Step 3.1: Create requirements.txt

Create `requirements.txt` in the project root:

```txt
# Core Data Processing
pyiceberg==0.5.1
polars==0.20.0
pandas==2.1.4
pyarrow==14.0.1

# Storage & APIs
minio==7.2.0
boto3==1.34.0
requests==2.31.0

# Configuration
python-dotenv==1.0.0
pyyaml==6.0.1

# Testing
pytest==7.4.3
pytest-cov==4.1.0

# Utilities
tqdm==4.66.1  # Progress bars
```

**Note**: Pin versions for reproducibility. Update as needed for your environment.

### Step 3.2: Setup Virtual Environment

#### Step 3.2.1: Create Virtual Environment

```bash
# Navigate to project root
cd ~/Documents/lakehouse-project  # Adjust as needed

# Create virtual environment
python -m venv venv

# Verify venv directory was created
ls -la venv/  # Linux/Mac
# OR
dir venv      # Windows
```

#### Step 3.2.2: Activate Virtual Environment

**Linux/macOS:**
```bash
source venv/bin/activate

# Verify activation (prompt should show (venv))
which python
# Should show: .../lakehouse-project/venv/bin/python
```

**Windows:**
```cmd
venv\Scripts\activate

# Verify activation
where python
# Should show: ...\lakehouse-project\venv\Scripts\python.exe
```

**PowerShell (Windows):**
```powershell
venv\Scripts\Activate.ps1

# If you get execution policy error:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

#### Step 3.2.3: Upgrade pip and Install Dependencies

```bash
# Upgrade pip to latest version
pip install --upgrade pip

# Verify pip version (should be 23.0+)
pip --version

# Install all dependencies
pip install -r requirements.txt

# This will take 2-5 minutes depending on your internet speed
# Expected output shows packages being installed
```

#### Step 3.2.4: Verify Installation

```bash
# Test critical imports
python -c "import pyiceberg; print('✓ pyiceberg:', pyiceberg.__version__)"
python -c "import polars; print('✓ polars:', polars.__version__)"
python -c "import minio; print('✓ minio installed')"
python -c "from dotenv import load_dotenv; print('✓ python-dotenv installed')"

# List installed packages
pip list

# Expected: Should see all packages from requirements.txt
```

### Step 3.3: Initialize System

#### Step 3.3.1: Verify Services Are Running

```bash
# Check Docker containers
docker-compose ps

# Both services should show "Up (healthy)"
# If not, start them:
docker-compose up -d
```

#### Step 3.3.2: Run Setup Scripts

```bash
# Ensure you're in project root and venv is activated
pwd  # Should show .../lakehouse-project

# Setup MinIO bucket
python scripts/utils/setup_minio.py

# Verify: Should see "✓ Created bucket: lakehouse" or "✓ Bucket exists"

# Setup Nessie branches
python scripts/utils/setup_nessie.py

# Verify: Should see branches created (bronze, silver, gold)
```

#### Step 3.3.3: Test Configuration

```bash
# Test configuration loading
python config/iceberg_config.py

# Should print configuration without errors
```

### Step 3.4: Generate Sample Data

#### Step 3.4.1: Create scripts/utils/generate_sample_data.py

```python
import sys
import os
import polars as pl
from datetime import datetime, timedelta
import random

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

def generate_orders_data(num_records=1000, seed=42):
    """Generate sample orders data"""
    random.seed(seed)  # For reproducibility
    start_date = datetime(2024, 1, 1)
    
    data = {
        "order_id": [f"ORD{i:06d}" for i in range(1, num_records + 1)],
        "customer_id": [f"CUST{random.randint(1, 200):04d}" for _ in range(num_records)],
        "order_date": [start_date + timedelta(days=random.randint(0, 365)) for _ in range(num_records)],
        "total_amount": [round(random.uniform(10, 1000), 2) for _ in range(num_records)],
        "status": [random.choice(["pending", "completed", "cancelled", "refunded"]) for _ in range(num_records)],
        "created_at": [datetime.now() for _ in range(num_records)],
    }
    return pl.DataFrame(data)

def generate_customers_data(num_records=200, seed=42):
    """Generate sample customers data"""
    random.seed(seed)  # For reproducibility
    
    data = {
        "customer_id": [f"CUST{i:04d}" for i in range(1, num_records + 1)],
        "name": [f"Customer {i}" for i in range(1, num_records + 1)],
        "email": [f"customer{i}@example.com" for i in range(1, num_records + 1)],
        "signup_date": [datetime(2023, 1, 1) + timedelta(days=random.randint(0, 500)) for _ in range(num_records)],
        "is_active": [random.choice([True, False]) for _ in range(num_records)],
    }
    return pl.DataFrame(data)

def main():
    print("=" * 60)
    print("GENERATING SAMPLE DATA")
    print("=" * 60)
    
    # Ensure data/raw directory exists
os.makedirs("data/raw", exist_ok=True)
    
    # Generate orders data
    print("\nGenerating orders data...")
orders_df = generate_orders_data(1000)
    orders_path = "data/raw/orders.csv"
    orders_df.write_csv(orders_path)
    print(f"✓ Generated {orders_path}: {len(orders_df):,} records")
    print(f"  File size: {os.path.getsize(orders_path) / 1024:.2f} KB")
    
    # Generate customers data
    print("\nGenerating customers data...")
customers_df = generate_customers_data(200)
    customers_path = "data/raw/customers.csv"
    customers_df.write_csv(customers_path)
    print(f"✓ Generated {customers_path}: {len(customers_df):,} records")
    print(f"  File size: {os.path.getsize(customers_path) / 1024:.2f} KB")
    
    # Display sample data
    print("\n" + "=" * 60)
    print("SAMPLE ORDERS DATA (first 5 rows)")
    print("=" * 60)
    print(orders_df.head(5))
    
    print("\n" + "=" * 60)
    print("SAMPLE CUSTOMERS DATA (first 5 rows)")
    print("=" * 60)
    print(customers_df.head(5))
    
    # Data quality summary
    print("\n" + "=" * 60)
    print("DATA QUALITY SUMMARY")
    print("=" * 60)
    print(f"Orders:")
    print(f"  Total records: {len(orders_df):,}")
    print(f"  Unique order_ids: {orders_df['order_id'].n_unique():,}")
    print(f"  Date range: {orders_df['order_date'].min()} to {orders_df['order_date'].max()}")
    print(f"  Amount range: ${orders_df['total_amount'].min():.2f} - ${orders_df['total_amount'].max():.2f}")
    
    print(f"\nCustomers:")
    print(f"  Total records: {len(customers_df):,}")
    print(f"  Unique customer_ids: {customers_df['customer_id'].n_unique():,}")
    print(f"  Active customers: {customers_df['is_active'].sum()}")
    
    print("\n✓ Sample data generation complete!")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"✗ Error generating sample data: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
```

#### Step 3.4.2: Run Data Generation

```bash
# Ensure you're in project root with venv activated
python scripts/utils/generate_sample_data.py

# Expected output:
# ============================================================
# GENERATING SAMPLE DATA
# ============================================================
# 
# Generating orders data...
# ✓ Generated data/raw/orders.csv: 1,000 records
#   File size: XX.XX KB
# 
# Generating customers data...
# ✓ Generated data/raw/customers.csv: 200 records
#   File size: XX.XX KB
# 
# [Sample data preview...]
# 
# ✓ Sample data generation complete!
```

#### Step 3.4.3: Verify Generated Data

```bash
# Check files were created
ls -lh data/raw/

# Expected:
# -rw-r--r--  1 user  staff    XXK  ...  customers.csv
# -rw-r--r--  1 user  staff    XXK  ...  orders.csv

# Verify file contents (first few lines)
head -5 data/raw/orders.csv
head -5 data/raw/customers.csv

# Count lines (should be 1001 for orders.csv including header, 201 for customers.csv)
wc -l data/raw/*.csv
```

---

## 🥉 PHASE 4: BRONZE LAYER {#phase4}

### Step 4.1: Create scripts/bronze/ingest_orders.py

```python
import polars as pl
import sys
import os
from datetime import datetime

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from scripts.utils.storage_utils import get_catalog, create_namespace, create_table_if_not_exists, ORDERS_SCHEMA
from config.iceberg_config import NAMESPACE, BRONZE_BRANCH

def ingest_orders_to_bronze():
    print("Starting Bronze Orders Ingestion...")
    
    # Read raw data
    df = pl.read_csv("data/raw/orders.csv")
    print(f"✓ Loaded {len(df)} records")
    
    # Connect to Nessie
    catalog = get_catalog(branch=BRONZE_BRANCH)
    create_namespace(catalog, NAMESPACE)
    
    # Create table
    table = create_table_if_not_exists(catalog, NAMESPACE, "orders_bronze", ORDERS_SCHEMA)
    
    # Write data
    arrow_table = df.to_arrow()
    table.append(arrow_table)
    print(f"✓ Wrote {len(df)} records to Bronze")

if __name__ == "__main__":
    try:
        ingest_orders_to_bronze()
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
```

### Step 4.2: Create scripts/bronze/ingest_customers.py

```python
import polars as pl
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from scripts.utils.storage_utils import get_catalog, create_namespace, create_table_if_not_exists, CUSTOMERS_SCHEMA
from config.iceberg_config import NAMESPACE, BRONZE_BRANCH

def ingest_customers_to_bronze():
    print("Starting Bronze Customers Ingestion...")
    df = pl.read_csv("data/raw/customers.csv")
    print(f"✓ Loaded {len(df)} records")
    
    catalog = get_catalog(branch=BRONZE_BRANCH)
    create_namespace(catalog, NAMESPACE)
    table = create_table_if_not_exists(catalog, NAMESPACE, "customers_bronze", CUSTOMERS_SCHEMA)
    
    arrow_table = df.to_arrow()
    table.append(arrow_table)
    print(f"✓ Wrote {len(df)} records to Bronze")

if __name__ == "__main__":
    try:
        ingest_customers_to_bronze()
    except Exception as e:
        print(f"✗ Error: {e}")
        sys.exit(1)
```

### Step 4.3: Test Bronze Ingestion

```bash
python scripts/bronze/ingest_orders.py
python scripts/bronze/ingest_customers.py
```

---

## 🥈 PHASE 5: SILVER LAYER {#phase5}

### Step 5.1: Create scripts/silver/transform_orders.py

```python
import polars as pl
import sys
import os
from datetime import datetime
from pyiceberg.schema import Schema
from pyiceberg.types import NestedField, StringType, TimestampType, DoubleType, IntegerType

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from scripts.utils.storage_utils import get_catalog, create_namespace, create_table_if_not_exists
from config.iceberg_config import NAMESPACE, BRONZE_BRANCH, SILVER_BRANCH

ORDERS_SILVER_SCHEMA = Schema(
    NestedField(1, "order_id", StringType(), required=True),
    NestedField(2, "customer_id", StringType(), required=True),
    NestedField(3, "order_date", TimestampType(), required=True),
    NestedField(4, "total_amount", DoubleType(), required=True),
    NestedField(5, "status", StringType(), required=True),
    NestedField(6, "year", IntegerType(), required=True),
    NestedField(7, "month", IntegerType(), required=True),
    NestedField(8, "quarter", IntegerType(), required=True),
    NestedField(9, "is_completed", IntegerType(), required=True),
    NestedField(10, "processed_at", TimestampType(), required=True),
)

def transform_orders_to_silver():
    print("Starting Silver Orders Transformation...")
    
    # Read from Bronze
    bronze_catalog = get_catalog(branch=BRONZE_BRANCH)
    bronze_table = bronze_catalog.load_table(f"{NAMESPACE}.orders_bronze")
    df = pl.from_arrow(bronze_table.scan().to_arrow())
    print(f"✓ Loaded {len(df)} records from Bronze")
    
    # Clean data
    initial_count = len(df)
    df = df.unique(subset=["order_id"])
    df = df.filter(pl.col("total_amount") > 0)
    df = df.with_columns(pl.col("status").str.to_lowercase().str.strip_chars())
    print(f"✓ Cleaned data: {initial_count} → {len(df)} records")
    
    # Enrich data
    df = df.with_columns([
        pl.col("order_date").dt.year().alias("year"),
        pl.col("order_date").dt.month().alias("month"),
        pl.col("order_date").dt.quarter().alias("quarter"),
        pl.when(pl.col("status") == "completed").then(1).otherwise(0).alias("is_completed"),
        pl.lit(datetime.now()).alias("processed_at"),
    ])
    print(f"✓ Enriched data with derived columns")
    
    # Write to Silver
    silver_catalog = get_catalog(branch=SILVER_BRANCH)
    create_namespace(silver_catalog, NAMESPACE)
    silver_table = create_table_if_not_exists(silver_catalog, NAMESPACE, "orders_silver", ORDERS_SILVER_SCHEMA)
    
    arrow_table = df.to_arrow()
    silver_table.append(arrow_table)
    print(f"✓ Wrote {len(df)} records to Silver")

if __name__ == "__main__":
    try:
        transform_orders_to_silver()
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
```

### Step 5.2: Create scripts/silver/transform_customers.py

```python
import polars as pl
import sys
import os
from datetime import datetime
from pyiceberg.schema import Schema
from pyiceberg.types import NestedField, StringType, TimestampType, BooleanType

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from scripts.utils.storage_utils import get_catalog, create_namespace, create_table_if_not_exists
from config.iceberg_config import NAMESPACE, BRONZE_BRANCH, SILVER_BRANCH

CUSTOMERS_SILVER_SCHEMA = Schema(
    NestedField(1, "customer_id", StringType(), required=True),
    NestedField(2, "name", StringType(), required=True),
    NestedField(3, "email", StringType(), required=True),
    NestedField(4, "signup_date", TimestampType(), required=True),
    NestedField(5, "is_active", BooleanType(), required=True),
    NestedField(6, "email_domain", StringType(), required=True),
    NestedField(7, "processed_at", TimestampType(), required=True),
)

def transform_customers_to_silver():
    print("Starting Silver Customers Transformation...")
    
    bronze_catalog = get_catalog(branch=BRONZE_BRANCH)
    bronze_table = bronze_catalog.load_table(f"{NAMESPACE}.customers_bronze")
    df = pl.from_arrow(bronze_table.scan().to_arrow())
    print(f"✓ Loaded {len(df)} records")
    
    df = df.unique(subset=["customer_id"])
    df = df.filter(pl.col("email").is_not_null())
    df = df.with_columns([
        pl.col("email").str.to_lowercase(),
        pl.col("email").str.extract(r"@(.+)$", 1).alias("email_domain"),
        pl.lit(datetime.now()).alias("processed_at")
    ])
    print(f"✓ Cleaned and enriched data")
    
    silver_catalog = get_catalog(branch=SILVER_BRANCH)
    create_namespace(silver_catalog, NAMESPACE)
    silver_table = create_table_if_not_exists(silver_catalog, NAMESPACE, "customers_silver", CUSTOMERS_SILVER_SCHEMA)
    
    arrow_table = df.to_arrow()
    silver_table.append(arrow_table)
    print(f"✓ Wrote {len(df)} records to Silver")

if __name__ == "__main__":
    try:
        transform_customers_to_silver()
    except Exception as e:
        print(f"✗ Error: {e}")
        sys.exit(1)
```

### Step 5.3: Test Silver Transformations

```bash
python scripts/silver/transform_orders.py
python scripts/silver/transform_customers.py
```

---

## 🥇 PHASE 6: GOLD LAYER {#phase6}

### Step 6.1: Create scripts/gold/create_order_analytics.py

```python
import polars as pl
import sys
import os
from datetime import datetime
from pyiceberg.schema import Schema
from pyiceberg.types import NestedField, StringType, IntegerType, DoubleType, TimestampType

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from scripts.utils.storage_utils import get_catalog, create_namespace, create_table_if_not_exists
from config.iceberg_config import NAMESPACE, SILVER_BRANCH, GOLD_BRANCH

ORDER_ANALYTICS_SCHEMA = Schema(
    NestedField(1, "year", IntegerType(), required=True),
    NestedField(2, "month", IntegerType(), required=True),
    NestedField(3, "quarter", IntegerType(), required=True),
    NestedField(4, "status", StringType(), required=True),
    NestedField(5, "total_orders", IntegerType(), required=True),
    NestedField(6, "total_revenue", DoubleType(), required=True),
    NestedField(7, "avg_order_value", DoubleType(), required=True),
    NestedField(8, "created_at", TimestampType(), required=True),
)

def create_order_analytics():
    print("Starting Gold Order Analytics...")
    
    silver_catalog = get_catalog(branch=SILVER_BRANCH)
    silver_table = silver_catalog.load_table(f"{NAMESPACE}.orders_silver")
    df = pl.from_arrow(silver_table.scan().to_arrow())
    print(f"✓ Loaded {len(df)} records from Silver")
    
    analytics_df = df.group_by(["year", "month", "quarter", "status"]).agg([
        pl.count().alias("total_orders"),
        pl.sum("total_amount").alias("total_revenue"),
        pl.mean("total_amount").alias("avg_order_value"),
    ])
    
    analytics_df = analytics_df.with_columns([pl.lit(datetime.now()).alias("created_at")])
    print(f"✓ Created {len(analytics_df)} aggregated rows")
    
    gold_catalog = get_catalog(branch=GOLD_BRANCH)
    create_namespace(gold_catalog, NAMESPACE)
    gold_table = create_table_if_not_exists(gold_catalog, NAMESPACE, "order_analytics", ORDER_ANALYTICS_SCHEMA)
    
    arrow_table = analytics_df.to_arrow()
    gold_table.append(arrow_table)
    print(f"✓ Wrote {len(analytics_df)} analytics to Gold")

if __name__ == "__main__":
    try:
        create_order_analytics()
    except Exception as e:
        print(f"✗ Error: {e}")
        sys.exit(1)
```

### Step 6.2: Create scripts/gold/create_customer_analytics.py

```python
import polars as pl
import sys
import os
from datetime import datetime
from pyiceberg.schema import Schema
from pyiceberg.types import NestedField, StringType, IntegerType, DoubleType, TimestampType

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from scripts.utils.storage_utils import get_catalog, create_namespace, create_table_if_not_exists
from config.iceberg_config import NAMESPACE, SILVER_BRANCH, GOLD_BRANCH

CUSTOMER_ANALYTICS_SCHEMA = Schema(
    NestedField(1, "customer_id", StringType(), required=True),
    NestedField(2, "customer_name", StringType(), required=True),
    NestedField(3, "total_orders", IntegerType(), required=True),
    NestedField(4, "total_spent", DoubleType(), required=True),
    NestedField(5, "avg_order_value", DoubleType(), required=True),
    NestedField(6, "created_at", TimestampType(), required=True),
)

def create_customer_analytics():
    print("Starting Gold Customer Analytics...")
    
    silver_catalog = get_catalog(branch=SILVER_BRANCH)
    customers_table = silver_catalog.load_table(f"{NAMESPACE}.customers_silver")
    customers_df = pl.from_arrow(customers_table.scan().to_arrow())
    
    orders_table = silver_catalog.load_table(f"{NAMESPACE}.orders_silver")
    orders_df = pl.from_arrow(orders_table.scan().to_arrow())
    print(f"✓ Loaded customers and orders")
    
    order_metrics = orders_df.group_by("customer_id").agg([
        pl.count().alias("total_orders"),
        pl.sum("total_amount").alias("total_spent"),
        pl.mean("total_amount").alias("avg_order_value"),
    ])
    
    analytics_df = customers_df.join(order_metrics, on="customer_id", how="inner")
    analytics_df = analytics_df.select([
        pl.col("customer_id"),
        pl.col("name").alias("customer_name"),
        pl.col("total_orders"),
        pl.col("total_spent"),
        pl.col("avg_order_value"),
        pl.lit(datetime.now()).alias("created_at"),
    ])
    print(f"✓ Created analytics for {len(analytics_df)} customers")
    
    gold_catalog = get_catalog(branch=GOLD_BRANCH)
    create_namespace(gold_catalog, NAMESPACE)
    gold_table = create_table_if_not_exists(gold_catalog, NAMESPACE, "customer_analytics", CUSTOMER_ANALYTICS_SCHEMA)
    
    arrow_table = analytics_df.to_arrow()
    gold_table.append(arrow_table)
    print(f"✓ Wrote {len(analytics_df)} customer analytics to Gold")

if __name__ == "__main__":
    try:
        create_customer_analytics()
    except Exception as e:
        print(f"✗ Error: {e}")
        sys.exit(1)
```

### Step 6.3: Test Gold Layer

```bash
python scripts/gold/create_order_analytics.py
python scripts/gold/create_customer_analytics.py
```

---

## ✅ PHASE 7: QUALITY CHECKS {#phase7}

### Step 7.1: Create scripts/utils/quality_checks.py

```python
import polars as pl
from typing import List

class DataQualityCheck:
    def __init__(self, table_name: str):
        self.table_name = table_name
        self.checks_passed = []
        self.checks_failed = []
    
    def check_row_count(self, df: pl.DataFrame, min_rows: int = 1) -> bool:
        row_count = len(df)
        if row_count >= min_rows:
            self.checks_passed.append(f"✓ Row count: {row_count} >= {min_rows}")
            return True
        else:
            self.checks_failed.append(f"✗ Row count: {row_count} < {min_rows}")
            return False
    
    def check_no_nulls(self, df: pl.DataFrame, columns: List[str]) -> bool:
        all_passed = True
        for col in columns:
            null_count = df[col].null_count()
            if null_count == 0:
                self.checks_passed.append(f"✓ No nulls in {col}")
            else:
                self.checks_failed.append(f"✗ {null_count} nulls in {col}")
                all_passed = False
        return all_passed
    
    def check_unique(self, df: pl.DataFrame, column: str) -> bool:
        total = len(df)
        unique = df[column].n_unique()
        if total == unique:
            self.checks_passed.append(f"✓ All unique in {column}")
            return True
        else:
            self.checks_failed.append(f"✗ {total - unique} duplicates in {column}")
            return False
    
    def print_report(self) -> bool:
        print(f"\n{'='*60}")
        print(f"Quality Report: {self.table_name}")
        print(f"{'='*60}")
        
        print(f"\nPASSED ({len(self.checks_passed)}):")
        for check in self.checks_passed:
            print(f"  {check}")
        
        if self.checks_failed:
            print(f"\nFAILED ({len(self.checks_failed)}):")
            for check in self.checks_failed:
                print(f"  {check}")
        
        print(f"\n{'='*60}\n")
        return len(self.checks_failed) == 0

def run_bronze_quality_checks(df: pl.DataFrame) -> bool:
    qc = DataQualityCheck("orders_bronze")
    qc.check_row_count(df, min_rows=1)
    qc.check_no_nulls(df, ["order_id", "customer_id", "total_amount"])
    qc.check_unique(df, "order_id")
    return qc.print_report()
```

---

## 🔄 PHASE 8: ORCHESTRATION {#phase8}

### Step 8.1: Create Master Pipeline

Create `scripts/run_full_pipeline.py`:

```python
import sys
import os
from datetime import datetime

sys.path.append(os.path.dirname(__file__))

from bronze.ingest_orders import ingest_orders_to_bronze
from bronze.ingest_customers import ingest_customers_to_bronze
from silver.transform_orders import transform_orders_to_silver
from silver.transform_customers import transform_customers_to_silver
from gold.create_order_analytics import create_order_analytics
from gold.create_customer_analytics import create_customer_analytics

def run_full_pipeline():
    print("\n" + "="*70)
    print(" FULL LAKEHOUSE PIPELINE")
    print("="*70)
    print(f"Start: {datetime.now()}\n")
    
    stages = [
        ("Bronze - Orders", ingest_orders_to_bronze),
        ("Bronze - Customers", ingest_customers_to_bronze),
        ("Silver - Orders", transform_orders_to_silver),
        ("Silver - Customers", transform_customers_to_silver),
        ("Gold - Order Analytics", create_order_analytics),
        ("Gold - Customer Analytics", create_customer_analytics),
    ]
    
    for stage_name, stage_func in stages:
        print(f"\n{'='*70}")
        print(f"STAGE: {stage_name}")
        print(f"{'='*70}\n")
        
        try:
            stage_func()
            print(f"\n✓ {stage_name} completed")
        except Exception as e:
            print(f"\n✗ {stage_name} failed: {e}")
            sys.exit(1)
    
    print(f"\n{'='*70}")
    print("✓ PIPELINE COMPLETED SUCCESSFULLY")
    print(f"End: {datetime.now()}")
    print(f"{'='*70}\n")

if __name__ == "__main__":
    run_full_pipeline()
```

### Step 8.2: Test Full Pipeline

```bash
python scripts/run_full_pipeline.py
```

---

## 🧪 PHASE 9: TESTING {#phase9}

### Step 9.1: Create Test Suite

Create `tests/test_pipeline.py`:

```python
import unittest
import polars as pl
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from scripts.utils.storage_utils import get_catalog, table_exists
from config.iceberg_config import NAMESPACE, BRONZE_BRANCH, SILVER_BRANCH, GOLD_BRANCH

class TestPipeline(unittest.TestCase):
    
    def test_bronze_tables_exist(self):
        catalog = get_catalog(branch=BRONZE_BRANCH)
        self.assertTrue(table_exists(catalog, NAMESPACE, "orders_bronze"))
        self.assertTrue(table_exists(catalog, NAMESPACE, "customers_bronze"))
    
    def test_bronze_has_data(self):
        catalog = get_catalog(branch=BRONZE_BRANCH)
        table = catalog.load_table(f"{NAMESPACE}.orders_bronze")
        df = pl.from_arrow(table.scan().to_arrow())
        self.assertGreater(len(df), 0)
    
    def test_silver_tables_exist(self):
        catalog = get_catalog(branch=SILVER_BRANCH)
        self.assertTrue(table_exists(catalog, NAMESPACE, "orders_silver"))
        self.assertTrue(table_exists(catalog, NAMESPACE, "customers_silver"))
    
    def test_gold_tables_exist(self):
        catalog = get_catalog(branch=GOLD_BRANCH)
        self.assertTrue(table_exists(catalog, NAMESPACE, "order_analytics"))
        self.assertTrue(table_exists(catalog, NAMESPACE, "customer_analytics"))
    
    def test_data_quality(self):
        catalog = get_catalog(branch=SILVER_BRANCH)
        table = catalog.load_table(f"{NAMESPACE}.orders_silver")
        df = pl.from_arrow(table.scan().to_arrow())
        
        # Check required columns exist
        self.assertIn("order_id", df.columns)
        self.assertIn("year", df.columns)
        self.assertIn("month", df.columns)
        
        # Check no nulls in key columns
        self.assertEqual(df["order_id"].null_count(), 0)
        
        # Check value ranges
        self.assertTrue((df["month"] >= 1).all() and (df["month"] <= 12).all())

if __name__ == "__main__":
    unittest.main()
```

### Step 9.2: Run Tests

```bash
python tests/test_pipeline.py
```

---

## 🚀 PHASE 10: PRODUCTION DEPLOYMENT {#phase10}

### Step 10.1: Query Utilities

Create `scripts/utils/query_tables.py`:

```python
import sys
import os
import polars as pl

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from scripts.utils.storage_utils import get_catalog
from config.iceberg_config import NAMESPACE

def query_table(branch: str, table_name: str, limit: int = 10):
    print(f"\nQuerying {NAMESPACE}.{table_name} on branch '{branch}'")
    print(f"{'='*60}\n")
    
    try:
        catalog = get_catalog(branch=branch)
        table = catalog.load_table(f"{NAMESPACE}.{table_name}")
        
        data = table.scan().to_arrow()
        df = pl.from_arrow(data)
        
        print(f"Total Records: {len(df)}")
        print(f"\nFirst {min(limit, len(df))} rows:")
        print(df.head(limit))
        
        return df
    except Exception as e:
        print(f"✗ Error: {e}")
        return None

if __name__ == "__main__":
    print("=== BRONZE LAYER ===")
    query_table("bronze", "orders_bronze", limit=5)
    
    print("\n=== SILVER LAYER ===")
    query_table("silver", "orders_silver", limit=5)
    
    print("\n=== GOLD LAYER ===")
    query_table("gold", "order_analytics", limit=10)
```

### Step 10.2: Monitoring Dashboard

Create `scripts/utils/monitoring.py`:

```python
import requests
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from scripts.utils.storage_utils import get_catalog
from config.iceberg_config import NAMESPACE

def check_infrastructure():
    print("\n" + "="*60)
    print(" INFRASTRUCTURE HEALTH")
    print("="*60 + "\n")
    
    # Check Nessie
    try:
        response = requests.get("http://localhost:19120/api/v2/config", timeout=5)
        if response.status_code == 200:
            print("✓ Nessie: Running")
        else:
            print(f"✗ Nessie: Status {response.status_code}")
    except:
        print("✗ Nessie: Not accessible")
    
    # Check MinIO
    try:
        response = requests.get("http://localhost:9000/minio/health/live", timeout=5)
        if response.status_code == 200:
            print("✓ MinIO: Running")
        else:
            print(f"✗ MinIO: Status {response.status_code}")
    except:
        print("✗ MinIO: Not accessible")

def check_tables():
    print("\n" + "="*60)
    print(" TABLE STATISTICS")
    print("="*60 + "\n")
    
    tables = [
        ("bronze", "orders_bronze"),
        ("bronze", "customers_bronze"),
        ("silver", "orders_silver"),
        ("silver", "customers_silver"),
        ("gold", "order_analytics"),
        ("gold", "customer_analytics"),
    ]
    
    for branch, table_name in tables:
        try:
            catalog = get_catalog(branch=branch)
            table = catalog.load_table(f"{NAMESPACE}.{table_name}")
            data = table.scan().to_arrow()
            print(f"{branch}/{table_name}: {len(data):,} records")
        except Exception as e:
            print(f"{branch}/{table_name}: ✗ Error - {e}")

if __name__ == "__main__":
    check_infrastructure()
    check_tables()
    print()
```

---

## ⚡ QUICK START COMMANDS {#quickstart}

### Complete Setup Script (One-Time)

Create `setup.sh` (Linux/Mac) or `setup.bat` (Windows) for automated setup:

**Linux/Mac (`setup.sh`):**
```bash
#!/bin/bash
set -e  # Exit on error

echo "=========================================="
echo "LAKEHOUSE SETUP"
echo "=========================================="

# 1. Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file..."
    cat > .env << EOF
MINIO_ROOT_USER=admin
MINIO_ROOT_PASSWORD=password123
S3_ENDPOINT=http://localhost:9000
S3_ACCESS_KEY=admin
S3_SECRET_KEY=password123
S3_BUCKET=lakehouse
NESSIE_URI=http://localhost:19120/api/v2
NAMESPACE=ecommerce
BRONZE_BRANCH=bronze
SILVER_BRANCH=silver
GOLD_BRANCH=gold
EOF
    echo "✓ Created .env file"
else
    echo "✓ .env file already exists"
fi

# 2. Start Docker services
echo ""
echo "Starting Docker services..."
docker-compose up -d
sleep 10  # Wait for services to start

# 3. Setup Python environment
echo ""
echo "Setting up Python environment..."
python -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 4. Initialize storage
echo ""
echo "Initializing storage..."
python scripts/utils/setup_minio.py
python scripts/utils/setup_nessie.py

# 5. Generate sample data
echo ""
echo "Generating sample data..."
python scripts/utils/generate_sample_data.py

echo ""
echo "=========================================="
echo "✓ SETUP COMPLETE!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Activate virtual environment: source venv/bin/activate"
echo "  2. Run pipeline: python scripts/run_full_pipeline.py"
echo "  3. Query data: python scripts/utils/query_tables.py"
```

**Windows (`setup.bat`):**
```batch
@echo off
echo ==========================================
echo LAKEHOUSE SETUP
echo ==========================================

REM 1. Create .env file
if not exist .env (
    echo Creating .env file...
    (
        echo MINIO_ROOT_USER=admin
        echo MINIO_ROOT_PASSWORD=password123
        echo S3_ENDPOINT=http://localhost:9000
        echo S3_ACCESS_KEY=admin
        echo S3_SECRET_KEY=password123
        echo S3_BUCKET=lakehouse
        echo NESSIE_URI=http://localhost:19120/api/v2
        echo NAMESPACE=ecommerce
        echo BRONZE_BRANCH=bronze
        echo SILVER_BRANCH=silver
        echo GOLD_BRANCH=gold
    ) > .env
    echo ✓ Created .env file
) else (
    echo ✓ .env file already exists
)

REM 2. Start Docker services
echo.
echo Starting Docker services...
docker-compose up -d
timeout /t 10 /nobreak

REM 3. Setup Python environment
echo.
echo Setting up Python environment...
python -m venv venv
call venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt

REM 4. Initialize storage
echo.
echo Initializing storage...
python scripts\utils\setup_minio.py
python scripts\utils\setup_nessie.py

REM 5. Generate sample data
echo.
echo Generating sample data...
python scripts\utils\generate_sample_data.py

echo.
echo ==========================================
echo ✓ SETUP COMPLETE!
echo ==========================================
pause
```

**Run setup:**
```bash
# Linux/Mac
chmod +x setup.sh
./setup.sh

# Windows
setup.bat
```

### Daily Workflow Commands

#### Start Your Work Session

```bash
# 1. Navigate to project
cd ~/Documents/lakehouse-project

# 2. Activate virtual environment
source venv/bin/activate  # Linux/Mac
# OR
venv\Scripts\activate     # Windows

# 3. Verify services are running
docker-compose ps

# 4. Check system health
python scripts/utils/monitoring.py
```

#### Run Pipeline

```bash
# Run full pipeline (recommended)
python scripts/run_full_pipeline.py

# Or run individual stages
python scripts/bronze/ingest_orders.py
python scripts/bronze/ingest_customers.py
python scripts/silver/transform_orders.py
python scripts/silver/transform_customers.py
python scripts/gold/create_order_analytics.py
python scripts/gold/create_customer_analytics.py
```

#### Query and Monitor

```bash
# Query all tables
python scripts/utils/query_tables.py

# Query specific table
python -c "
from scripts.utils.query_tables import query_table
query_table('bronze', 'orders_bronze', limit=10)
"

# Check system health
python scripts/utils/monitoring.py

# Run tests
python tests/test_pipeline.py
# OR
pytest tests/ -v
```

#### Stop Services

```bash
# Stop services (keeps data)
docker-compose stop

# Stop and remove containers (keeps volumes/data)
docker-compose down

# Stop and remove everything including data (WARNING: deletes all data)
docker-compose down -v
```

---

## 🔧 TROUBLESHOOTING {#troubleshooting}

### Problem: Docker containers won't start

**Symptoms:**
- `docker-compose up -d` fails
- Containers show as "Exited" or "Restarting"
- Port already in use errors

**Solutions:**

```bash
# 1. Check Docker is running
docker info
# If this fails, start Docker Desktop application

# 2. Check for port conflicts
lsof -i :9000   # MinIO API
lsof -i :9001   # MinIO Console
lsof -i :19120  # Nessie

# If ports are in use:
# Option A: Stop the conflicting service
# Option B: Change ports in docker-compose.yml and .env

# 3. Check container logs for errors
docker-compose logs minio
docker-compose logs nessie

# 4. Remove old containers and restart
docker-compose down -v
docker-compose up -d

# 5. Verify containers are healthy
docker-compose ps
# Wait 30 seconds, then check again
```

**Common Issues:**
- **Port already in use**: Another service is using the port. Change ports in `.env` and `docker-compose.yml`
- **Insufficient memory**: Increase Docker Desktop memory allocation (Settings → Resources → Memory)
- **Permission denied**: On Linux, add user to docker group: `sudo usermod -aG docker $USER`

### Problem: Cannot connect to Nessie

**Symptoms:**
- `Connection refused` errors
- `404 Not Found` when accessing API
- Scripts fail with Nessie connection errors

**Solutions:**

```bash
# 1. Verify Nessie container is running
docker ps | grep nessie
# Should show lakehouse-nessie as "Up"

# 2. Check Nessie health
curl http://localhost:19120/api/v2/config
# Expected: JSON response

# 3. Check Nessie logs
docker logs lakehouse-nessie --tail 50
# Look for errors or startup messages

# 4. Restart Nessie
docker-compose restart nessie
sleep 15  # Wait for startup
curl http://localhost:19120/api/v2/config

# 5. Complete reset (if needed)
docker-compose down
docker-compose up -d nessie
```

**Common Issues:**
- **Container not ready**: Wait 15-20 seconds after starting
- **Network issues**: Ensure containers are on same network: `docker network ls`
- **Version mismatch**: Ensure using compatible Nessie version

### Problem: MinIO access denied

**Symptoms:**
- `Access Denied` errors
- Cannot create buckets
- Authentication failures

**Solutions:**

```bash
# 1. Verify credentials in .env file
cat .env | grep MINIO

# 2. Verify credentials match in:
#    - .env file
#    - docker-compose.yml
#    - config/iceberg_config.py

# 3. Test MinIO connection
python -c "
from minio import Minio
client = Minio('localhost:9000', 
               access_key='admin', 
               secret_key='password123', 
               secure=False)
print('Connected:', client.bucket_exists('lakehouse'))
"

# 4. Access MinIO console
# Open: http://localhost:9001
# Login with credentials from .env

# 5. Reset MinIO (WARNING: deletes all data)
docker-compose down
docker volume rm lakehouse-project_minio-data
docker-compose up -d
python scripts/utils/setup_minio.py
```

**Common Issues:**
- **Wrong credentials**: Double-check `.env` file values
- **Bucket doesn't exist**: Run `python scripts/utils/setup_minio.py`
- **SSL/TLS issues**: Ensure `secure=False` for local MinIO

### Problem: Module not found errors

**Symptoms:**
- `ModuleNotFoundError: No module named 'pyiceberg'`
- Import errors in scripts
- `python-dotenv` not found

**Solutions:**

```bash
# 1. Verify virtual environment is activated
which python  # Linux/Mac
# Should show: .../venv/bin/python

where python   # Windows
# Should show: ...\venv\Scripts\python.exe

# If not activated:
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate    # Windows

# 2. Verify packages are installed
pip list | grep pyiceberg
pip list | grep polars

# 3. Reinstall requirements
pip install --upgrade pip
pip install -r requirements.txt

# 4. Verify critical imports
python -c "import pyiceberg; print('✓ pyiceberg OK')"
python -c "import polars; print('✓ polars OK')"
python -c "from dotenv import load_dotenv; print('✓ dotenv OK')"

# 5. If still failing, recreate venv
deactivate  # Exit current venv
rm -rf venv  # Linux/Mac
# OR
rmdir /s venv  # Windows
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate
pip install -r requirements.txt
```

**Common Issues:**
- **Wrong Python version**: Ensure Python 3.9+ (`python --version`)
- **Virtual environment not activated**: Always activate before running scripts
- **Corrupted installation**: Recreate virtual environment

### Problem: Table not found

**Symptoms:**
- `TableNotFoundException`
- Scripts fail when loading tables
- Tables don't appear in queries

**Solutions:**

```bash
# 1. Verify branch exists
curl http://localhost:19120/api/v2/trees
# Should list branches including bronze, silver, gold

# 2. Check if table was created
python -c "
from scripts.utils.storage_utils import get_catalog, table_exists
from config.iceberg_config import NAMESPACE, BRONZE_BRANCH
catalog = get_catalog(branch=BRONZE_BRANCH)
print('Table exists:', table_exists(catalog, NAMESPACE, 'orders_bronze'))
"

# 3. List all tables in namespace
python -c "
from scripts.utils.storage_utils import get_catalog
from config.iceberg_config import NAMESPACE, BRONZE_BRANCH
catalog = get_catalog(branch=BRONZE_BRANCH)
tables = catalog.list_tables(NAMESPACE)
print('Tables:', list(tables))
"

# 4. Re-run ingestion
python scripts/bronze/ingest_orders.py
python scripts/bronze/ingest_customers.py

# 5. Verify data was written
python scripts/utils/query_tables.py
```

**Common Issues:**
- **Wrong branch**: Verify branch name in script matches Nessie branch
- **Namespace mismatch**: Check NAMESPACE in `iceberg_config.py`
- **Data not ingested**: Re-run ingestion scripts

### Problem: Quality checks failing

**Symptoms:**
- Quality check reports show failures
- Null values in required columns
- Duplicate records

**Solutions:**

```python
# Debug data issues
import polars as pl

# Load raw data
df = pl.read_csv("data/raw/orders.csv")

# Check schema
print("Schema:")
print(df.schema)

# Check statistics
print("\nStatistics:")
print(df.describe())

# Check nulls
print("\nNull counts:")
print(df.null_count())

# Check duplicates
print("\nDuplicates:")
print(f"Total rows: {len(df)}")
print(f"Unique order_ids: {df['order_id'].n_unique()}")

# Check value ranges
print("\nValue ranges:")
print(f"Amount range: {df['total_amount'].min()} - {df['total_amount'].max()}")
print(f"Date range: {df['order_date'].min()} - {df['order_date'].max()}")

# Check specific issues
print("\nStatus distribution:")
print(df['status'].value_counts())
```

**Common Issues:**
- **Data quality issues in source**: Clean data before ingestion
- **Schema mismatch**: Verify schema matches data types
- **Missing required fields**: Ensure all required columns have values

### Problem: Out of memory

**Symptoms:**
- `MemoryError` exceptions
- Docker containers killed
- System becomes unresponsive

**Solutions:**

```bash
# 1. Increase Docker memory allocation
# Docker Desktop → Settings → Resources → Memory
# Recommended: 8GB minimum, 16GB for large datasets

# 2. Process data in batches
# Modify scripts to process data in chunks:
python -c "
import polars as pl
chunk_size = 10000
for i in range(0, 100000, chunk_size):
    df = pl.read_csv('data/raw/orders.csv', skip_rows=i, n_rows=chunk_size)
    # Process chunk...
"

# 3. Use streaming/scan operations
# Instead of loading all data:
# df = pl.read_csv("file.csv")  # Loads all
# Use: pl.scan_csv("file.csv")  # Lazy evaluation

# 4. Free up system memory
# Close other applications
# Restart Docker Desktop
```

### Problem: Slow queries

**Symptoms:**
- Queries take very long
- Timeouts
- High CPU/memory usage

**Solutions:**

```python
# 1. Use predicate pushdown (filter early)
from scripts.utils.storage_utils import get_catalog
from config.iceberg_config import NAMESPACE, SILVER_BRANCH

catalog = get_catalog(branch=SILVER_BRANCH)
table = catalog.load_table(f"{NAMESPACE}.orders_silver")

# Filter before loading
scan = table.scan(row_filter="year = 2024 AND month = 1")
df = pl.from_arrow(scan.to_arrow())

# 2. Select only needed columns
scan = table.scan(selected_fields=("order_id", "total_amount", "status"))
df = pl.from_arrow(scan.to_arrow())

# 3. Use partitioning
# Ensure tables are partitioned by commonly filtered columns
# (year, month, etc.)

# 4. Increase batch size for large datasets
scan = table.scan()
df = pl.from_arrow(scan.to_arrow())  # Loads all
# Consider processing in batches for very large tables
```

### Problem: Data not appearing after ingestion

**Symptoms:**
- Scripts complete successfully
- But queries return no data
- Tables exist but are empty

**Solutions:**

```bash
# 1. Verify data was written
python scripts/utils/query_tables.py

# 2. Check MinIO for data files
# Access MinIO console: http://localhost:9001
# Navigate to: lakehouse → warehouse → ecommerce → orders_bronze

# 3. Verify branch is correct
curl http://localhost:19120/api/v2/trees
# Check you're querying the correct branch

# 4. Check for errors in ingestion logs
# Re-run ingestion with verbose output:
python scripts/bronze/ingest_orders.py

# 5. Verify schema matches data
python -c "
import polars as pl
df = pl.read_csv('data/raw/orders.csv')
print('CSV columns:', df.columns)
print('CSV types:', df.dtypes)
"
# Compare with schema in storage_utils.py
```

### Getting Help

If problems persist:

1. **Check logs**: `docker-compose logs` and script error messages
2. **Verify versions**: Ensure all package versions are compatible
3. **Reset environment**: `docker-compose down -v` and start fresh
4. **Check documentation**: 
   - Apache Iceberg: https://iceberg.apache.org/docs/
   - Project Nessie: https://projectnessie.org/docs/
   - Polars: https://pola-rs.github.io/polars/

---

## 💡 BEST PRACTICES {#bestpractices}

### Credential Management

1. **Never commit `.env` to version control**
   - Already in `.gitignore`
   - Use `.env.example` as template
   - Rotate credentials regularly in production

2. **Use different credentials for each environment**
   - Development: Simple passwords (as shown)
   - Staging: Medium complexity
   - Production: Strong, randomly generated passwords

3. **Store production credentials securely**
   - Use secret management services (AWS Secrets Manager, HashiCorp Vault)
   - Never hardcode in scripts
   - Use environment variables or secret injection

### Data Pipeline Practices

1. **Always validate data before ingestion**
   ```python
   # Run quality checks before writing
   from scripts.utils.quality_checks import DataQualityCheck
   qc = DataQualityCheck("orders_bronze")
   qc.check_row_count(df, min_rows=1)
   qc.check_no_nulls(df, ["order_id", "customer_id"])
   if not qc.print_report():
       raise ValueError("Data quality checks failed")
   ```

2. **Use Write-Audit-Publish pattern**
   - Write to staging table first
   - Run quality checks
   - Only publish to production if checks pass

3. **Handle errors gracefully**
   ```python
   try:
       # Your pipeline code
   except Exception as e:
       # Log error
       logger.error(f"Pipeline failed: {e}")
       # Send alert (email, Slack, etc.)
       # Exit with error code
       sys.exit(1)
   ```

4. **Version your schemas**
   - Document schema changes
   - Use schema evolution features of Iceberg
   - Test schema changes on dev branch first

### Branch Management

1. **Use branches for different environments**
   - `dev`: Development/testing
   - `staging`: Pre-production
   - `main`: Production
   - Feature branches for experiments

2. **Merge branches carefully**
   ```python
   # Example: Merge dev to main
   # Use Nessie API or UI to merge branches
   # Verify data quality after merge
   ```

3. **Tag important versions**
   - Tag releases
   - Tag before major changes
   - Enable time-travel queries

### Performance Optimization

1. **Partition tables appropriately**
   - Partition by date columns (year, month)
   - Partition by frequently filtered columns
   - Avoid over-partitioning (too many small files)

2. **Use predicate pushdown**
   ```python
   # Good: Filter early
scan = table.scan(row_filter="year = 2024")

   # Bad: Load all then filter
   df = pl.from_arrow(table.scan().to_arrow())
   df = df.filter(pl.col("year") == 2024)
   ```

3. **Select only needed columns**
   ```python
   # Good: Select specific columns
scan = table.scan(selected_fields=("order_id", "total_amount"))
   
   # Bad: Load all columns
   df = pl.from_arrow(table.scan().to_arrow())
   ```

4. **Process data in batches for large datasets**
   ```python
   chunk_size = 10000
   for i in range(0, total_rows, chunk_size):
       chunk = df.slice(i, chunk_size)
       # Process chunk
   ```

### Monitoring and Logging

1. **Log important events**
   ```python
   import logging
   logging.basicConfig(
       level=logging.INFO,
       format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
       handlers=[
           logging.FileHandler('logs/pipeline.log'),
           logging.StreamHandler()
       ]
   )
   logger = logging.getLogger(__name__)
   logger.info("Pipeline started")
   ```

2. **Monitor pipeline health**
   - Run `python scripts/utils/monitoring.py` regularly
   - Set up alerts for failures
   - Track pipeline execution times

3. **Track data quality metrics**
   - Record quality check results
   - Alert on quality degradation
   - Maintain quality dashboards

### Testing

1. **Write tests for each layer**
   - Unit tests for transformations
   - Integration tests for pipelines
   - End-to-end tests for full flow

2. **Test with sample data first**
   - Use small datasets for development
   - Validate logic before processing full dataset
   - Use realistic but manageable data volumes

3. **Test error handling**
   - Test with invalid data
   - Test with missing data
   - Test with schema mismatches

### Documentation

1. **Document your schemas**
   - Use comments in schema definitions
   - Maintain schema documentation
   - Document data lineage

2. **Document transformations**
   - Explain business logic
   - Document data quality rules
   - Note any assumptions

3. **Keep runbooks updated**
   - Document common operations
   - Document troubleshooting steps
   - Document recovery procedures

---

## 📊 PROJECT STRUCTURE

```
lakehouse-project/
├── config/
│   └── iceberg_config.py          # Configuration
├── data/
│   ├── raw/                       # Raw CSV files
│   ├── bronze/                    # (MinIO handles storage)
│   ├── silver/
│   └── gold/
├── scripts/
│   ├── bronze/
│   │   ├── ingest_orders.py
│   │   └── ingest_customers.py
│   ├── silver/
│   │   ├── transform_orders.py
│   │   └── transform_customers.py
│   ├── gold/
│   │   ├── create_order_analytics.py
│   │   └── create_customer_analytics.py
│   ├── utils/
│   │   ├── storage_utils.py
│   │   ├── quality_checks.py
│   │   ├── generate_sample_data.py
│   │   ├── setup_minio.py
│   │   ├── setup_nessie.py
│   │   ├── query_tables.py
│   │   └── monitoring.py
│   └── run_full_pipeline.py
├── tests/
│   └── test_pipeline.py
├── logs/
├── docker-compose.yml
└── requirements.txt
```

---

## 📝 EXECUTION CHECKLIST

- [ ] Docker Desktop installed and running
- [ ] Python 3.9+ installed
- [ ] Project directory created
- [ ] docker-compose.yml created
- [ ] Containers started (`docker-compose up -d`)
- [ ] MinIO accessible (http://localhost:9001)
- [ ] Nessie accessible (http://localhost:19120)
- [ ] Virtual environment created
- [ ] Requirements installed
- [ ] MinIO bucket created
- [ ] Nessie branches created
- [ ] Sample data generated
- [ ] Bronze ingestion tested
- [ ] Silver transformation tested
- [ ] Gold analytics tested
- [ ] Full pipeline runs successfully
- [ ] Tests pass
- [ ] Monitoring dashboard works

---

## 🏭 PRODUCTION CONSIDERATIONS {#production}

### Infrastructure Changes for Production

1. **Replace MinIO with Production S3**
   ```python
   # Update .env for production
   S3_ENDPOINT=https://s3.amazonaws.com  # AWS S3
   # OR
   S3_ENDPOINT=https://s3.us-east-1.amazonaws.com  # Regional endpoint
   S3_ACCESS_KEY=<your-aws-access-key>
   S3_SECRET_KEY=<your-aws-secret-key>
   S3_BUCKET=<your-production-bucket>
   ```

2. **Use Persistent Nessie Storage**
   ```yaml
   # docker-compose.yml - Update Nessie service
   nessie:
     environment:
       NESSIE_VERSION_STORE_TYPE: JDBC
       QUARKUS_DATASOURCE_JDBC_URL: jdbc:postgresql://postgres:5432/nessie
       # Add PostgreSQL service
   ```

3. **Add Monitoring and Alerting**
   - Set up Prometheus/Grafana for metrics
   - Configure alerts for pipeline failures
   - Monitor data quality metrics
   - Track storage costs

4. **Implement Backup Strategy**
   - Regular backups of Nessie metadata
   - S3 versioning for data files
   - Cross-region replication
   - Point-in-time recovery testing

5. **Security Hardening**
   - Use IAM roles instead of access keys
   - Enable encryption at rest
   - Enable encryption in transit (TLS)
   - Implement network isolation (VPC)
   - Use secret management services

### Orchestration Options

1. **Apache Airflow**
   ```python
   # orchestration/dags/lakehouse_dag.py
   from airflow import DAG
   from airflow.operators.bash import BashOperator
   
   dag = DAG('lakehouse_pipeline', schedule_interval='@daily')
   
   bronze_task = BashOperator(
       task_id='bronze_ingestion',
       bash_command='python scripts/bronze/ingest_orders.py',
       dag=dag
   )
   # Add more tasks...
   ```

2. **Prefect**
   ```python
   from prefect import flow, task
   
   @task
   def ingest_bronze():
       # Your ingestion code
       pass
   
   @flow
   def lakehouse_pipeline():
       ingest_bronze()
       # Add more steps
   ```

3. **Cron Jobs** (Simple option)
   ```bash
   # Add to crontab
   0 2 * * * cd /path/to/lakehouse && source venv/bin/activate && python scripts/run_full_pipeline.py
   ```

### Scaling Considerations

1. **Horizontal Scaling**
   - Use Spark for large-scale processing
   - Distribute workloads across workers
   - Use distributed query engines (Trino, Dremio)

2. **Optimization**
   - Implement data compaction
   - Use columnar formats (Parquet)
   - Implement caching strategies
   - Optimize partition strategies

3. **Cost Management**
   - Use S3 lifecycle policies
   - Archive old data to Glacier
   - Monitor and optimize storage usage
   - Use spot instances for batch processing

### Migration Checklist

Before moving to production:

- [ ] Replace MinIO with production S3
- [ ] Configure persistent Nessie storage
- [ ] Set up monitoring and alerting
- [ ] Implement backup strategy
- [ ] Security review and hardening
- [ ] Load testing with production-scale data
- [ ] Disaster recovery plan
- [ ] Documentation for operations team
- [ ] Runbook for common issues
- [ ] Performance benchmarking
- [ ] Cost estimation and optimization

---

## 🎉 SUCCESS!

You now have a complete Git-style versioned lakehouse with:

✅ **Medallion Architecture** (Bronze → Silver → Gold)
✅ **Version Control** for data (Nessie branches)
✅ **Quality Checks** (Write-Audit-Publish)
✅ **Production Ready** code structure
✅ **Complete Testing** suite
✅ **Monitoring** capabilities
✅ **Comprehensive Documentation**

### What You've Built:

1. **Data Ingestion Pipeline**: Automated ingestion from raw data to Bronze layer
2. **Transformation Pipeline**: Data cleaning and enrichment in Silver layer
3. **Analytics Pipeline**: Aggregated analytics in Gold layer
4. **Version Control**: Git-like branching for data with Nessie
5. **Quality Framework**: Data quality checks and validation
6. **Monitoring Tools**: Health checks and table statistics

### Next Steps:

1. **Customize for Your Data**
   - Replace sample data with your actual data sources
   - Adapt schemas to your domain
   - Customize transformations for your business logic

2. **Enhance the Pipeline**
   - Add more data sources
   - Implement additional transformations
   - Create more analytics tables

3. **Add Orchestration**
   - Set up Airflow/Prefect for scheduling
   - Implement error handling and retries
   - Add data quality alerts

4. **Scale for Production**
   - Move to production S3
   - Set up persistent Nessie storage
   - Implement monitoring and alerting
   - Add backup and disaster recovery

5. **Extend Functionality**
   - Add more data quality checks
   - Implement data lineage tracking
   - Add data catalog integration
   - Create BI dashboards

### Learning Resources:

- **Apache Iceberg**: 
  - Documentation: https://iceberg.apache.org/docs/
  - GitHub: https://github.com/apache/iceberg
  
- **Project Nessie**: 
  - Documentation: https://projectnessie.org/docs/
  - GitHub: https://github.com/projectnessie/nessie
  
- **Polars**: 
  - Documentation: https://pola-rs.github.io/polars/
  - User Guide: https://pola-rs.github.io/polars-book/
  
- **Data Lakehouse Patterns**:
  - Medallion Architecture: https://www.databricks.com/glossary/medallion-architecture
  - Delta Lake: https://delta.io/

### Community and Support:

- **Apache Iceberg Slack**: Join for community support
- **Project Nessie Discord**: Get help from the community
- **Stack Overflow**: Tag questions with `apache-iceberg`, `nessie`, `polars`

### Final Notes:

- **Keep Learning**: Data engineering is constantly evolving
- **Iterate**: Start simple, add complexity as needed
- **Monitor**: Always monitor your pipelines in production
- **Document**: Keep your documentation up to date
- **Test**: Test changes thoroughly before deploying

**Happy Data Engineering!** 🚀

---

## 📞 SUPPORT

If you encounter issues:

1. Check the [Troubleshooting](#troubleshooting) section
2. Review logs: `docker-compose logs` and script outputs
3. Verify all prerequisites are met
4. Check service health: `python scripts/utils/monitoring.py`
5. Consult official documentation (links above)

**Remember**: This is a learning project. Adapt it to your needs and scale gradually!
