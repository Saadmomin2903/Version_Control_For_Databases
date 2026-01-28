# Silver Layer: Extreme Detail Plan & Documentation

> **Status**: Verified & Optimized  
> **Focus**: Data Cleaning, Deduplication, and Validation  
> **Key Pattern**: Write-Audit-Publish (WAP)  

---

## 👶 ELI5: The "Magic" Behind the Scenes

You asked to explain this like you're 5 years old. Let's imagine a **Big Library**.

### 1. Nessie (The Magic Librarian) 🧙‍♂️
Imagine a librarian who has a magic notebook.
- **Normal Librarians** just put books on shelves. If they make a mistake, the book is messy forever.
- **Nessie** allows you to take a photo of the *entire library* before you change anything.
- If you scribble in a book and ruin it, Nessie snaps her fingers, and the library goes back to exactly how it was before you started.
- **Branches**: Nessie lets you have a "Ghost Library" (the `silver` branch) where you can work messily. Only when you are perfect does she copy your work to the "Real Library" (`main` branch).

### 2. Iceberg (The Magic Table of Contents) 📖
- Imagine a book where you can't erase ink (S3/MinIO files can't be changed, only rewritten).
- **Iceberg** is a super-smart Table of Contents at the front of the book.
- When you "change" a page, you actually just write a *new* page and put it in the back.
- Then, Iceberg updates the Table of Contents to say: *"Skip page 5, go to page 102 instead."*
- This means you never accidentally lose the old words—they are still there if you need to look back!

### 3. MinIO (The Bookshelf) 📚
- This is just the wooden shelf where the pages (files) sit.
- It doesn't know what's written on them. It just holds them.
- In our project, this is the **Storage Layer** (Port 9000).

### 4. Spark (The Super-Fast Reader/Writer) ⚡
- This is you! The person doing the work.
- You read the messy notes (Bronze), fix the spelling (Silver), and write a clean copy.
- You are very fast, but you need a desk (Memory/RAM). If the book is too big for your desk, you crash (Out of Memory).

---

## 🛠️ Deep Dive: What Actually Happens in the Silver Layer?

The Silver Layer is where we take "Raw" data and make it "Trusted".

### **Workflow 1: Customers Transformation (`transform_customers_silver.py`)**

This script uses the **Write-Audit-Publish** pattern.

1.  **Read Bronze**:
    - Spark asks Nessie: *"Give me the `customers_bronze` table from the `bronze` branch."*
    - Nessie points to the latest files in MinIO.
    - Spark loads them into memory.

2.  **Transformation (The Cleaning)**:
    - **Deduplication**: `dropDuplicates(["customer_id"])` - If two people have ID #101, keep one, throw away the other.
    - **Standardization**: `lower(email)` - Changes "BOB@GMAIL.COM" to "bob@gmail.com".
    - **Validation**: Creates a flag `email_valid` = True if the email has an "@" symbol.
    - **Scoring**: Calculates a 0-100 `data_quality_score`.
        - 100 points: Name, Email + "@", ID all present.
        - 75 points: Missing name but has email.
        - 50 points: Missing email or ID.

3.  **The "Safety Check" (Quality Gate)**:
    - Before saving, the script pauses.
    - **Check**: *"Are 95% of emails valid?"*
    - **Pass**: Continue.
    - **Fail**: Stop everything! do not write data. (This prevents bad data from ever entering Silver).

4.  **Write to Silver Branch**:
    - Spark writes the new clean data to MinIO (as Parquet files).
    - It tells Nessie: *"Update the `customers_silver` table on the `silver` branch."*

---

### **Workflow 2: Orders Transformation (`transform_orders_silver.py`)**
*Optimized for Performance*

This script is different. It uses **Batch Processing** because there are too many orders to fit on the desk at once.

1.  **The Hard Reset**:
    - `spark.sql("DROP TABLE ... orders_silver")`
    - We completely wipe the old Silver table to start fresh (Full Refresh strategy).

2.  **Smart Partitioning**:
    - We tell Iceberg: *"Organize these files by Day."*
    - This makes future lookups fast (e.g., "Show me orders from Jan 1st").

3.  **The Loop (Batch Processing)**:
    - Instead of reading 300 Million rows at once...
    - **Loop 1**: Read only **December 2019**. Clean it. Write it.
    - **Loop 2**: Read only **January 2020**. Clean it. Append it to the table.
    - **Loop 3**: Read only **February 2020**...
    - This is how we prevent **Out of Memory (OOM)** errors. We only put one month on the "desk" at a time.

---

## ❓ Q&A: Addressing Your Specific Questions

