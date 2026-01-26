import requests
import os
import json

NESSIE_URL = os.getenv("NESSIE_URI", "http://172.18.0.2:19120/api/v1")
BRANCH = "bronze"  # We'll clean bronze first
TABLE_KEY = ["ecommerce", "orders_bronze"]

def get_hash(branch_name):
    url = f"{NESSIE_URL}/trees/tree/{branch_name}"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()['hash']
        print(f"Failed to get hash for {branch_name}: {response.status_code}")
        return None
    except Exception as e:
        print(f"Error fetching hash: {e}")
        return None

def force_delete_table(branch_name):
    current_hash = get_hash(branch_name)
    if not current_hash:
        return

    print(f"Attempting to force delete key {TABLE_KEY} from {branch_name} at {current_hash}...")
    
    url = f"{NESSIE_URL}/trees/branch/{branch_name}/commit?expectedHash={current_hash}"
    
    payload = {
        "branch": branch_name,
        "hash": current_hash,
        "commitMeta": {
            "message": "Force delete corrupted table pointer",
            "authors": ["Antigravity Agent"]
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
    
    response = requests.post(url, json=payload)
    if response.status_code == 200: # Nessie commit returns 200 OK + metadata
        print(f"✅ Successfully deleted {TABLE_KEY} from {branch_name}.")
    elif response.status_code == 409: # Conflict - maybe key doesn't exist?
        err = response.json()
        if "keys do not exist" in str(err) or "Key does not exist" in response.text:
             print(f"ℹ️ Key {TABLE_KEY} does not exist in {branch_name}. Nothing to delete.")
        else:
             print(f"❌ Conflict error: {response.text}")
    else:
        print(f"❌ Failed to delete. Status: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    # Check if main is also polluted? Optional, but safer to just clean bronze for now
    force_delete_table(BRANCH)
