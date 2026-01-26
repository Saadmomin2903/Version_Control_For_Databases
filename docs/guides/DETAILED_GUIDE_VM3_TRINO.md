# Ultra-Detailed Production Guide - Part 5 (Bonus)
## Setting Up VM3 for High-Performance Trino

---

## 🎯 What You'll Accomplish in Part 5

By the end of this guide, you will have:
- ✅ **VM3** running (Dedicated to Trino)
- ✅ **Docker** installed on VM3
- ✅ **Trino** deployed with full memory capacity (12GB Heap)
- ✅ **Connected** to Nessie (VM1) and Object Storage
- ✅ **Verified** high-speed SQL access

**Time Required**: 30-45 minutes
**Prerequisites**: Parts 1-4 completed

---

## Step 1: Create VM3 (The Query Engine)

### Step 1.1: Provision the VM
Follow the exact same steps from **Part 1, Step 4** to create a new instance, BUT use these details:

- **Name**: `lakehouse-trino-vm3`
- **Image**: Ubuntu 22.04
- **Shape**: Ampere (ARM) - **4 OCPU, 24 GB RAM** (If available)
    *   *Note: If you already used your Free Tier limits, try 2 OCPU / 12 GB RAM. Trino needs RAM!*
- **SSH Key**: Use the **same key** as VM1/VM2 (easier) OR generate a new `oracle-vm3.key`.

### Step 1.2: Get the IP Addresses
Once running, note down:
1.  **Public IP**: (e.g., `150.x.x.x`)
2.  **Private IP**: (e.g., `10.0.0.x`)

### Step 1.3: Configure Firewall (Security List)
Go to **Networking -> VCN -> Security Lists** and add an Ingress Rule for Trino:

- **Source**: `0.0.0.0/0`
- **Protocol**: TCP
- **Port**: `8090` (We will use 8090 to avoid conflict with anything else)
- **Description**: Trino UI

---

## Step 2: System Setup (On VM3)

### Step 2.1: SSH into VM3
```bash
# On your local machine
ssh -i ~/.ssh/oracle-vm1.key ubuntu@[VM3-PUBLIC-IP]
```

### Step 2.2: Install Docker (The Fast Way)
Copy-paste this entire block to install Docker in one go:

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y docker.io docker-compose-plugin git curl
sudo usermod -aG docker ubuntu
```

**Logout and Login** to apply the group change:
```bash
exit
ssh -i ~/.ssh/oracle-vm1.key ubuntu@[VM3-PUBLIC-IP]
```

---

## Step 3: Deployment Configuration

### Step 3.1: Clone the Repository
```bash
cd ~
git clone https://github.com/Saadmomin2903/Version_Control_For_Databases.git
cd Version_Control_For_Databases
```

### Step 3.2: Create Trino-Specific Environment File
We need a special `.env` for VM3 that points to VM1's Nessie server.

1.  **Find VM1's Private IP**:
    *   SSH into VM1 and run `hostname -I`.
    *   Let's assume it is `10.0.0.148`.

2.  **Create `.env.trino` on VM3**:
    ```bash
    nano .env.trino
    ```

3.  **Paste this Content** (Update the placeholders!):
    ```ini
    # --- ORACLE CLOUD STORAGE ---
    ORACLE_ACCESS_KEY=[Paste from local oracle-s3-credentials.txt]
    ORACLE_SECRET_KEY=[Paste from local oracle-s3-credentials.txt]
    ORACLE_REGION=ap-mumbai-1
    ORACLE_ENDPOINT=https://bmcfe6z38foz.compat.objectstorage.ap-mumbai-1.oraclecloud.com
    
    # --- NESSIE (Running on VM1) ---
    # Use VM1 PRIVATE IP here!
    NESSIE_URI=http://10.0.0.148:19120/api/v1
    ```

### Step 3.3: Create Dedicated Trino Compose File
Create `docker-compose-vm3-trino.yml`:

```bash
nano docker-compose-vm3-trino.yml
```

Paste this configuration (Optimized for 12GB+ RAM):

```yaml
version: "3"

