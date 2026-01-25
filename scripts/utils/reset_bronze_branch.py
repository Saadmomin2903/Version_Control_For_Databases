import requests
import sys
import os
import time

# Use hostname 'nessie' by default for container-to-container communication
# But allow override if running from host or different setup
NESSIE_URL = os.getenv("NESSIE_URI", "http://nessie:19120/api/v1")
BRANCH_TO_RESET = "bronze"
SOURCE_REF = "main"

def get_hash(branch_name):
    url = f"{NESSIE_URL}/trees/tree/{branch_name}"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()['hash']
        return None
    except Exception as e:
        print(f"Error fetching hash for {branch_name}: {e}")
        return None

def get_main_hash():
    return get_hash(SOURCE_REF)

def delete_branch(branch_name, current_hash):
    url = f"{NESSIE_URL}/trees/branch/{branch_name}?expectedHash={current_hash}"
    print(f"Deleting branch {branch_name}...")
    response = requests.delete(url)
    if response.status_code == 204:
        print(f"✅ Branch {branch_name} deleted successfully.")
        return True
    else:
        print(f"❌ Failed to delete branch {branch_name}. Status: {response.status_code}")
        print(response.text)
        return False

def create_branch(branch_name, source_hash):
    url = f"{NESSIE_URL}/trees/tree"
    payload = {
        "type": "BRANCH",
        "name": branch_name,
        "hash": source_hash
    }
    print(f"Creating branch {branch_name} from {SOURCE_REF} ({source_hash})...")
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        print(f"✅ Branch {branch_name} created successfully.")
        return True
    else:
        print(f"❌ Failed to create branch {branch_name}. Status: {response.status_code}")
        print(response.text)
        return False

def reset_bronze():
    print(f"🔌 Connecting to Nessie at {NESSIE_URL}")
    
    # 1. Get current hash of bronze to delete it
    bronze_hash = get_hash(BRANCH_TO_RESET)
    
    if bronze_hash:
        print(f"Found {BRANCH_TO_RESET} at hash {bronze_hash}")
        if not delete_branch(BRANCH_TO_RESET, bronze_hash):
            print("Aborting reset due to deletion failure.")
            return
    else:
        print(f"Branch {BRANCH_TO_RESET} does not exist. Proceeding to creation.")

    # 2. Get main hash to base new bronze on
    main_hash = get_main_hash()
    if not main_hash:
        print(f"❌ Could not find {SOURCE_REF} branch. Is Nessie initialized?")
        return

    # 3. Create fresh bronze branch
    create_branch(BRANCH_TO_RESET, main_hash)

if __name__ == "__main__":
    reset_bronze()
