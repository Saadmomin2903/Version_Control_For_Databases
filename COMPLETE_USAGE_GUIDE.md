# Complete Usage Guide - Version Control for Databases

**Last Updated**: 2026-01-23

This guide contains everything you need to operate your data lakehouse with Git-like version control.

---

## Quick Reference

### Access Points

| Service | URL | Notes |
|---------|-----|-------|
| **Nessie API** | http://140.238.224.207:19120/api/v2/config | Catalog API |
| **Jupyter Notebook** | http://140.238.224.207:8888 | Get token first |
| **VM1 SSH** | `ssh -i ~/.ssh/oracle-vm1.key ubuntu@140.238.224.207` | Main server |
| **VM2 SSH** | `ssh -i ~/.ssh/oracle-vm2.key ubuntu@140.245.16.49` | Worker |

### Get Jupyter Token
```bash
# On VM1
docker logs lakehouse-spark 2>&1 | grep token
```

---

## Part 1: Starting the Infrastructure

### If VM Was Rebooted (Containers Not Running)

SSH to VM1 and restart everything:

```bash
ssh -i ~/.ssh/oracle-vm1.key ubuntu@140.238.224.207

# Re-add firewall rule (lost after reboot)
sudo iptables -I INPUT -p tcp --dport 5432 -j ACCEPT

# Restart containers
cd ~/Version_Control_For_Databases
docker-compose -f docker-compose-production.yml down
docker-compose -f docker-compose-production.yml up -d

# Wait and verify
sleep 20
docker ps
curl http://localhost:19120/api/v2/config
```

**Expected output**: Both containers running, Nessie API responding.

---

## Part 2: Using Spark with Nessie + Iceberg

### Step 1: Open Jupyter Notebook

1. Get token on VM1:
   ```bash
   docker logs lakehouse-spark 2>&1 | grep token
   ```

2. Open in browser:
   ```
   http://140.238.224.207:8888/?token=YOUR_TOKEN_HERE
   ```

3. Create a new Python 3 notebook

### Step 2: Configure Spark Session

**Run this in the first cell** (required every time you restart the kernel):

```python
from pyspark.sql import SparkSession

spark = SparkSession.builder \
    .appName("NessieIceberg") \
    .config("spark.jars", "/opt/spark/jars/iceberg-spark-runtime-3.3_2.12-1.3.0.jar") \
    .config("spark.sql.extensions", "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions") \
    .config("spark.sql.catalog.nessie", "org.apache.iceberg.spark.SparkCatalog") \
    .config("spark.sql.catalog.nessie.catalog-impl", "org.apache.iceberg.nessie.NessieCatalog") \
    .config("spark.sql.catalog.nessie.uri", "http://nessie:19120/api/v1") \
    .config("spark.sql.catalog.nessie.ref", "main") \
    .config("spark.sql.catalog.nessie.warehouse", "/tmp/warehouse") \
    .getOrCreate()

print("Spark version:", spark.version)
```

### Step 3: Basic Operations

**List namespaces**:
```python
spark.sql("USE nessie")
spark.sql("SHOW NAMESPACES").show()
```

**Create namespace**:
```python
spark.sql("CREATE NAMESPACE IF NOT EXISTS nessie.demo")
```

**Create table**:
```python
spark.sql("""
    CREATE TABLE IF NOT EXISTS nessie.demo.my_table (
        id INT,
        name STRING,
        created_at TIMESTAMP
    ) USING iceberg
""")
```

**Insert data**:
```python
spark.sql("""
    INSERT INTO nessie.demo.my_table VALUES 
    (1, 'Alice', current_timestamp()),
    (2, 'Bob', current_timestamp())
""")
```

**Query data**:
```python
spark.sql("SELECT * FROM nessie.demo.my_table").show()
```

---

## Part 3: Version Control with Nessie

### List All Branches

```python
import requests

branches = requests.get("http://nessie:19120/api/v1/trees").json()
print("Branches:")
for ref in branches.get('references', []):
    print(f"  - {ref['name']}: {ref['hash'][:8]}...")
```

### Create a New Branch

```python
import requests

# First, get current main hash
branches = requests.get("http://nessie:19120/api/v1/trees").json()
main_ref = next(r for r in branches['references'] if r['name'] == 'main')
main_hash = main_ref['hash']

# Create new branch
response = requests.post(
    "http://nessie:19120/api/v1/trees/tree",
    headers={"Content-Type": "application/json"},
    json={
        "name": "feature-branch",
        "type": "BRANCH",
        "hash": main_hash
    }
)
print("Created branch:", response.status_code)
```

### View Commit History

```python
import requests

logs = requests.get("http://nessie:19120/api/v1/trees/tree/main/log").json()
print(f"Commits on main: {len(logs.get('logEntries', []))}")
for entry in logs.get('logEntries', []):
    print(f"  - {entry.get('commitMeta', {}).get('message', 'No message')}")
```

### Switch Branch in Spark

To query data from a different branch, create a new Spark session with that ref:

