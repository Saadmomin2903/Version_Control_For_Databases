# Troubleshooting: Jupyter Notebook (VM2)

If you cannot access Jupyter at `http://140.245.16.49:8888` (e.g., "Connection Refused"), follow these steps to restart the service.

## 1. Connect to VM2
Open your terminal and SSH into the Spark Cluster VM:

```bash
ssh -i ~/.ssh/oracle-vm2.key ubuntu@140.245.16.49
```

## 2. Check Service Status
Run this command to see if the Jupyter container (`spark-master`) is running:

```bash
docker ps -a
```
*   **Status `Up`:** It is running.
*   **Status `Exited`:** It has crashed or stopped. This causes the connection error.

## 3. Restart the Service
If it is stopped (or to force a restart), run these commands:

```bash
# Remove old containers/ghost processes
docker rm -f spark-master spark-worker

# Go to the project directory
cd lakehouse

# Start the stack (Detach mode)
docker-compose -f docker-compose-spark.yml up -d
```

## 4. Retrieve the Login Token
After restarting, you need the new security token to log in.

```bash
docker logs spark-master 2>&1 | grep 'token='
```

**Look for output like this:**
`http://spark-master:8888/?token=9b1e7d6cd2f...`

Copy the token part (e.g., `9b1e7d6...`) and use it to log in at `http://140.245.16.49:8888`.
