# Deployment Status - Version Control for Databases

**Last Updated**: 2026-01-23 01:17 IST

## ✅ Infrastructure Status

### VM1 (airflow-nessie)
| Component | Status | Port | Access |
|-----------|--------|------|--------|
| **Docker** | ✅ Running | - | - |
| **PostgreSQL** | ✅ Running | 5432 | Local only |
| **Nessie** | ✅ Running | 19120 | http://140.238.224.207:19120/api/v2/config |
| **Spark Master** | ✅ Running | 7077 | - |
| **Spark UI** | ✅ Running | 8081 | http://140.238.224.207:8081 |
| **Jupyter** | ✅ Running | 8888 | http://140.238.224.207:8888 |

**SSH Access**:
```bash
ssh -i ~/.ssh/oracle-vm1.key ubuntu@140.238.224.207
```

**Get Jupyter Token**:
```bash
docker logs lakehouse-spark 2>&1 | grep token
```

---

### VM2 (spark-cluster)
| Component | Status | Notes |
|-----------|--------|-------|
| **Docker** | ✅ Running | v28.2.2 |
| **Docker Compose** | ✅ Installed | v2.23.3 |
| **Repo Cloned** | ✅ Done | ~/Version_Control_For_Databases |
| **Nessie Connection** | ✅ Working | Can reach VM1 |

**SSH Access**:
```bash
ssh -i ~/.ssh/oracle-vm2.key ubuntu@140.245.16.49
```

---

## Oracle Cloud Resources

### Object Storage
| Resource | Value |
|----------|-------|
| Bucket | lakehouse-prod |
| Namespace | bmcfe6z38foz |
| Region | ap-mumbai-1 |
| Endpoint | https://bmcfe6z38foz.compat.objectstorage.ap-mumbai-1.oraclecloud.com |

### Network
| VM | Public IP | Private IP |
|----|-----------|------------|
| VM1 | 140.238.224.207 | 10.0.0.148 |
| VM2 | 140.245.16.49 | 10.0.0.x |

---

## Nessie Catalog Info

```json
{
  "defaultBranch": "main",
  "repositoryCreationTimestamp": "2026-01-22T18:01:58Z",
  "specVersion": "2.1.0"
}
```

---

## Key Learnings & Fixes Applied

### 1. Supabase IPv6 Issue
**Problem**: Oracle VMs don't support IPv6, but Supabase only provides IPv6 addresses.
**Solution**: Installed PostgreSQL locally on VM1 for Nessie catalog storage.

### 2. Docker → PostgreSQL Connectivity
**Problem**: Docker containers can't connect to host's localhost.
**Solution**: 
- Used Docker gateway IP (172.18.0.1) in JDBC URL
- Configured pg_hba.conf to allow Docker network connections
- Set listen_addresses = '*' in postgresql.conf

### 3. Oracle S3 Upload Issue
**Problem**: AWS CLI `s3 cp` doesn't work with Oracle Object Storage (Content-Length header issue).
**Solution**: Use curl with `--aws-sigv4` for uploads instead.

---

## Next Steps

- [ ] Upload parquet data to Oracle Storage
- [ ] Run Bronze → Silver → Gold pipeline
- [ ] Test Nessie branching and time-travel
- [ ] Configure Airflow for orchestration

---

## Cost Status

| Resource | Cost |
|----------|------|
| Oracle Cloud (Always Free) | $0.00 |
| Supabase (Free Tier) | $0.00 |
| **Total** | **$0.00** |
