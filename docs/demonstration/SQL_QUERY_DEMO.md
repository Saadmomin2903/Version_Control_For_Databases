# 📊 SQL Query Engine Demo

## What This Shows

This demonstration shows how to connect to the **Consumption Layer** (Spark Thrift Server) on VM3 to run standard SQL queries against the Data Lakehouse. This simulates how Business Intelligence (BI) tools (like Tableau, PowerBI) or Analysts (using DBeaver) would access the data.

---

## 🎯 Demo Steps

### 1. Connect to the SQL Engine (VM3)

Launch the Beeline CLI (a standard JDBC client) directly inside the container to demonstrate connectivity.

**Command:**
```bash
ssh -i key3/oracle-vm3.key ubuntu@161.118.185.218 \
  "docker exec -it lakehouse-thrift /opt/spark/bin/beeline -u jdbc:hive2://localhost:10000 -n admin -p admin"
```

**What to explain:**
> "I am now connecting to the SQL Query Engine running on VM3. This is a dedicated server that allows external tools to query our Iceberg tables using standard SQL, just like a traditional data warehouse."

---

### 2. Explore Database Objects

Once inside the `jdbc:hive2://localhost:10000> ` prompt, run:

**Command:**
```sql
SHOW SCHEMAS IN nessie;
```

**Expected Output:**
```
+------------+
| namespace  |
+------------+
| ecommerce  |
| demo       |
+------------+
```

**Command:**
```sql
USE nessie.ecommerce;
SHOW TABLES;
```

**Expected Output:**
```
+----------------+
|   tableName    |
+----------------+
| orders_bronze  |
| orders_silver  |
| daily_sales_gold |
...
+----------------+
```

---

### 3. Run Analytical Queries

Demonstrate that you can run standard aggregations on the data.

**Command (Count Total Records):**
```sql
SELECT count(*) FROM orders_silver;
```
*(Should return ~3.1 million rows)*

**Command (Business Analytics - Gold Layer):**
```sql
SELECT * FROM daily_sales_gold ORDER BY order_date DESC LIMIT 5;
```

**What to explain:**
> "We are running ANSI SQL queries directly against the files in Object Storage. The query engine handles the compute, while Nessie ensures we are reading the consistent version of the data."

---

### 4. Exit

**Command:**
```sql
!quit
```

---

## 🔌 Connecting DBeaver (Optional Visual Demo)

If you have DBeaver installed on your laptop, you can show a visual connection:

1. **New Connection** -> **Apache Hive** or **Spark SQL**
2. **Host:** `161.118.185.218`
3. **Port:** `10000`
4. **Database:** `default` (or `nessie`)
5. **No Authentication** (or user/pass: admin/admin)
6. **Test Connection**

> "This confirms that our Data Lakehouse is open for business and compatible with standard industry tools."
