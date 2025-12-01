import requests
import time
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from config.iceberg_config import NESSIE_URI, BRONZE_BRANCH, SILVER_BRANCH, GOLD_BRANCH

def wait_for_nessie(max_retries=30, delay=2):
    """Wait for Nessie to be ready"""
    print("Waiting for Nessie to be ready...")
    for i in range(max_retries):
        try:
            response = requests.get(f"{NESSIE_URI}/config", timeout=5)
            if response.status_code == 200:
                print("✓ Nessie is ready")
                return True
        except requests.exceptions.RequestException:
            pass
        print(f"  Attempt {i+1}/{max_retries}...")
        time.sleep(delay)
    
    print("✗ Nessie failed to start")
    return False

def get_default_branch():
    """Get the default branch (main) information"""
    try:
        # Use the correct API endpoint to get all references
        response = requests.get(f"{NESSIE_URI}/trees", timeout=10)
        response.raise_for_status()
        
        references = response.json().get("references", [])
        
        # Find the main branch
        for ref in references:
            if ref.get("name") == "main":
                return ref.get("name"), ref.get("hash")
        
        print("✗ Could not find 'main' branch")
        return None, None
        
    except Exception as e:
        print(f"✗ Failed to get default branch: {e}")
        return None, None

def create_branch(branch_name, source_name="main", source_hash=None):
    """Create a Nessie branch"""
    
    # Create the new branch using Nessie API v2
    # The API expects the Reference object fields at the top level
    # (including the polymorphic 'type' property). Provide optional
    # sourceRefName/sourceHash when branching from an existing ref.
    # Nessie expects a CreateReference payload wrapper named `createReference`
    payload = {
    "name": branch_name,
    "type": "BRANCH",
    "sourceRefName": source_name,
    "sourceHash": source_hash
    }   

    # Add sourceRefName/sourceHash for branching from main
    if source_name:
        payload["sourceRefName"] = source_name
    if source_hash:
        payload["sourceHash"] = source_hash
    
    try:
        # Correct API v2 endpoint for creating references
        response = requests.post(
            f"{NESSIE_URI}/trees",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        if response.status_code in [200, 201]:
            print(f"✓ Created branch '{branch_name}' from '{source_name}'")
            return True
        elif response.status_code == 409:
            print(f"✓ Branch '{branch_name}' already exists")
            return True
        else:
            print(f"✗ Failed to create branch '{branch_name}': {response.status_code}")
            print(f"  Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"✗ Error creating branch '{branch_name}': {e}")
        return False

def list_branches():
    """List all Nessie branches"""
    try:
        response = requests.get(f"{NESSIE_URI}/trees", timeout=10)
        response.raise_for_status()
        
        references = response.json().get("references", [])
        print("\n" + "=" * 60)
        print("AVAILABLE BRANCHES")
        print("=" * 60)
        
        for ref in references:
            ref_type = ref.get("type", "UNKNOWN")
            ref_name = ref.get("name", "unknown")
            ref_hash = ref.get("hash", "N/A")[:8]  # Show first 8 chars of hash
            print(f"  - {ref_name} ({ref_type}) [{ref_hash}]")
        
        print("=" * 60)
        
    except Exception as e:
        print(f"✗ Failed to list branches: {e}")

def main():
    print("=" * 60)
    print("SETTING UP NESSIE")
    print("=" * 60)
    
    # Wait for Nessie to be ready
    if not wait_for_nessie():
        print("\nTroubleshooting:")
        print("  1. Check if Nessie container is running: docker ps | grep nessie")
        print("  2. Check Nessie logs: docker logs <nessie-container-id>")
        print("  3. Verify NESSIE_URI in .env file")
        return False
    
    # Get the main branch info
    print("\nGetting main branch information...")
    main_name, main_hash = get_default_branch()
    
    if not main_hash:
        print("✗ Cannot proceed without main branch")
        return False
    
    print(f"✓ Found main branch with hash: {main_hash[:8]}")
    
    # Create branches
    print("\nCreating branches...")
    branches = [BRONZE_BRANCH, SILVER_BRANCH, GOLD_BRANCH]
    success = True
    
    for branch in branches:
        if not create_branch(branch, source_name=main_name, source_hash=main_hash):
            success = False
    
    # List all branches
    list_branches()
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)