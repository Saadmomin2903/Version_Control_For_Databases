# 🧠 Machine Learning in the Lakehouse
This document explains exactly how the "Intelligence" layer of our Data Lakehouse works. We use **Apache Spark MLlib** to run distributed machine learning directly on our Silver data.

---

## 1. 👥 Customer Segmentation (Clustering)
**Goal:** Group customers based on their buying behavior to target them with specific marketing campaigns (e.g., "VIP Rewards" vs "Win-back Campaign").

### 🔬 The Algorithm: K-Means Clustering
We use **K-Means**, an unsupervised learning algorithm that groups data points into $K$ clusters by minimizing the distance between points and their cluster center.

### ⚙️ The Process:
1.  **Input Data (`orders_silver`)**:
    We read the clean transaction history from the Silver layer.
2.  **Feature Engineering (RFM)**:
    We transform raw orders into **RFM Metrics** for each customer:
    *   **R**ecency: (Not used in this simplified version, but typically "Days since last purchase")
    *   **F**requency: Total count of orders.
    *   **M**onetary: Total amount spent ($).
    *   **A**vg Order Value: Average spend per order.
3.  **Scaling**:
    We use `StandardScaler` to normalize the data (so that High Revenue doesn't dominate High Frequency just because the numbers are bigger).
4.  **Training**:
    Spark iterates to find the optimal 4-6 clusters.
5.  **Labeling**:
    We assign business-friendly names based on the cluster's average spend:
    *   👑 **Whales:** Highest Spend & Frequency
    *   💎 **VIP:** High Spend
    *   🥇 **Gold / Medium:** Average
    *   🥈 **Low Value:** Rare, low spend

### 💾 Output Table: `nessie.ecommerce.customer_segments`
| customer_id | frequency | monetary | cluster_id | segment_name |
| :--- | :--- | :--- | :--- | :--- |
| CUST_123 | 52 | $12,500 | 5 | Whales |
| CUST_456 | 2 | $45 | 0 | Low Value |

### 📉 Model Evaluation (Test Results)
Since this is **Unsupervised Learning** (we don't have "Ground Truth" labels), we cannot calculate Accuracy. Instead, we use:
*   **Silhouette Score:** Measures how similar an object is to its own cluster compared to other clusters.
    *   *Our Target:* $> 0.5$ (Indicates good separation).
    *   *Where to find it:* Printed in the execution logs when running the script.

---

## 2. 🛍️ Product Recommendations (Market Basket Analysis)
**Goal:** Suggest products to users based on what other users bought (e.g., "People who bought iPhone also bought AirPods").

### 🔬 The Algorithm: FPGrowth
We use **FPGrowth (Frequent Pattern Growth)**, an algorithm that finds frequent itemsets in transaction databases to generate **Association Rules**.

### ⚙️ The Process:
1.  **Input Data (`orders_silver`)**:
    We look only at "Purchase" events.
2.  **Basket Creation**:
    We group items by `user_session`.
    *   *Session A:* `[iPhone, Case, Charger]`
    *   *Session B:* `[iPhone, Case]`
3.  **Pattern Mining**:
    The algorithm finds items that appear together often.
    *   *Rule:* If `iPhone` is in basket -> Then `Case` is likely in basket.
4.  **Scoring (Confidence & Lift)**:
    *   **Confidence:** How often the rule is true (e.g., 80% of iPhone buyers buy a Case).
    *   **Lift:** How much more likely the items are to be bought together than randomly.

### 💾 Output Table: `nessie.ecommerce.product_recommendations`
| Antecedent (If) | Consequent (Then) | Confidence | Lift |
| :--- | :--- | :--- | :--- |
| `[iPhone 15]` | `[MagSafe Case]` | 0.85 | 3.2 |
| `[PlayStation 5]` | `[Controller]` | 0.92 | 4.5 |

---

## 🚀 How to Run It?
You don't need to write this code every time. The pipelines are packaged in the `scripts/gold/` directory:

1.  **Run Segmentation:**
    ```bash
    python3 scripts/gold/customer_segmentation_simple.py
    ```

2.  **Run Recommendations:**
    ```bash
    python3 scripts/gold/product_recommendation_iceberg.py
    ```
