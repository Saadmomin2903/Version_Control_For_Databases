#!/usr/bin/env python3
"""
Nessie Branch Creator
Creates bronze, silver, and gold branches in Nessie
"""
import requests
import json
import sys
import time

NESSIE_URL = "http://localhost:19120/api/v1"
BRANCHES = ["bronze", "silver", "gold"]

def wait_for_nessie(max_retries=30):
    """Wait for Nessie to be ready"""
    print("⏳ Waiting for Nessie to be ready...")
    for i in range(max_retries):
        try:
            response = requests.get(f"{NESSIE_URL}/config", timeout=2)
            if response.status_code == 200:
                print("✓ Nessie is ready\n")
                return True
        except:
            pass
        print(f"  Attempt {i+1}/{max_retries}...")
        time.sleep(2)
    return False

def get_branches():
    """Get all existing branches"""
    try:
        response = requests.get(f"{NESSIE_URL}/trees")
        if response.status_code == 200:
            data = response.json()
            return [ref["name"] for ref in data.get("references", [])]
        return []
    except Exception as e:
        print(f"Error getting branches: {e}")
        return []

def get_branch_hash(branch_name):
    """Get hash for a specific branch"""
    try:
        response = requests.get(f"{NESSIE_URL}/trees")
        if response.status_code == 200:
            data = response.json()
            for ref in data.get("references", []):
                if ref["name"] == branch_name:
                    return ref["hash"]
        return None
    except Exception as e:
        print(f"Error getting branch hash: {e}")
        return None

def create_branch_v1(branch_name, source_hash):
    """Create branch using v1 API - trying multiple endpoint formats"""
    
    # Try format 1: PUT with branch name in path
    try:
        response = requests.put(
            f"{NESSIE_URL}/trees/branch/{branch_name}",
            headers={"Content-Type": "application/json"},
            json={"hash": source_hash}
        )
        if response.status_code in [200, 204]:
            return True, "created"
    except:
        pass
    
    # Try format 2: POST to /tree endpoint
    try:
        response = requests.post(
            f"{NESSIE_URL}/trees/tree",
            headers={"Content-Type": "application/json"},
            json={
                "name": branch_name,
                "type": "BRANCH", 
                "hash": source_hash
            }
        )
        if response.status_code in [200, 204]:
            return True, "created"
    except:
        pass
    
    return False, "failed"

def main():
    print("🚀 Nessie Branch Creator\n")
    
    # Wait for Nessie
    if not wait_for_nessie():
        print("❌ Nessie is not ready")
        sys.exit(1)
    
    # Get main branch hash
    print("📋 Getting main branch information...")
    main_hash = get_branch_hash("main")
    if not main_hash:
        print("❌ Could not get main branch hash")
        sys.exit(1)
    
    print(f"✓ Main branch hash: {main_hash}\n")
    
    # Get existing branches
    existing_branches = get_branches()
    print("📋 Current branches:")
    for branch in existing_branches:
        print(f"  - {branch}")
    print()
    
    # Create new branches
    print("🌿 Creating branches...")
    success_count = 0
    
    for branch_name in BRANCHES:
        if branch_name in existing_branches:
            print(f"  ○ Branch '{branch_name}' already exists")
            success_count += 1
        else:
            success, msg = create_branch_v1(branch_name, main_hash)
            if success:
                print(f"  ✓ Created branch '{branch_name}'")
                success_count += 1
            else:
                print(f"  ✗ Failed to create branch '{branch_name}'")
    
    # Verify final state
    print()
    final_branches = get_branches()
    print("📋 Final branches:")
    for branch in final_branches:
        print(f"  - {branch}")
    
    print()
    if success_count == len(BRANCHES):
        print("✅ All branches ready!")
    else:
        print(f"⚠️  {success_count}/{len(BRANCHES)} branches ready")
        print("\n💡 Alternative: Use Java Nessie Client in your application")
        print("   Add dependency: org.projectnessie.nessie:nessie-client:0.70.0")

if __name__ == "__main__":
    main()