services:
  trino:
    image: trinodb/trino:406
    container_name: lakehouse-trino
    ports:
      - "8090:8080"
    environment:
      - JAVA_TOOL_OPTIONS=-Xmx10G
    volumes:
      - ./trino/etc:/etc/trino
    # ENTRYPOINT INJECTION
    # This ensures the config files use the ENV vars from .env.trino
    entrypoint: >
      /bin/sh -c "
      export NESSIE_URI=$${NESSIE_URI} &&
      export ORACLE_ACCESS_KEY=$${ORACLE_ACCESS_KEY} &&
      export ORACLE_SECRET_KEY=$${ORACLE_SECRET_KEY} &&
      export ORACLE_REGION=$${ORACLE_REGION} &&
      export ORACLE_ENDPOINT=$${ORACLE_ENDPOINT} &&
      
      # 1. Inject Secrets into Iceberg Properties
      sed -i \"s|iceberg.nessie-catalog.uri=.*|iceberg.rest-catalog.uri=$${NESSIE_URI}/iceberg/|\" /etc/trino/catalog/iceberg.properties &&
      sed -i \"s|s3.aws-access-key=.*|s3.aws-access-key=$${ORACLE_ACCESS_KEY}|\" /etc/trino/catalog/iceberg.properties &&
      sed -i \"s|s3.aws-secret-key=.*|s3.aws-secret-key=$${ORACLE_SECRET_KEY}|\" /etc/trino/catalog/iceberg.properties &&
      sed -i \"s|s3.region=.*|s3.region=$${ORACLE_REGION}|\" /etc/trino/catalog/iceberg.properties &&
      sed -i \"s|s3.endpoint=.*|s3.endpoint=$${ORACLE_ENDPOINT}|\" /etc/trino/catalog/iceberg.properties &&
      
      # 2. Fix Catalog Type for Trino 406
      sed -i 's/iceberg.catalog.type=nessie/iceberg.catalog.type=rest/' /etc/trino/catalog/iceberg.properties &&
      
      # 3. Start Trino
      /usr/lib/trino/bin/launcher run
      "
    restart: always
```

---

## Step 4: Configure Memory & Catalogs

### Step 4.1: Tune JVM Config
Since this VM is *only* for Trino, we can give it maximum RAM.

```bash
nano trino/etc/jvm.config
```

Change `-Xmx4G` to `-Xmx10G` (or 80% of your VM's RAM).

```properties
-server
-Xmx10G
-XX:+UseG1GC
-XX:G1HeapRegionSize=32M
-XX:+UseGCOverheadLimit
-XX:+ExplicitGCInvokesConcurrent
-XX:+HeapDumpOnOutOfMemoryError
-XX:OnOutOfMemoryError=kill -9 %p
```

### Step 4.2: Tune Query Config
```bash
nano trino/etc/config.properties
```

Update to use more memory for queries:

```properties
coordinator=true
node-scheduler.include-coordinator=true
http-server.http.port=8080
query.max-memory=8GB
query.max-memory-per-node=4GB
discovery.uri=http://localhost:8080
```

---

## Step 5: Start & Verify

### Step 5.1: Launch Trino
```bash
# Load environment vars
source .env.trino

# Start Container
docker compose -f docker-compose-vm3-trino.yml up -d
```

### Step 5.2: Check Logs
```bash
docker logs -f lakehouse-trino
```
Wait about 60-90 seconds. You should see:
> `======== SERVER STARTED ========`

### Step 5.3: Test Query
Run a query directly inside the container to verify it can see the data created by Spark (on VM2) and managed by Nessie (on VM1):

```bash
docker exec -it lakehouse-trino trino
```

Then run SQL:
```sql
SHOW CATALOGS;
-- Should show 'iceberg'

USE iceberg.ecommerce;
SHOW TABLES;
-- Should show 'orders_bronze', 'orders_silver', etc.

SELECT count(*) FROM orders_silver;
-- Should return the count (e.g., 400M+)
```

---

## 🚀 You are Live!
You now have a **3-Node Lakehouse**:
1.  **VM1**: Control Plane (Airflow, Nessie)
2.  **VM2**: Compute Plane (Spark Cluster)
3.  **VM3**: Consumption Plane (Trino Query Engine)

This is a professional, scalable architecture.
