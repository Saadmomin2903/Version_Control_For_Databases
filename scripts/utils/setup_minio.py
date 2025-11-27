import sys
import os
from minio import Minio
from minio.error import S3Error

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from config.iceberg_config import S3_ENDPOINT, S3_ACCESS_KEY, S3_SECRET_KEY, S3_BUCKET

def setup_minio():
    """Create MinIO bucket if it doesn't exist"""
    print("=" * 60)
    print("SETTING UP MINIO")
    print("=" * 60)
    
    # Extract host and port from endpoint
    endpoint = S3_ENDPOINT.replace("http://", "").replace("https://", "")
    
    try:
        # Initialize MinIO client with named parameters
        client = Minio(
            endpoint=endpoint,
            access_key=S3_ACCESS_KEY,
            secret_key=S3_SECRET_KEY,
            secure=False  # Set to True for HTTPS
        )
        
        print(f"✓ Connected to MinIO at {S3_ENDPOINT}")
        
        # Check if bucket exists - FIXED: use bucket_name parameter
        if client.bucket_exists(bucket_name=S3_BUCKET):
            print(f"✓ Bucket '{S3_BUCKET}' already exists")
        else:
            # Create bucket - FIXED: use bucket_name parameter
            client.make_bucket(bucket_name=S3_BUCKET)
            print(f"✓ Created bucket: {S3_BUCKET}")
        
        # Verify bucket is accessible
        if client.bucket_exists(bucket_name=S3_BUCKET):
            print(f"✓ Bucket '{S3_BUCKET}' is accessible")
            
            # List all buckets
            print("\n" + "=" * 60)
            print("AVAILABLE BUCKETS")
            print("=" * 60)
            buckets = client.list_buckets()
            for bucket in buckets:
                print(f"  - {bucket.name}")
            
            return True
        else:
            print(f"✗ Failed to verify bucket '{S3_BUCKET}'")
            return False
            
    except S3Error as e:
        print(f"✗ MinIO S3 Error: {e}")
        return False
    except Exception as e:
        print(f"✗ Error connecting to MinIO: {e}")
        print(f"  Endpoint: {S3_ENDPOINT}")
        print(f"  Bucket: {S3_BUCKET}")
        return False

if __name__ == "__main__":
    success = setup_minio()
    sys.exit(0 if success else 1)