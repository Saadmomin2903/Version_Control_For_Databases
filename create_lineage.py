
import requests
import json
import os

OM_URL = "http://140.238.224.207:8585/api/v1"
JWT_TOKEN = "eyJraWQiOiJHYjM4OWEtOWY3Ni1nZGpzLWE5MmotMDI0MmJrOTQzNTYiLCJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJvcGVuLW1ldGFkYXRhLm9yZyIsInN1YiI6ImluZ2VzdGlvbi1ib3QiLCJlbWFpbCI6ImluZ2VzdGlvbi1ib3RAb3Blbm1ldGFkYXRhLm9yZyIsImlzQm90Ijp0cnVlLCJ0b2tlblR5cGUiOiJCT1QiLCJpYXQiOjE3Njk2MjA1MzksImV4cCI6bnVsbH0.idnPdxxfUUts0WWWAYvClIRKx5Z6sDifV8qMOYANQWqUO9HEFuOuiHhnbsiAUZepnAjnvvgyFmOlyqLTNDExO2XDBODJiKIcZg0sRWSLpGAxrtVLLh-dkP-xEalvYslW78Mvf7SkkXwrFSOn8cf05INxSbgNvukqB5po-1mL_0YVI9rS0TgJ-MwdaPS-kl55LZ3UnodAE9g4klki5ISuFe8eEdhaLBM5mP3hvBSgvjKEytMfVATdDWFJmWCOnN3bqemf19d23BPvoIWlBgVNluPaT1r3cTYxf2-2ini0fg0cRx43rdFm11qGfcfDvLVHIK1x1jgs_LFExIhGIcbhHQ"

headers = {
    "Authorization": f"Bearer {JWT_TOKEN}",
    "Content-Type": "application/json"
}

def get_table_id(fqn):
    url = f"{OM_URL}/tables/name/{fqn}"
    resp = requests.get(url, headers=headers)
    if resp.status_code == 200:
        return resp.json()["id"]
    return None

def create_bronze_table():
    # We need to find the service, database, and schema IDs first
    # For now, let's assume we can create it by providing the service and namespace info
    # Better: create it via the 'tables' API
    # Service: trino_service
    # Database: iceberg
    # Schema: ecommerce
    
    # Let's get the schema ID
    schema_fqn = "trino_service.iceberg.ecommerce"
    url = f"{OM_URL}/databaseSchemas/name/{schema_fqn}"
    resp = requests.get(url, headers=headers)
    if resp.status_code != 200:
        print(f"Failed to find schema: {resp.text}")
        return None
    schema_id = resp.json()["id"]
    
    table_data = {
        "name": "orders_bronze",
        "displayName": "orders_bronze",
        "databaseSchema": schema_fqn,
        "tableType": "Regular",
        "columns": [
            {"name": "event_time", "dataType": "TIMESTAMP", "displayName": "event_time"},
            {"name": "event_type", "dataType": "STRING", "displayName": "event_type"},
            {"name": "product_id", "dataType": "INT", "displayName": "product_id"},
            {"name": "category_id", "dataType": "BIGINT", "displayName": "category_id"},
            {"name": "category_code", "dataType": "STRING", "displayName": "category_code"},
            {"name": "brand", "dataType": "STRING", "displayName": "brand"},
            {"name": "price", "dataType": "DOUBLE", "displayName": "price"},
            {"name": "user_id", "dataType": "INT", "displayName": "user_id"},
            {"name": "user_session", "dataType": "STRING", "displayName": "user_session"}
        ]
    }
    url = f"{OM_URL}/tables"
    resp = requests.post(url, headers=headers, json=table_data)
    if resp.status_code in [200, 201]:
        print("Bronze table created/verified.")
        return resp.json()["id"]
    else:
        print(f"Failed to create bronze table: {resp.text}")
        return None

def add_lineage(from_id, to_id):
    url = f"{OM_URL}/lineage"
    lineage_data = {
        "edge": {
            "fromEntity": {"id": from_id, "type": "table"},
            "toEntity": {"id": to_id, "type": "table"}
        }
    }
    resp = requests.put(url, headers=headers, json=lineage_data)
    if resp.status_code in [200, 201]:
        print("Lineage added successfully.")
    else:
        print(f"Failed to add lineage: {resp.text}")

if __name__ == "__main__":
    silver_id = get_table_id("trino_service.iceberg.ecommerce.orders_silver")
    if not silver_id:
        print("Could not find silver table.")
    else:
        bronze_id = create_bronze_table()
        if bronze_id:
            add_lineage(bronze_id, silver_id)
