# VM1 - Airflow & Nessie Server

**Created**: January 22, 2026

---

## Quick Access

```bash
# SSH Command
ssh -i ~/.ssh/oracle-vm1.key ubuntu@140.238.224.207
```

---

## Instance Details

| Property | Value |
|----------|-------|
| **Name** | airflow-nessie |
| **Status** | Running ✅ |
| **Public IP** | `140.238.224.207` |
| **Private IP** | `10.0.0.148` |
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
| **Hostname** | airflow-nessie |
| **Internal FQDN** | airflow-nessie.sub01211221430.lakehousevcn.oraclevcn.com |

---

## Image

| Property | Value |
|----------|-------|
| **OS** | Canonical Ubuntu 22.04 |
| **Image** | Canonical-Ubuntu-22.04-2025.10.31-0 |
| **Launch Mode** | PARAVIRTUALIZED |
| **In-Transit Encryption** | Enabled |

---

## OCID

```
ocid1.instance.oc1.ap-mumbai-1.anrg6ljrvi2ctdac45c4muzorkp7thu7wxgbivze7lkoqdtc2v367qxoekpq
```

---

## Services to Deploy

- Nessie Catalog (port 19120)
- Airflow Webserver (port 8080)
- Airflow Scheduler

---

## Next Steps

1. ✅ VM Created
2. ⬜ Test SSH connection
3. ⬜ Create VM2 (Spark)
4. ⬜ Install Docker
5. ⬜ Deploy containers