```python
spark.stop()

spark = SparkSession.builder \
    .appName("NessieIceberg") \
    .config("spark.jars", "/opt/spark/jars/iceberg-spark-runtime-3.3_2.12-1.3.0.jar") \
    .config("spark.sql.extensions", "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions") \
    .config("spark.sql.catalog.nessie", "org.apache.iceberg.spark.SparkCatalog") \
    .config("spark.sql.catalog.nessie.catalog-impl", "org.apache.iceberg.nessie.NessieCatalog") \
    .config("spark.sql.catalog.nessie.uri", "http://nessie:19120/api/v1") \
    .config("spark.sql.catalog.nessie.ref", "dev") \  # <-- Different branch
    .config("spark.sql.catalog.nessie.warehouse", "/tmp/warehouse") \
    .getOrCreate()
```

---

## Part 4: Troubleshooting

### Problem: Nessie Container Keeps Restarting

**Cause**: PostgreSQL connection issue (iptables rule lost after reboot)

**Solution**:
```bash
# On VM1
sudo iptables -I INPUT -p tcp --dport 5432 -j ACCEPT
docker-compose -f docker-compose-production.yml down
docker-compose -f docker-compose-production.yml up -d
```

### Problem: Cannot Connect to Nessie from Outside

**Cause**: Oracle Security List doesn't have ingress rule for port 19120

**Solution**: Add ingress rule in Oracle Console:
1. Networking → Virtual Cloud Networks → Your VCN
2. Security Lists → Default Security List
3. Add Ingress Rule: Source 0.0.0.0/0, TCP, Port 19120

### Problem: ClassNotFoundException for Iceberg

**Cause**: Iceberg JAR not loaded

**Solution**: Make sure this is in your Spark config:
```python
.config("spark.jars", "/opt/spark/jars/iceberg-spark-runtime-3.3_2.12-1.3.0.jar")
```

If JAR doesn't exist, download it:
```python
!wget -q -P /opt/spark/jars/ https://repo1.maven.org/maven2/org/apache/iceberg/iceberg-spark-runtime-3.3_2.12/1.3.0/iceberg-spark-runtime-3.3_2.12-1.3.0.jar
```

### Problem: "Network is unreachable" for Supabase

**Cause**: Oracle VMs don't support IPv6, and Supabase only provides IPv6 addresses

**Solution**: Use local PostgreSQL instead of Supabase (already configured)

---

## Part 5: Architecture Reference

```
┌─────────────────────────────────────────────────────────────┐
│                         YOUR MAC                            │
│  ┌─────────────────┐                                        │
│  │  Browser        │  Access Jupyter, Nessie API           │
│  └────────┬────────┘                                        │
│           │                                                  │
└───────────┼──────────────────────────────────────────────────┘
            │ HTTP (ports 8888, 19120)
            ▼
┌─────────────────────────────────────────────────────────────┐
│              VM1: 140.238.224.207                           │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Docker Containers                                   │   │
│  │  ┌──────────────┐  ┌───────────────────────────┐    │   │
│  │  │   Nessie     │  │   Spark + Jupyter         │    │   │
│  │  │  :19120      │◄─┤   :8888, :7077, :8081     │    │   │
│  │  └──────────────┘  └───────────────────────────┘    │   │
│  └─────────────────────────────────────────────────────┘   │
│                           │                                  │
│                           ▼                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  PostgreSQL (local)                                  │   │
│  │  :5432 - Stores Nessie catalog metadata              │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│              VM2: 140.245.16.49                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Docker (Spark Worker - Optional)                    │   │
│  │  Connects to VM1's Nessie                            │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│              Oracle Object Storage                          │
│  Bucket: lakehouse-prod                                     │
│  Region: ap-mumbai-1                                        │
│  Namespace: bmcfe6z38foz                                    │
│  (For production data - not currently used in local tests)  │
└─────────────────────────────────────────────────────────────┘
```

---

## Part 6: Common Commands Cheatsheet

### VM Access
```bash
# SSH to VM1
ssh -i ~/.ssh/oracle-vm1.key ubuntu@140.238.224.207

# SSH to VM2
ssh -i ~/.ssh/oracle-vm2.key ubuntu@140.245.16.49
```

### Docker Commands (on VM1)
```bash
# Check containers
docker ps

# View Nessie logs
docker logs lakehouse-nessie --tail 50

# View Spark logs
docker logs lakehouse-spark --tail 50

# Restart containers
docker-compose -f docker-compose-production.yml down
docker-compose -f docker-compose-production.yml up -d
```

### API Checks
```bash
# Check Nessie is running
curl http://localhost:19120/api/v2/config

# Check from outside (your Mac)
curl http://140.238.224.207:19120/api/v2/config
```

### Get Jupyter Token
```bash
docker logs lakehouse-spark 2>&1 | grep token
```

---

## Part 7: What's Working

| Component | Status | Details |
|-----------|--------|---------|
| VM1 Docker | ✅ | docker.io + docker-compose |
| VM2 Docker | ✅ | docker.io + docker-compose |
| PostgreSQL | ✅ | Local on VM1, port 5432 |
| Nessie | ✅ | Port 19120, JDBC backend |
| Spark 3.3.1 | ✅ | With Iceberg runtime |
| Jupyter | ✅ | Port 8888 |
| Iceberg Tables | ✅ | Working with Nessie catalog |
| Nessie Branches | ✅ | main, dev created |
| Oracle Storage | ✅ | Configured, ready for production data |

---

## Cost Summary

| Resource | Cost |
|----------|------|
| Oracle Cloud VMs (Always Free) | $0.00 |
| Oracle Object Storage (10GB free) | $0.00 |
| Supabase (not used - IPv6 issue) | $0.00 |
| **Total Monthly** | **$0.00** |
