# Oracle Cloud Security List (Ingress Rules)

To fully access the Data Lakehouse services running on **VM1 (140.238.224.207)**, you must configure the following Ingress Rules in your Oracle Cloud VCN Security List.

## 🛡️ Critical Ports (User Interface & Access)

| Service Name | Port (TCP) | Description | Priority |
| :--- | :--- | :--- | :--- |
| **Apache Superset** | **8088** | Business Intelligence Dashboards | 🔴 High |
| **OpenMetadata** | **8585** | Data Governance UI | 🔴 High |
| **Grafana** | **3000** | Monitoring Dashboards | 🔴 High |
| **Spark Master UI** | **8080** | Spark Cluster Status | 🟡 Medium |
| **Spark Worker UI** | **8081** | Spark Worker Logs & Status | 🟡 Medium |

## 🔧 Technical Ports (Connectivity & Debugging)

| Service Name | Port (TCP) | Description | Reasons to Open |
| :--- | :--- | :--- | :--- |
| **Spark Thrift** | **10000** | JDBC/ODBC SQL Connection | Required if connecting TablePlus/DBeaver from your laptop. |
| **Prometheus** | **9090** | Metrics Backend | Debugging metric collection issues. |
| **Nessie API** | **19120** | Git-for-Data Catalog API | Debugging catalog connectivity. |
| **Node Exporter**| **9100** | VM1 System Metrics | Usually internal only, but open if you want to query from external Prometheus. |

## 📝 How to Add These Rules in Oracle Cloud

1.  Log in to **Oracle Cloud Console**.
2.  Navigate to **Networking** -> **Virtual Cloud Networks**.
3.  Click on your active **VCN**.
4.  Click **Security Lists** (usually `Default Security List...`).
5.  Click **Add Ingress Rules**.
6.  **Source CIDR:** `0.0.0.0/0` (Allows access from anywhere) -> *Recommended: Restrict to your specific laptop IP for security.*
7.  **IP Protocol:** `TCP`
8.  **Destination Port Range:** Enter the port (e.g., `8088`).
9.  **Description:** e.g., "Superset UI".
10. Click **Add Ingress Rules**.
