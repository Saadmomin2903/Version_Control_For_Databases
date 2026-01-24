# Oracle Object Storage - lakehouse-prod

**Created**: January 22, 2026

---

## Quick Reference

| Property | Value |
|----------|-------|
| **Bucket Name** | `lakehouse-prod` |
| **Namespace** | `bmcfe6z38foz` |
| **Region** | ap-mumbai-1 |
| **Endpoint** | `https://objectstorage.ap-mumbai-1.oraclecloud.com` |

---

## S3-Compatible Access

```bash
# S3 Endpoint URL
https://bmcfe6z38foz.compat.objectstorage.ap-mumbai-1.oraclecloud.com

# Bucket Path
s3://lakehouse-prod/
```

---

## Bucket Details

| Property | Value |
|----------|-------|
| **Compartment** | shivamk14 (root) |
| **Created** | Jan 22, 2026, 13:15 UTC |
| **ETag** | fa101b74-9e63-41c9-8913-e6f3b71ff405 |
| **Current Size** | 0 bytes |
| **Object Count** | 0 |

---

## OCID

```
ocid1.bucket.oc1.ap-mumbai-1.aaaaaaaamnny3xe7pcs7rhbcgzkjtfvgnltelhxef53na4nkcvxhybe5xpgq
```

---

## Free Tier Limits

| Type | Limit | Used |
|------|-------|------|
| Object Storage | 10 GB | 0 bytes |
| Archive Storage | 10 GB | 0 bytes |
| **Total** | 20 GB | 0 bytes |

---

## AWS CLI Configuration

For S3-compatible access, use:

```bash
# ~/.aws/config
[profile oracle]
region = ap-mumbai-1
output = json

# Endpoint for commands
--endpoint-url https://bmcfe6z38foz.compat.objectstorage.ap-mumbai-1.oraclecloud.com
```

---

## Usage Examples

```bash
# List bucket contents
aws s3 ls s3://lakehouse-prod/ \
    --endpoint-url https://bmcfe6z38foz.compat.objectstorage.ap-mumbai-1.oraclecloud.com

# Upload file
aws s3 cp myfile.csv s3://lakehouse-prod/raw/ \
    --endpoint-url https://bmcfe6z38foz.compat.objectstorage.ap-mumbai-1.oraclecloud.com
```

---

## Environment Variables for Scripts

```bash
export ORACLE_NAMESPACE=bmcfe6z38foz
export ORACLE_REGION=ap-mumbai-1
export ORACLE_ENDPOINT=https://bmcfe6z38foz.compat.objectstorage.ap-mumbai-1.oraclecloud.com
export WAREHOUSE=s3a://lakehouse-prod/warehouse
```

---

## Next Steps

1. ✅ Bucket created
2. ⬜ Generate S3 API keys (Customer Secret Keys)
3. ⬜ Configure AWS CLI
4. ⬜ Upload Firebolt dataset
