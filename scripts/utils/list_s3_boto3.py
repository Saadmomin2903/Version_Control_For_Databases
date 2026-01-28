
import boto3
from botocore.client import Config
import os

def list_s3_files_boto3():
    # Credentials from ingest_orders_spark.py
    ACCESS_KEY = "962c9f862226831e4edea90cfcfafb8a8dffcd51"
    SECRET_KEY = "sd2rGU918DTmn35E4xJ8EV7BX2XUt7DkqC8v6WDNDUw="
    ENDPOINT = "https://bmcfe6z38foz.compat.objectstorage.ap-mumbai-1.oraclecloud.com"
    REGION = "ap-mumbai-1"
    
    # Path: s3a://lakehouse-prod/bronze/ecommerce/
    # Bucket: lakehouse-prod
    # Prefix: bronze/ecommerce/
    
    print(f"Connecting to S3 Endpoint: {ENDPOINT}")
    
    s3 = boto3.client('s3',
                      aws_access_key_id=ACCESS_KEY,
                      aws_secret_access_key=SECRET_KEY,
                      endpoint_url=ENDPOINT,
                      region_name=REGION,
                      config=Config(signature_version='s3v4'))
    
    bucket = "lakehouse-prod"
    prefix = "bronze/ecommerce/"
    
    print(f"Listing objects in bucket '{bucket}' with prefix '{prefix}'...")
    
    try:
        response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix, MaxKeys=20)
        
        if 'Contents' in response:
            print(f"Found {response['KeyCount']} files (showing first 20):")
            for obj in response['Contents']:
                print(f" - {obj['Key']} ({obj['Size']} bytes)")
        else:
            print("No objects found or bucket is empty.")
            
    except Exception as e:
        print(f"Error listing objects: {e}")

if __name__ == "__main__":
    list_s3_files_boto3()
