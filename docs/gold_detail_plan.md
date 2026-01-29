# Gold Layer: Business Aggregation & BI

> **Status**: Operational (Staging on `gold` branch)  
> **Focus**: KPI Calculation, Customer Segmentation, Business Logic  
> **Key Pattern**: Dimensional Modeling / Wide Tables

---

## 👶 ELI5: The "Magic" Behind the Scenes

Let's return to our **Big Library** one last time.

### 1. The Researchers (The Gold Layer) 👩‍🔬
- The **Bronze Room** holds the raw piled-up boxes.
- The **Silver Room** has clean, sorted books on shelves.
- But the **Mayor** (The CEO/Manager) doesn't have time to read 10,000 books to find out "Who reads the most?"
- So, we have **Researchers**.
- They run around the Silver Room, count the books, check the dates, and write a single **One-Page Report** for every visitor.

### 2. The Report Card (Customer Summary) 📝
- Instead of a list of every single book you ever borrowed, the Gold Layer creates a card that says:
    - **Name**: Bob
    - **Total Books Read**: 50
    - **Favorite Genre**: Sci-Fi
    - **Status**: **GOLD MEMBER** 🌟
- This is what we show to the Mayor. It's fast, easy to read, and tells a story.

### 3. The "Draft" Folder (Staging) 📂
- The Researchers don't publish this report to the town square immediately.
- They put it in a special "Drafts" folder (the `gold` branch).
- Only when the Chief Librarian signs off does it get copied to the "Public Board" (`main` branch) for everyone to see.

---

## 🛠️ Deep Dive: What Actually Happens in the Gold Layer?

The Gold Layer is designed for **Consumption**. It joins tables together so BI tools (like Superset, Tableau, PowerBI) don't have to do heavy lifting.

### **Workflow: Customer Summary Aggregation (`aggregate_customer_summary_gold.py`)**

1.  **Read from Silver**:
    - It pulls data from `customers_silver` and `orders_silver`.
    - Note: It reads from the `silver` branch (`@silver`), ensuring it uses the latest clean data.

2.  **Calculate Metrics (The Aggregation)**:
    - It groups all orders by `customer_id`.
    - **Math happens here**:
        - `count(order_id)` -> `total_orders`
        - `sum(total_amount)` -> `total_revenue`
        - `avg(total_amount)` -> `avg_order_value`

3.  **Business Logic (The Intelligence)**:
    - This is where we add value that didn't exist in the source data.
    - **Segmentation**: We label customers based on how much they spent (CLV - Customer Lifetime Value).
        - **Premium**: > $1000
        - **Gold**: > $500
        - **Silver**: > $100
        - **Bronze**: > $0
    - This logic is defined *here* in code, ensuring everyone uses the exact same definition of a "VIP Customer".

4.  **Write to Gold (Staging)**:
    - `spark.sql("CREATE OR REPLACE TABLE ... customer_summary@gold ...")`
    - The data is saved to the `gold` branch. It is NOT yet in Production (`main`).

---

## ❓ Q&A: Addressing Common Questions

### **1. Why do we need a Gold layer? Why not just query Silver?**
*   **Performance**: joining `customers` (1M rows) + `orders` (50M rows) takes time. Doing it once in Gold means the Dashboard loads in milliseconds.
*   **Consistency**: If every analyst defines "VIP" differently in their SQL queries, the numbers won't match. Gold defines it once for everyone.

### **2. What does "Staging" mean here?**
*   The `gold` branch acts as a generic "Staging" environment in our Nessie workflow.
*   We run our heavy aggregations here.
*   We can review the data: `SELECT * FROM customer_summary@gold`.
*   If the numbers look wrong (e.g., negative revenue), we fix the code and re-run. **Production users on `main` never saw the bad data.**

### **3. How does this get to Production?**
*   There is a separate "Promotion" step (often a merge or a specialized script).
*   Once we trust the data on `gold`, we merge `gold` -> `main`.

### **4. What are the key metrics we track?**
*   **Total Revenue**: Sum of all completed orders.
*   **Active vs Inactive**: Customers who have bought something vs those who just signed up.
*   **CLV**: Customer Lifetime Value (Crucial for marketing).

### **5. Can I see the results?**
*   **Yes!** Run the script, then query:
    ```sql
    SELECT customer_id, name, customer_segment, total_revenue 
    FROM nessie.ecommerce.`customer_summary@gold` 
    ORDER BY total_revenue DESC 
    LIMIT 5;
    ```

### **6. Is the data normalized?**
*   **No.** Gold tables are often **Denormalized** (Wide Tables).
*   We deliberately duplicate customer names onto the summary table so we don't have to join again later. Storage is cheap; Compute (time) is expensive.
