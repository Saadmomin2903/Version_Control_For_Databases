# Bronze Layer: Ingestion & Raw Data

> **Status**: Operational  
> **Focus**: Data Ingestion, History Preservation, Speed  
> **Key Pattern**: Raw Data Landing (EL - Extract, Load)

---

## 👶 ELI5: The "Magic" Behind the Scenes

You asked to explain this like you're 5 years old. Let's send it back to the **Big Library**.

### 1. The Delivery Truck (CSV Files) 🚚
- Imagine a big delivery truck backing up to the library.
- It dumps a pile of boxes (Customer and Order records) on the floor.
- The driver doesn't care if the boxes are upside down, labeled wrong, or if there are two identical boxes. They just want to empty the truck and leave.
- This is our **Raw Data** (CSVs).

### 2. The Landing Zone (Bronze Layer) 📦
- We don't put these boxes on the nice shelves yet. That would make a mess!
- Instead, we have a special room called the **Bronze Room**.
- We simply move the boxes from the floor into this room exactly as they are.
- **Rule #1**: Do not open the boxes.
- **Rule #2**: Do not fix typos.
- **Rule #3**: Just keep them safe so we can look at them later if we made a mistake sorting.

### 3. Nessie (The Branch Manager) 🌿
- Nessie opens a special notebook page called `"bronze"`.
- She writes down: "Truck arrived at 9:00 AM. We put 1,000 boxes in the Bronze Room."
- This is distinct from the main library. Visitors (Analysts) don't see this room. It's only for the librarians (Data Engineers).

---

## 🛠️ Deep Dive: What Actually Happens in the Bronze Layer?

The Bronze Layer is the entry point of our "Lakehouse". Its job is to ingest data from external sources with **Zero Transformation**.

### **Workflow 1: Customers Ingestion (`ingest_customers_spark.py`)**

1.  **Setup Spark & Nessie**:
    - The script configures Spark to talk to **Nessie** and **MinIO**.
    - **Crucial Setting**: `.set('spark.sql.catalog.nessie.ref', 'bronze')`
    - This tells Spark: *"Whatever you do, do it on the `bronze` branch. Do not touch `main`."*

2.  **Read Raw Data**:
    - `spark.read.csv("/home/jovyan/data/raw/customers.csv")`
    - It reads the messy text file.
    - `inferSchema=True`: It guesses that "123" is a number and "Bob" is text.

3.  **Write to Bronze**:
    - `df.writeTo("nessie.ecommerce.customers_bronze").createOrReplace()`
    - It takes the data from RAM and saves it as **Iceberg Tables** in MinIO.
    - **Why Iceberg?** Because CSVs are slow to read. Iceberg is fast and lets us travel back in time.

### **Workflow 2: Orders Ingestion (`ingest_orders_spark.py`)**

This follows the exact same pattern as Customers.

1.  **Read**: Load `orders.csv`.
2.  **Structure**: It creates a table `nessie.ecommerce.orders_bronze`.
3.  **Persist**: Saves the data to `s3a://lakehouse/warehouse/ecommerce/orders_bronze`.

---

## ❓ Q&A: Addressing Common Questions

### **1. Why don't we clean the data here?**
*   **The "Safety Net" Principle**: If we made a mistake in our cleaning code (e.g., accidentally deleted all customers named "Null"), we need a way to get the original data back.
*   The Bronze layer is that backup. It is an exact copy of the source. If the Silver layer breaks, we just re-run it from Bronze.

### **2. Why `createOrReplace` instead of Append?**
*   **For this Demo**: We are simulating a "Snapshot" ingestion. Every time we run the script, we treat the CSV as the current full state of the world.
*   **In Production**: usually, we would use `.append()` to add only today's new orders.

### **3. Where is the table physically?**
*   **MinIO Path**: `s3a://lakehouse/warehouse/ecommerce/customers_bronze/data/`
*   **Branch**: It exists on the `bronze` branch in Nessie. If you look at the `main` branch, this table might be empty or different!

### **4. How is this different from the CSV file?**
*   **Format**: The CSV is a text file. The Bronze table is **Parquet** (compressed binary).
*   **Metadata**: Iceberg tracks the files. We can query it with SQL (`SELECT * FROM customers_bronze`). You can't easily run SQL on a raw CSV file without defining it first.

### **5. Can I query the Bronze layer?**
*   **Yes**, but be careful!
*   It contains duplicates, bad data, and messy formats.
*   Query example:
    ```python
    spark.sql("SELECT * FROM nessie.ecommerce.`customers_bronze@bronze`").show()
    ```
    *(Note the `@bronze` syntax to tell Nessie which branch to look at)*

### **6. What happens if the CSV is missing columns?**
*   Since we use `inferSchema=True`, Spark will try to adapt.
*   However, if a required column is missing, the script might fail or create a table with a different schema than expected. This is why Silver validates the schema!

### **7. Why do we need Nessie here?**
*   Nessie versions the **ingestion itself**.
*   If we load a bad batch of data (e.g., a corrupted CSV), we can simply "undo" the commit in Nessie, and the Bronze reference reverts to the previous good state. No need to manually delete files in S3.
