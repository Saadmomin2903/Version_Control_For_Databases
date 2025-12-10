import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

"""
CONFIGURATION FOR PYSPARK + NESSIE LAKEHOUSE

NOTE: This project uses PySpark with Nessie NessieCatalog, NOT PyIceberg.

Why PySpark instead of PyIceberg?
- PySpark handles S3 access directly (simpler configuration)
- Nessie only tracks metadata/versions (no complex S3 setup needed)
- Proven working pattern with Nessie + MinIO
- Better for distributed processing

The configuration below is for reference and local scripts.
PySpark scripts use environment variables directly from Docker container.
"""

# MinIO/S3 Configuration (from .env or defaults)
S3_ENDPOINT = os.getenv("S3_ENDPOINT", "http://localhost:9000")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY", "admin")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY", "password123")
S3_BUCKET = os.getenv("S3_BUCKET", "lakehouse")

# Nessie Configuration
NESSIE_URI = os.getenv("NESSIE_URI", "http://localhost:19120/api/v1")

# PySpark Configuration (used in Docker container)
# These are set in docker-compose.yml and read by PySpark scripts
PYSPARK_CONFIG = {
    "nessie.uri": NESSIE_URI,
    "warehouse": f"s3a://{S3_BUCKET}/warehouse",
    "s3.endpoint": S3_ENDPOINT,
    "s3.access-key-id": S3_ACCESS_KEY,
    "s3.secret-access-key": S3_SECRET_KEY,
    "s3.region": "us-east-1",
}

# Project Configuration
NAMESPACE = os.getenv("NAMESPACE", "ecommerce")
BRONZE_BRANCH = os.getenv("BRONZE_BRANCH", "main")  # Using main for simplicity
SILVER_BRANCH = os.getenv("SILVER_BRANCH", "main")
GOLD_BRANCH = os.getenv("GOLD_BRANCH", "main")

# Legacy PyIceberg configuration (kept for reference, not actively used)
# If you need to use PyIceberg for local testing, uncomment this:
# ICEBERG_REST_URI = os.getenv("ICEBERG_REST_URI", "http://localhost:19120/iceberg")
# CATALOG_CONFIG = {
#     "uri": ICEBERG_REST_URI,
#     "warehouse": f"s3://{S3_BUCKET}/warehouse",
#     "s3.endpoint": S3_ENDPOINT,
#     "s3.access-key-id": S3_ACCESS_KEY,
#     "s3.secret-access-key": S3_SECRET_KEY,
#     "s3.path-style-access": "true",
#     "s3.region": "us-east-1",
# }

# Print configuration (without secrets) for verification
def print_config():
    print("=" * 60)
    print("LAKEHOUSE CONFIGURATION (PySpark + Nessie)")
    print("=" * 60)
    print(f"S3 Endpoint: {S3_ENDPOINT}")
    print(f"S3 Bucket: {S3_BUCKET}")
    print(f"Nessie URI: {NESSIE_URI}")
    print(f"Namespace: {NAMESPACE}")
    print(f"Warehouse: s3a://{S3_BUCKET}/warehouse")
    print(f"Branch: {BRONZE_BRANCH}")
    print("=" * 60)
    print("\nNOTE: Using PySpark + Nessie NessieCatalog")
    print("Spark handles S3 directly, Nessie tracks metadata only")
    print("=" * 60)

if __name__ == "__main__":
    print_config()