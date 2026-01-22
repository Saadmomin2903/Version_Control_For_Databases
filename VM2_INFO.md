# VM2 - Spark Cluster Server

**Created**: January 22, 2026

---

## Quick Access

```bash
# SSH Command
ssh -i ~/.ssh/oracle-vm2.key ubuntu@140.245.16.49
```

---

## Instance Details

| Property | Value |
|----------|-------|
| **Name** | spark-cluster |
| **Status** | Running ✅ |
| **Public IP** | `140.245.16.49` |
| **Private IP** | `10.0.0.108` |
| **Username** | `ubuntu` |

---

## Configuration

| Property | Value |
|----------|-------|
| **Shape** | VM.Standard.E5.Flex |
| **OCPU** | 1 |
| **Memory** | 12 GB |
| **Network** | 1 Gbps |
| **Boot Volume** | 47 GB |

---

## Location

| Property | Value |
|----------|-------|
| **Region** | ap-mumbai-1 |
| **Availability Domain** | AD-1 |
| **Fault Domain** | FD-3 |
| **Compartment** | shivamk14 (root) |

---

## Network

| Property | Value |
|----------|-------|
| **VCN** | lakehouse-vcn |
| **Subnet** | public subnet-lakehouse-vcn |
| **Hostname** | spark-cluster |
| **Internal FQDN** | spark-cluster.sub01211221430.lakehousevcn.oraclevcn.com |

---

## Image

| Property | Value |
|----------|-------|
| **OS** | Canonical Ubuntu 22.04 |
| **Image** | Canonical-Ubuntu-22.04-2025.10.31-0 |
| **In-Transit Encryption** | Enabled |

---

## OCID

```
ocid1.instance.oc1.ap-mumbai-1.anrg6ljrvi2ctdacd2aigwtnvhujlgprude46y5vdi7uhrzy54decoezudla
```

---

## Services to Deploy

- Spark Master (port 7077, 8081)
- Spark Worker
- Jupyter Notebook (port 8888)

---

## Both VMs Summary

| VM | Name | Public IP | Private IP | Shape | Memory |
|----|------|-----------|------------|-------|--------|
| VM1 | airflow-nessie | 140.238.224.207 | 10.0.0.148 | E5.Flex | 12 GB |
| VM2 | spark-cluster | 140.245.16.49 | 10.0.0.108 | E5.Flex | 12 GB |

---

## Next Steps

1. ✅ VM1 Created & SSH Working
2. ✅ VM2 Created
3. ⬜ Test VM2 SSH
4. ⬜ Install Docker on both VMs
5. ⬜ Deploy containers
