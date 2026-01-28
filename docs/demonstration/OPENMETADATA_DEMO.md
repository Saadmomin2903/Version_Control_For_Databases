# OpenMetadata Governance: Theory & Demo Guide

This document serves as both a **conceptual guide** to Data Governance and a **practical manual** for demonstrating the OpenMetadata platform installed in our Data Lakehouse.

---

## 🏗️ 1. Conceptual Theory: The "Why" & "How"

### What is Metadata?
Metadata is "data about data". It turns a "Data Swamp" (files on S3 that nobody understands) into a "Data Lake" (discoverable assets).
*   **Technical Metadata:** Schemas, data types (e.g., `order_id` is a `BIGINT`), table names.
*   **Operational Metadata:** Lineage (where did this data come from?), freshness, execution logs.
*   **Business Metadata:** Ownership (who is responsible?), Tags (e.g., `PII`, `Financial`), Descriptions.

### How OpenMetadata Works (The Architecture)
In our project, we use a **Pull-Based Ingestion** architecture. Using the "Push" model (sending data every time a job runs) is brittle. Instead, OpenMetadata actively *crawls* our systems.

**The Data Flow:**
1.  **Source of Truth:** Our data lives in **Iceberg Tables** on **S3 (Oracle Cloud)**, managed by the **Nessie Catalog**.
2.  **Gateway:** The **Spark Thrift Server** acts as the SQL interface to these tables. It knows the schemas because it talks to Nessie.
3.  **Ingestion Client:** We run a Dockerized ingestion connector (Python/Airflow based).
4.  **The Process:**
    *   The Ingestion Client connects to Spark Thrift via JDBC.
    *   It runs commands like `SHOW TABLES` and `DESCRIBE TABLE`.
    *   It extracts column names, types, and comments.
    *   It sends this packet to the **OpenMetadata Server** (Port 8585).
5.  **Storage:** The server indexes this in **Elasticsearch** (for search) and stores relationships in **MySQL**.

---

## 🚀 2. Demo Walkthrough Script

**URL:** `http://140.238.224.207:8585`
**Login:** `admin@openmetadata.org` / `admin`

### Part A: The "Google for Metadata" (Discovery)
*Goal: Show how easy it is to find data without asking colleagues.*

1.  **Dashboard Start:** Land on the "Activity Feed". Explain this is like a social feed for data changes.
2.  **Search Bar:** Type `orders` or `ecommerce`.
3.  **Results:** Point out the rich results. You don't just see a table name; you see:
    *   **Service:** `spark_thrift_ingestion_service`
    *   **Database:** `default`
    *   **Schema:** `ecommerce`
4.  **Click:** Select `orders_silver`.

### Part B: Deep Inspection (Technical Metadata)
*Goal: Prove we know exactly what is in the data.*

1.  **Schema Tab:** Scroll through the columns.
2.  **Highlight:**
    *   `order_id` (bigint)
    *   `customer_id` (string)
    *   `order_date` (date)
3.  **Theory Note:** Explain that this info was extracted automatically from the Iceberg metadata files on S3 via the Thrift Server.

### Part C: Data Lineage (Operational Metadata)
*Goal: The "Killer Feature" - proving we know the data's journey.*

1.  Click the **Lineage** tab (top right of the table view).
2.  **Visual Graph:** You will see a node connection graph.
    *   **Left Node:** `orders_bronze` (Raw data)
    *   **Right Node:** `orders_silver` (Cleaned data)
3.  **Interaction:** Click on the connecting line.
    *   **Explanation:** OpenMetadata parsed the Spark SQL plans to understand that `INSERT INTO silver SELECT * FROM bronze` created this relationship.
    *   **Impact:** If `orders_bronze` contains bad data, we instantly know `orders_silver` is affected.

### Part D: Governance & Tagging (Business Metadata)
*Goal: Show how we manage sensitive data.*

1.  Go back to the **Schema** tab of `orders_silver`.
2.  Find the `customer_id` column.
3.  **Action:** Click the **Add Tag** (plus icon) next to it.
4.  **Select:** Choose a tag like `PII.Sensitive` or create a generic `Sensitive` tag.
5.  **Save:** The column is now flagged.
6.  **Impact:** In a production setup, this tag could automatically trigger masking policies (e.g., hiding the ID from junior analysts) via Ranger or IAM integration.

---

## 3. Technical Implementation Details for Examiners

If asked "How did you connect this?", use these technical points:

1.  **Connector:** We used the `Hive` connector type because Spark Thrift Server is HiveServer2 compatible.
2.  **Classpath Challenges:** The biggest challenge was the **Spark Classpath**. The Thrift Server needed:
    *   `hadoop-aws` & `aws-java-sdk` (for S3 access).
    *   `iceberg-spark-runtime` (for table format).
    *   `nessie-client` (for catalog version control).
3.  **Resolution:** We manually injected these JARs into the Docker container and configured the `spark.sql.catalog.nessie` properties to point to our Nessie deployment.
4.  **Ingestion:** We used the OpenMetadata Docker CLI to run a one-time ingestion:
    ```bash
    metadata ingest -c /config.yaml
    ```

---

## 4. Next Steps
*   **Monitoring:** We will next deploy Prometheus & Grafana to monitor the health of these services.
*   **Data Quality:** Future work could involve adding Great Expectations tests to the ingestion pipeline to flag quality issues directly in this UI.
