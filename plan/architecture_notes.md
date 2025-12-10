# Architecture & Implementation Notes

## Current Working Implementation

**Technology Stack:**
- ✅ **PySpark 3.3** - Data processing and ingestion
- ✅ **Nessie** - Git-like version control for tables
- ✅ **MinIO** - S3-compatible object storage
- ✅ **Apache Iceberg 1.3.1** - Table format
- ✅ **Docker** - Containerized services

## Why PySpark Instead of PyIceberg?

### What We Initially Tried
- PyIceberg with Nessie REST Catalog
- Nessie configured to vend S3 credentials
- Complex URN secret reference system

### Why It Didn't Work
1. **Complex Nessie Configuration**: Nessie S3 setup with URN secrets was not being recognized
2. **Environment Variable Issues**: Quarkus property naming conventions were unclear
3. **Version Compatibility**: Nessie 0.99.0 had undocumented requirements
4. **Error Messages**: "Missing access key and secret for STATIC authentication mode"

### What Works Now
1. **Simple Nessie**: No S3 configuration in Nessie at all
2. **Spark Handles S3**: PySpark connects directly to MinIO with AWS credentials
3. **Nessie Tracks Metadata**: Only responsible for version control, not data access
4. **Proven Pattern**: Matches official Nessie + Spark tutorials

## Architecture Diagram

```
CSV Files
    ↓
┌─────────────────┐
│   PySpark       │
│   (Container)   │
│                 │
│  - Reads CSV    │
│  - Transforms   │
│  - Writes S3    │
└────────┬────────┘
         │
         ├──────────────┐
         ▼              ▼
  ┌──────────┐   ┌──────────┐
  │  MinIO   │   │  Nessie  │
  │  (S3)    │   │ (Catalog)│
  │          │   │          │
  │ Stores   │   │ Tracks   │
  │ Data     │   │ Versions │
  └──────────┘   └──────────┘
```

## File Organization

### Active Files (PySpark Implementation)
- ✅ `scripts/bronze/ingest_orders_spark.py` - Orders ingestion
- ✅ `scripts/bronze/ingest_customers_spark.py` - Customers ingestion
- ✅ `docker-compose.yml` - Infrastructure definition
- ✅ `config/iceberg_config.py` - Configuration (updated for PySpark)

### Legacy Files (PyIceberg - Not Used)
- ⚠️ `scripts/bronze/ingest_orders.py` - Old PyIceberg version
- ⚠️ `scripts/bronze/ingest_customers.py` - Old PyIceberg version
- ⚠️ `scripts/utils/storage_utils.py` - Contains PyIceberg utilities (kept for reference)

**Note**: Legacy files are kept for reference but not actively used.

## How to Run

### Start Infrastructure
```bash
docker compose up -d
```

### Create MinIO Bucket
```bash
docker exec lakehouse-minio mc alias set myminio http://localhost:9000 admin password123
docker exec lakehouse-minio mc mb myminio/lakehouse --ignore-existing
```

### Run Bronze Ingestion
```bash
# Orders
docker exec lakehouse-spark python3 /home/jovyan/scripts/bronze/ingest_orders_spark.py

# Customers
docker exec lakehouse-spark python3 /home/jovyan/scripts/bronze/ingest_customers_spark.py
```

### Query Data (Jupyter)
Access http://localhost:8888 and run:
```python
spark.sql("SELECT * FROM nessie.ecommerce.orders_bronze LIMIT 10").show()
```

## Key Learnings

### 1. Nessie Doesn't Need S3 Config
When using **Spark NessieCatalog**, Nessie only tracks metadata.
Spark handles all S3 operations directly.

### 2. Disk Space Matters
Spark container is ~3.3GB. Ensure at least 10GB free disk space.

### 3. Environment Variables in Docker
Use underscores for env vars in docker-compose:
```yaml
- AWS_ACCESS_KEY_ID=admin
- AWS_SECRET_ACCESS_KEY=password123
```

### 4. Network Connectivity
- Inside Docker: Use service names (`http://minio:9000`)
- From host: Use localhost (`http://localhost:9000`)

## Troubleshooting

### "Connection refused" to MinIO
**Solution**: Ensure lakehouse bucket exists
```bash
docker exec lakehouse-minio mc mb myminio/lakehouse --ignore-existing
```

### "Python not found" in container
**Solution**: Use `python3` instead of `python`
```bash
docker exec lakehouse-spark python3 script.py
```

### Spark JARs downloading slowly
**First run downloads ~400MB of dependencies. Subsequent runs use cached JARs.**

### Platform warning (amd64 vs arm64)
**Safe to ignore if container starts successfully.**

## References

- **Tutorial**: https://dev.to/alexmercedcoder/hands-on-with-apache-iceberg-on-your-laptop-deep-dive-with-apache-spark-nessie-minio-dremio-polars-and-seaborn-2hgk
- **GitHub Example**: https://github.com/domainio/iceberglakehouse
- **YouTube**: https://youtu.be/3hpW-BUCvi8

## Next Steps

- [ ] Implement Silver layer transformations
- [ ] Implement Gold layer aggregations
- [ ] Add data quality checks
- [ ] Set up orchestration (Airflow)
- [ ] Add comprehensive testing

---

**Last Updated**: December 2025  
**Status**: Bronze Layer Working ✅
