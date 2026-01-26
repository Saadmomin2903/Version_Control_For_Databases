# VM3 - Trino Query Engine Server

**Created**: January 26, 2026

---

## Quick Access

```bash
# SSH Command
ssh -i key3/oracle-vm3.key ubuntu@161.118.185.218
```

---

## Instance Details

| Property | Value |
|----------|-------|
| **Name** | lakehouse-trino-vm3 |
| **Status** | Running ✅ |
| **Public IP** | `161.118.185.218` |
| **Private IP** | `10.0.0.247` |
| **Username** | `ubuntu` |

---

## Configuration

| Property | Value |
|----------|-------|
| **Shape** | VM.Standard.E5.Flex |
| **OCPU** | 2 |
| **Memory** | 24 GB |
| **Network** | 2 Gbps |
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
| **Hostname** | trino-vm3-vnic |
| **Internal FQDN** | trino-vm3-vnic.sub01211221430.lakehousevcn.oraclevcn.com |

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
ocid1.instance.oc1.ap-mumbai-1.anrg6ljrvi2ctdacw3dda6nvi4vhguua7a4ovikyvi6hflpulu3lase7l43a
```

---

## Services to Deploy

- Trino Query Engine (port 8090)
- SQL access to Iceberg tables

---

## All VMs Summary

| VM | Name | Public IP | Private IP | Shape | Memory | Purpose |
|----|------|-----------|------------|-------|--------|---------|
| VM1 | airflow-nessie | 140.238.224.207 | 10.0.0.148 | E5.Flex | 12 GB | Control Plane |
| VM2 | spark-cluster | 140.245.16.49 | 10.0.0.108 | E5.Flex | 12 GB | Compute Plane |
| VM3 | lakehouse-trino-vm3 | 161.118.185.218 | 10.0.0.247 | E5.Flex | 24 GB | Query Engine |

---

## Next Steps

1. ✅ VM3 Created
2. ⬜ SSH into VM3
3. ⬜ Install Docker
4. ⬜ Deploy Trino container
5. ⬜ Verify SQL access to Iceberg tables
