# 🎯 Complete Project Demonstration Guide

## Project Title: **Data Lakehouse with Git-Like Version Control**

**Duration:** 10-12 minutes  
**Tech Stack:** Apache Iceberg, Nessie, Spark, Airflow, Oracle Cloud  
**Data Scale:** 3.1M e-commerce transactions

---

## 🎬 Presentation Flow

### **[0-1 min] Introduction & Problem Statement**

> "Today I'm presenting a production-grade Data Lakehouse that brings **Git-like version control** to data engineering. Traditional data warehouses lack the ability to branch, rollback, or time-travel through data changes. We've solved this using **Apache Nessie** as a catalog."

**Key Stats to Mention:**
- 3.1M+ records processed
- 3-layer Medallion architecture (Bronze → Silver → Gold)
- 3 VMs orchestrating 2-node Spark cluster
- ML-powered customer segmentation (9,786 customers, 4 segments)

---

### **[1-3 min] Architecture Overview**

**Show:** `ARCHITECTURE_EXPLAINED.md` diagram

```
VM1 (Master)          VM2 (Worker)         VM3 (SQL Engine)
────────────          ────────────         ────────────────
• Nessie Catalog      • Spark Worker       • Spark Thrift Server
• Airflow             • Task Execution     • JDBC Interface (Port 10000)
• Spark Master                             • BI Tool Access
```

**Talking Points:**
- "VM1 runs the control plane: Nessie catalog, Airflow orchestration, Spark master"
- "VM2 provides distributed compute for large-scale transformations"
- "VM3 exposes data via standard SQL for Tableau, PowerBI, analysts"
- "All data stored in Oracle Object Storage (S3-compatible)"

---

### **[3-5 min] DEMO 1: Version Control in Action**

**Show:** `NESSIE_BRANCHES_DEMO.md`

**Command:**
```bash
ssh -i ~/.ssh/oracle-vm1.key ubuntu@140.238.224.207 \
  "docker exec lakehouse-spark python3 -c '
from pyspark.sql import SparkSession
spark = SparkSession.builder.getOrCreate()
spark.sql(\"LIST REFERENCES IN nessie\").show()
'"
```

**Expected Output:**
```
+--------+--------------------+
|   name |               hash |
+--------+--------------------+
|   main | a1b2c3d4e5f6...   |
| bronze | b2c3d4e5f6g7...   |
| silver | c3d4e5f6g7h8...   |
|   gold | d4e5f6g7h8i9...   |
+--------+--------------------+
```

**Explain:**
> "Just like Git has branches, our data has branches. Each layer (Bronze, Silver, Gold) develops independently. Teams can experiment without breaking production."

---

### **[5-7 min] DEMO 2: Automated Pipeline with Airflow**

**Show:** `AIRFLOW_DAG_DEMO.md`

**Option A: Browser (Recommended)**
1. Open http://140.238.224.207:8080
2. Login: `admin` / `admin`
3. Show `medallion_architecture_pipeline` DAG
4. Click "Trigger DAG" ▶️

**Option B: CLI**
```bash
ssh -i ~/.ssh/oracle-vm1.key ubuntu@140.238.224.207 \
  "docker exec lakehouse-airflow airflow dags trigger medallion_architecture_pipeline"
```

**Talking Points:**
- "This DAG orchestrates the entire pipeline: Bronze → Silver → Gold"
- "It runs nightly at midnight, fully automated"
- "Each task has retry logic and monitoring built-in"

---

### **[7-9 min] DEMO 3: ML Customer Segmentation**

**Show:** `ML_DEMO.md` + `customer_segmentation_analysis.png`

**Command:**
```bash
ssh -i ~/.ssh/oracle-vm1.key ubuntu@140.238.224.207 \
  "docker exec lakehouse-spark python3 /home/jovyan/scripts/gold/customer_segmentation_simple.py"
```

**Key Results to Highlight:**
```
🏆 Best K: 4 (Silhouette Score: 0.63)

📊 Segment Profiles:
              Lifetime Value  Customers  % of Base
VIP           $13,799         38         0.4%
High Value    $2,489          1,302      13.3%
Medium Value  $2,267          618        6.3%
Low Value     $499            7,828      80%
```

**Show the visualization:** `customer_segmentation_analysis.png`

**Explain:**
> "Our ML model identified 38 VIP customers worth $13K each. This enables targeted marketing. The model uses K-Means clustering with a Silhouette Score of 0.63, indicating strong segment separation."

---

### **[9-10 min] DEMO 4: Business Intelligence Access**

**Show:** `SQL_QUERY_DEMO.md`

