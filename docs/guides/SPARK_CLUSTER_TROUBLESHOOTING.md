# Multi-VM Spark Cluster Setup & Troubleshooting Guide

This document captures all the issues encountered and solutions for setting up a distributed Spark cluster across Oracle Cloud VMs.

## Architecture Overview

```
┌─────────────────────────────────────┐      ┌─────────────────────────────────────┐
│           VM1 (10.0.0.148)          │      │           VM2 (10.0.0.108)          │
│         Public: 140.238.224.207     │      │         Public: 140.245.16.49       │
├─────────────────────────────────────┤      ├─────────────────────────────────────┤
│  ┌─────────────────────────────┐    │      │  ┌─────────────────────────────┐    │
│  │   lakehouse-spark           │    │      │  │   spark-worker              │    │
│  │   - Spark Master (7077)     │◄───┼──────┼──►   - Spark Worker            │    │
│  │   - Spark Driver            │    │      │  │   - 2 Executors (2G each)   │    │
│  │   - Jupyter (8888)          │    │      │  └─────────────────────────────┘    │
│  └─────────────────────────────┘    │      │                                     │
│  ┌─────────────────────────────┐    │      │  network_mode: host                 │
│  │   lakehouse-nessie (19120)  │    │      │  (uses VM2's host network directly) │
│  └─────────────────────────────┘    │      │                                     │
│                                     │      │                                     │
│  network_mode: host                 │      │                                     │
│  (uses VM1's host network directly) │      │                                     │
└─────────────────────────────────────┘      └─────────────────────────────────────┘
                    │
                    ▼
         ┌─────────────────────────────┐
         │  Oracle Object Storage       │
         │  Region: ap-mumbai-1         │
         │  Bucket: lakehouse-prod      │
         └─────────────────────────────┘
```

## Critical Configuration Summary

### VM1 (docker-compose-production.yml)
```yaml
spark-notebook:
  network_mode: host                     # CRITICAL: Exposes driver port to VM2
  extra_hosts:
    - "spark-master:10.0.0.148"          # Self-reference for hostname resolution
  environment:
    - NESSIE_URI=http://localhost:19120/api/v1  # localhost, not 'nessie' (host networking)
```

### VM2 (docker-compose-vm2-worker.yml)
```yaml
spark-worker:
  network_mode: host                     # CRITICAL: Enables routing to VM1
  extra_hosts:
    - "spark-master:10.0.0.148"          # Resolves spark-master hostname
```

### Python Script (build_gold_layer.py)
```python
.set("spark.driver.host", "10.0.0.148")       # VM1 private IP
.set("spark.driver.bindAddress", "0.0.0.0")   # Bind to all interfaces
.set('spark.executor.memory', '2g')           # Must fit in worker memory
```

---

## Issues Encountered & Solutions

### Issue 1: Oracle Object Storage Wrong Region
**Error:**
```
The authorization header is malformed; region us-ashburn-1 is wrong; expecting ap-mumbai-1
```

**Root Cause:** Default region was set to `us-ashburn-1` but bucket is in `ap-mumbai-1`

**Solution:** Set correct region in script:
```python
AWS_REGION = "ap-mumbai-1"
```

---

### Issue 2: "No route to host" from VM2 to VM1
**Error:**
```
NoRouteToHostException: No route to host: /10.0.0.148:34771
```

**Root Cause:** Docker bridge network (172.x.x.x) can't route to VCN private IPs

**Solution:** Use `network_mode: host` on both VMs:
```yaml
services:
  spark-worker:
    network_mode: host
```

---

### Issue 3: Executor can't resolve "spark-master" hostname
**Error:**
```
Failed to connect to /10.0.0.148:34771
--driver-url "spark://CoarseGrainedScheduler@spark-master:43731"
```

**Root Cause:** With host networking, Docker DNS doesn't work. Executors can't resolve `spark-master`

**Solution:** Add `extra_hosts` to both compose files:
```yaml
extra_hosts:
  - "spark-master:10.0.0.148"
```

---

### Issue 4: "Connection refused" on driver port
**Error:**
```
ConnectException: Connection refused: /10.0.0.148:34771
```

**Root Cause:** VM1's Spark container was using bridge networking. Driver binds inside container, not exposed to VM2

**Solution:** Use `network_mode: host` on VM1 so driver port is directly on host network

---

### Issue 5: VM1 firewall blocking VM2 connections
**Error:**
```
NoRouteToHostException: No route to host: /10.0.0.148:7077
```

**Root Cause:** Oracle Cloud iptables has a REJECT rule that blocks inter-VM traffic

**Solution:** Add iptables rules on VM1:
```bash
# Allow Spark Master port
sudo iptables -I INPUT 1 -p tcp --dport 7077 -s 10.0.0.0/24 -j ACCEPT

# Allow dynamic driver ports (30000-50000)
sudo iptables -I INPUT 1 -p tcp --dport 30000:50000 -s 10.0.0.0/24 -j ACCEPT
```

