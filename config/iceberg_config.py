import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# MinIO/S3 Configuration (from .env or defaults)
S3_ENDPOINT = os.getenv("S3_ENDPOINT", "http://localhost:9000")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY", "admin")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY", "password123")
S3_BUCKET = os.getenv("S3_BUCKET", "lakehouse")

# Nessie Configuration
NESSIE_URI = os.getenv("NESSIE_URI", "http://localhost:19120/api/v2")

# Iceberg Catalog Configuration
CATALOG_CONFIG = {
    "type": "rest",
    "uri": NESSIE_URI,
    "warehouse": f"s3://{S3_BUCKET}/warehouse",
    "s3.endpoint": S3_ENDPOINT,
    "s3.access-key-id": S3_ACCESS_KEY,
    "s3.secret-access-key": S3_SECRET_KEY,
    "s3.path-style-access": "true",
    # Additional S3 settings for MinIO compatibility
    "s3.region": "us-east-1",  # MinIO doesn't care about region, but required
}

# Project Configuration
NAMESPACE = os.getenv("NAMESPACE", "ecommerce")
BRONZE_BRANCH = os.getenv("BRONZE_BRANCH", "bronze")
SILVER_BRANCH = os.getenv("SILVER_BRANCH", "silver")
GOLD_BRANCH = os.getenv("GOLD_BRANCH", "gold")

# Print configuration (without secrets) for verification
def print_config():
    print("=" * 60)
    print("LAKEHOUSE CONFIGURATION")
    print("=" * 60)
    print(f"S3 Endpoint: {S3_ENDPOINT}")
    print(f"S3 Bucket: {S3_BUCKET}")
    print(f"Nessie URI: {NESSIE_URI}")
    print(f"Namespace: {NAMESPACE}")
    print(f"Branches: {BRONZE_BRANCH}, {SILVER_BRANCH}, {GOLD_BRANCH}")
    print("=" * 60)

if __name__ == "__main__":
    print_config()