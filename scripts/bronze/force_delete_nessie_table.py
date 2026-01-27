#!/usr/bin/env python3
"""
Force Delete Table from Nessie via API
Used when Spark/Iceberg cannot drop a table due to corrupted metadata/IO issues.
"""

import json
import urllib.request
import urllib.error
import os

NESSIE_URI = "http://172.18.0.2:19120/api/v1"
BRANCH = "main"
TABLE_KEY = ["ecommerce", "orders_bronze"]

def get_branch_head():
    url = f"{NESSIE_URI}/trees/tree/{BRANCH}"
    try:
        with urllib.request.urlopen(url) as response:
            data = json.loads(response.read().decode())
            return data['hash']
    except Exception as e:
        print(f"Error fetching branch {BRANCH}: {e}")
        return None

def main():
    print(f"Attempting to force delete table {' '.join(TABLE_KEY)} from {BRANCH}...")
    
    # 1. Get current hash
    current_hash = get_branch_head()
    if not current_hash:
        print("Could not get current branch hash. Exiting.")
        return
    
    print(f"Current hash: {current_hash}")
    
    # 2. Construct Commit Payload
    # Remove hash from body, pass it in query param
    payload = {
        "branch": {
            "name": BRANCH
        },
        "commitMeta": {
            "message": "Force delete corrupted orders_bronze table",
            "author": "admin",
            "properties": {}
        },
        "operations": [
            {
                "type": "DELETE",
                "key": {
                    "elements": TABLE_KEY
                }
            }
        ]
    }
    
    commit_url = f"{NESSIE_URI}/trees/branch/{BRANCH}/commit?expectedHash={current_hash}"
    req = urllib.request.Request(commit_url, method="POST")
    req.add_header('Content-Type', 'application/json')
    req.add_header('Accept', 'application/json')
    
    data = json.dumps(payload).encode()
    
    # 3. Execute Commit
    try:
        with urllib.request.urlopen(req, data=data) as response:
            result = json.loads(response.read().decode())
            print("✅ Successfully deleted table reference!")
            print(f"New Hash: {result['hash']}")
    except urllib.error.HTTPError as e:
        if e.code == 409: # Conflict
            print("❌ Conflict (409). Branch hash might have changed. Please retry.")
            print(e.read().decode())
        elif e.code == 404:
            print("⚠️ Table or branch not found. It might be already deleted.")
        else:
            print(f"❌ Error {e.code}: {e.reason}")
            print(e.read().decode())
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    main()