**To persist after reboot:**
```bash
sudo iptables-save | sudo tee /etc/iptables.rules
echo 'iptables-restore < /etc/iptables.rules' | sudo tee -a /etc/rc.local
sudo chmod +x /etc/rc.local
```

---

### Issue 6: Spark Master hostname resolution failure
**Error:**
```
UnknownHostException: spark-master: Temporary failure in name resolution
```

**Root Cause:** `hostname: spark-master` in compose doesn't work with `network_mode: host`

**Solution:** Remove `hostname:` and add `extra_hosts` instead:
```yaml
# DON'T USE:
hostname: spark-master

# USE:
extra_hosts:
  - "spark-master:10.0.0.148"
```

---

### Issue 7: "App requires more resource than any Worker"
**Error:**
```
WARN Master: App requires more resource than any of Workers could have
```

**Root Cause:** Executor memory (4g) > Worker memory (4g after overhead)

**Solution:** Reduce executor memory:
```python
.set('spark.executor.memory', '2g')  # Must be < worker memory - overhead
```

---

### Issue 8: Executors continuously exiting with code 1
**Symptom:**
```
Executor finished with state EXITED message Command exited with code 1
```

**Debug command:**
```bash
docker exec spark-worker find /opt/spark/work -name "stderr" -exec cat {} \; | head -50
```

**Common causes:**
1. Can't connect to driver (firewall/network)
2. Hostname resolution failed
3. Out of memory

---

## Verification Commands

### Check Worker Registration
```bash
# On VM2
docker logs spark-worker 2>&1 | grep -i "registered"
# Expected: "Successfully registered with master spark://0.0.0.0:7077"

# On VM1
docker logs lakehouse-spark 2>&1 | grep -i "register" | tail -5
# Expected: "Registering worker 10.0.0.108:xxxxx with 2 cores, 4.0 GiB RAM"
```

### Test Connectivity from VM2 to VM1
```bash
# From VM2 host
nc -zv 10.0.0.148 7077
# Expected: "Connection to 10.0.0.148 7077 port [tcp/*] succeeded!"
```

### Check Executor Logs for Errors
```bash
docker exec spark-worker find /opt/spark/work -name "stderr" -exec cat {} \; 2>/dev/null | tail -30
```

### Verify iptables Rules on VM1
```bash
sudo iptables -L INPUT -n --line-numbers | head -10
# Should show:
# 1 ACCEPT tcp -- 10.0.0.0/24 0.0.0.0/0 tcp dpt:7077
# 2 ACCEPT tcp -- 10.0.0.0/24 0.0.0.0/0 tcp dpts:30000:50000
```

---

## Startup Procedure

### 1. Start VM1 Stack
```bash
cd ~/Version_Control_For_Databases
docker-compose -f docker-compose-production.yml up -d
sleep 30
docker logs lakehouse-spark 2>&1 | tail -5
# Verify: "Successfully started service 'sparkMaster' on port 7077"
```

### 2. Apply Firewall Rules (if not persistent)
```bash
sudo iptables -I INPUT 1 -p tcp --dport 7077 -s 10.0.0.0/24 -j ACCEPT
sudo iptables -I INPUT 1 -p tcp --dport 30000:50000 -s 10.0.0.0/24 -j ACCEPT
```

### 3. Start VM2 Worker
```bash
cd ~/Version_Control_For_Databases
docker-compose -f docker-compose-vm2-worker.yml up -d
sleep 20
docker logs spark-worker 2>&1 | grep -i "registered"
# Verify: "Successfully registered with master"
```

### 4. Run Jobs
```bash
# On VM1
docker exec lakehouse-spark python3 /home/jovyan/scripts/gold/build_gold_layer.py
```

---

## Adding More Workers (VM3, VM4, etc.)

1. Deploy same `docker-compose-vm2-worker.yml` to new VM
2. Update `extra_hosts` if needed for new VM's private IP
3. Ensure Oracle Cloud VCN Security List allows traffic on ports 7077, 8080-8082, 30000-50000
4. Add iptables rules on VM1 to accept from new VM's subnet

---

## Troubleshooting Checklist

If cluster stops working, check in order:

1. ☐ Are all containers running? (`docker ps`)
2. ☐ Can VM2 reach VM1? (`nc -zv 10.0.0.148 7077`)
3. ☐ Are iptables rules in place on VM1?
4. ☐ Is worker registered? (Check logs on both VMs)
5. ☐ Are executors starting? (Check spark-worker logs)
6. ☐ What error in executor stderr? (Check /opt/spark/work/)

---

*Document created: 2026-01-25*
*Last updated after successful multi-VM cluster deployment*
