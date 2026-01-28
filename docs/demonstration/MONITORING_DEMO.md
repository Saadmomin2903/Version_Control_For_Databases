# Monitoring Stack Demo Guide

This guide explains how to access and demonstrate the Observability layer of our Data Lakehouse, powered by **Prometheus** (Metrics) and **Grafana** (Visualization).

## 1. Access & Credentials

*   **Grafana URL:** `http://140.238.224.207:3000`
*   **Prometheus URL:** `http://140.238.224.207:9090` (For debugging only)
*   **Default Credentials:** `admin` / `admin` (You will be asked to change password on first login)

> [!IMPORTANT]
> **Firewall Action Required:**
> You must open the following ports in your Oracle Cloud Ingress Security List (VM1) to access these URLs:
> *   **TCP 3000** (Grafana)
> *   **TCP 9090** (Prometheus - optional, for debugging)

## 2. Setup Walkthrough (One-Time)

*Since this is a fresh deployment, you must connect Grafana to Prometheus manually.*

1.  **Login to Grafana.**
2.  **Add Data Source:**
    *   Click **Connections** -> **Data Sources**.
    *   Click **Add data source**.
    *   Select **Prometheus**.
    *   **URL:** `http://prometheus:9090` (Note: Use the container name, not localhost).
    *   Click **Save & Test**. You should see "Successfully queried the Prometheus API."

3.  **Import Dashboard:**
    *   Click **Dashboards** -> **New** -> **Import**.
    *   **ID:** Type `1860` (This is the official "Node Exporter Full" dashboard).
    *   Click **Load**.
    *   Select the **Prometheus** data source you just added.
    *   Click **Import**.

## 3. Demonstration Scenarios

### Scenario A: Infrastructure Health
1.  Open the **Node Exporter Full** dashboard.
2.  **CPU Usage:** Show the live CPU load of VM1. It might be high due to Spark/Airflow/OpenMetadata all running here.
3.  **Memory:** Check RAM usage. We are running many containers; this graph proves we are monitoring resource exhaustion limits.

### Scenario B: Service Up-Time
1.  Go to the **Prometheus** UI (`:9090`).
2.  Click **Status** -> **Targets**.
3.  Show that `node-exporter` is "UP".
4.  **Talking Point:** "We have automated health checks. If a service dies, Prometheus knows instantly."

## 4. Technical Architecture

*   **Node Exporter:** Runs on the host (VM1), collects OS metrics (CPU, RAM, Disk).
*   **Prometheus:** Scrapes these metrics every 15 seconds.
*   **Grafana:** Queries Prometheus to render the beautiful charts.
*   **Docker Network:** All three communicate over the internal `monitoring-net` bridge network.