**Command:**
```bash
ssh -i key3/oracle-vm3.key ubuntu@161.118.185.218 \
  "docker exec lakehouse-thrift /opt/spark/bin/beeline -u jdbc:hive2://localhost:10000 -n admin -p admin -e \"
SELECT segment_name, 
       COUNT(*) as customer_count,
       AVG(monetary) as avg_lifetime_value
FROM nessie.ecommerce.customer_segments
GROUP BY segment_name
ORDER BY avg_lifetime_value DESC
\""
```

**Talking Points:**
- "Data analysts and BI tools connect via standard JDBC on port 10000"
- "No Spark knowledge required - it's just SQL"
- "Tableau, PowerBI, DBeaver all work out of the box"

---

### **[10-11 min] DEMO 5: Time Travel**

**Show:** `TIME_TRAVEL_DEMO.md`

**Command:**
```bash
ssh -i ~/.ssh/oracle-vm1.key ubuntu@140.238.224.207 \
  "docker exec lakehouse-spark python3 -c '
from pyspark.sql import SparkSession
spark = SparkSession.builder.getOrCreate()
spark.sql(\"SELECT * FROM nessie.ecommerce.orders_silver.history\").show()
'"
```

**Explain:**
> "Every change is tracked. We can query data as it existed yesterday, last week, or at any commit. This is crucial for auditing and debugging bad data releases."

---

### **[11-12 min] Business Value & Closing**

**Key Achievements:**
1. ✅ **Version Control for Data** - Branch, merge, rollback like code
2. ✅ **Production ML** - 4-segment customer model (0.63 quality score)
3. ✅ **Scalable Architecture** - 2-node Spark cluster, 3.1M records
4. ✅ **Enterprise Integration** - Standard SQL interface for BI tools
5. ✅ **Automation** - Airflow orchestration with monitoring

**Business Impact:**
- **$13K per VIP customer** - Enables targeted retention campaigns
- **Rollback capability** - Prevents bad data from reaching production
- **Parallel development** - Multiple teams work without conflicts
- **Audit trail** - Every data change is tracked and reversible

**Tech Highlight:**
> "This stack (Iceberg + Nessie + Spark) is the same used by Netflix, Apple, and LinkedIn for petabyte-scale data lakes."

---

## 🎤 Q&A Preparation

### Common Questions & Answers

**Q: Why not just use Git for data?**  
A: Git is designed for text files. Data lakes need specialized formats like Iceberg that handle:
   - Partitioned datasets (millions of files)
   - Schema evolution
   - Concurrent writes
   - Time-travel queries

**Q: How does this compare to Databricks/Snowflake?**  
A: Similar capabilities but:
   - Open-source (no vendor lock-in)
   - Self-hosted (full control)
   - S3-compatible (works with any object storage)

**Q: What happens if two branches modify the same data?**  
A: Nessie handles merge conflicts just like Git. You resolve them manually before merging to main.

**Q: Can you query across branches?**  
A: Yes! Use `@branch` notation:
   ```sql
   SELECT * FROM nessie.ecommerce.orders_silver@gold
   ```

**Q: Cost of running this?**  
A: Oracle Cloud Free Tier covers 3 VMs. Storage cost: ~$0.10/month for 10GB.

---

## 📋 Pre-Demo Checklist

- [ ] All VMs running (`docker ps` on each)
- [ ] Nessie accessible: http://140.238.224.207:19120
- [ ] Airflow accessible: http://140.238.224.207:8080
- [ ] Have SSH keys ready (`~/.ssh/oracle-vm1.key`, etc.)
- [ ] Customer segmentation chart downloaded locally
- [ ] Browser tabs pre-opened (Airflow, Nessie)
- [ ] Terminal windows positioned for screen share

---

## 🚀 Backup Commands (If Live Demo Fails)

### Quick Verification Script
```bash
# Show all services running
ssh -i ~/.ssh/oracle-vm1.key ubuntu@140.238.224.207 "docker ps --format 'table {{.Names}}\t{{.Status}}'"

# Show record counts
ssh -i ~/.ssh/oracle-vm1.key ubuntu@140.238.224.207 \
  "docker exec lakehouse-spark python3 -c '
from pyspark.sql import SparkSession
spark = SparkSession.builder.getOrCreate()
print(\"Silver:\", spark.sql(\"SELECT count(*) FROM nessie.ecommerce.orders_silver@main\").collect()[0][0])
print(\"Segments:\", spark.sql(\"SELECT count(*) FROM nessie.ecommerce.customer_segments@gold\").collect()[0][0])
'"
```

---

## 📁 Supporting Documents

For deeper dives, refer to:
- **Architecture**: `ARCHITECTURE_EXPLAINED.md`
- **Pipeline Details**: `PIPELINE_DEMO.md`
- **ML Deep Dive**: `ML_DEMO.md`
- **Time Travel**: `TIME_TRAVEL_DEMO.md`
- **SQL Access**: `SQL_QUERY_DEMO.md`

---

**Good luck with your presentation! 🎓🚀**