### **1. Where are the errors shown?**
*   **Console Output**: The primary errors appear in the terminal where you run the command (or the Airflow logs).
*   **Quality Report**: The script `audit_silver_quality.py` prints a report showing "Dropped Rows" and "Failed Checks".
*   **Great Expectations**: If you enabled the strict mode in `silver_expectations.py`, it would generate a nice HTML report, but currently, it prints ``⚠️ Validation FAILED!`` to the console logs.

### **2. What are the types of errors?**
*   **Data Quality Errors**:
    *   **Null IDs**: An order without an Order ID.
    *   **Invalid Email**: "bob#gmail.com" (missing @).
    *   **Negative Price**: An order with price `-50.00`.
    *   **Duplicates**: The same order appearing twice.
*   **System Errors**:
    *   **OOM (Java Heap Space)**: Tried to process too much data at once.
    *   **Nessie Conflict**: Two people tried to update the branch at the exact same time.

### **3. What exactly is happening in `audit.py`?**
*It’s a detective.* 🕵️‍♀️
1.  **Counts Bronze**: "We started with 1,000 orders."
2.  **Counts Silver**: "We ended with 980 orders."
3.  **Calculates Drop**: "We lost 20 orders (2%)."
4.  **Deep Checks**:
    - It scans the *Silver* table specifically looking for mistakes that might have slipped through.
    - checks: `filter("price < 0")` -> Should be 0.
    - checks: `filter("customer_id IS NULL")` -> Should be 0.
5.  If it finds issues, it screams (prints) **FAILED**.

### **4. What are the challenges you faced in this layer?**
*   **Memory Limits**: Spark runs inside a container with limited RAM (4GB). Loading all valid emails to check for duplicates crashed the worker.
    *   *Solution*: Switch to Monthly Batches for Orders.
*   **Deduplication**: Removing duplicates is "expensive" (computationaly) because you have to compare every row with every other row.
    *   *Solution*: We rely on Iceberg's `dropDuplicates` which is optimized, but it still triggers a "Shuffle" (moving data between workers).
*   **Small Files**: Writing many small batches creates thousands of tiny files, which slows down reading later.
    *   *Solution*: Iceberg has a "Compaction" procedure (maintenance) to glue small files together later.

### **5. Where can I see what data is populated into the table?**
*   **Jupyter Notebook**: Open `notebooks/SILVER_LAYER.ipynb` and run:
    ```python
    spark.sql("SELECT * FROM nessie.ecommerce.`orders_silver@silver` LIMIT 10").show()
    ```
*   **Trino**:
    ```sql
    SELECT * FROM silver.ecommerce.orders_silver LIMIT 10;
    ```
*   **Superset**: Go to the "SQL Lab" and query the table.

### **6. Where can I see the audit files?**
Currently, the audit **results** are printed to the logs (Console/Airflow). They are not saved as a separate file in this version.
*   *Improvement*: We could save the bad rows to a `quarters_silver_rejects` table to inspect them later.

### **7. What is the Trino here?**
*   **The Speedster**.
*   Spark is like a heavy truck. It's great for moving the whole library (ETL).
*   **Trino** is like a sports car. It's great for just *looking* at the library.
*   When you open Superset (Dashboards), it uses Trino to query the Iceberg tables because Trino answers in milliseconds, whereas Spark might take seconds or minutes to start up.

### **8. Where is the populated data getting stored?**
*   **Physically**: In **MinIO** (or Oracle Object Storage in Prod).
*   **Path**: `s3a://lakehouse/warehouse/ecommerce/orders_silver/data/`
*   **Format**: `.parquet` files (binary, compressed files). You can't read them with Notepad; you need Spark or Trino.

### **9. How do you do Silver optimization?**
1.  **Partitioning**: We chop the data by `Day`. When you query "Jan 1st", we only read that day's filse.
2.  **Bucketing**: We bucket by `customer_id`. This groups specific customers into specific files, making joins faster later.
3.  **Batching**: Processing data in chunks (Months) to save RAM.
4.  **Predicate Pushdown**: We use `.filter()` *before* doing anything else, so we don't carry useless data through the pipeline.

### **10. Batch process to prevent out of memory errors?**
*   See `transform_orders_silver.py` Step 5.
*   Instead of `df.write()`, we do:
    ```python
    months = [(2019, 12), (2020, 1), ...]
    for year, month in months:
        batch = read_data(year, month)
        batch.writeTo(table).append()
    ```
*   This ensures we never hold more than ~1 month of data (approx. 50MB-100MB) in RAM at once, keeping us safely under the 4GB limit.

