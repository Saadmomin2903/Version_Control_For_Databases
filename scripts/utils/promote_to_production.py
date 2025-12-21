#!/usr/bin/env python3
"""
Promote Gold Branch to Production (Main)

This script merges the gold branch into main, making aggregations
available to production BI tools.
"""

import requests
import json
import sys

NESSIE_URL = "http://localhost:19120/api/v1"

def get_branch_hash(branch_name):
    """Get current hash of a branch"""
    response = requests.get(f"{NESSIE_URL}/trees/tree/{branch_name}")
    if response.status_code == 200:
        return response.json()['hash']
    return None

def merge_to_main():
    """Merge gold branch into main"""
    
    print("=" * 70)
    print("PROMOTE GOLD BRANCH TO PRODUCTION")
    print("=" * 70)
    print()
    
    # Get current hashes
    print("📋 Getting branch information...")
    main_hash = get_branch_hash("main")
    gold_hash = get_branch_hash("gold")
    
    if not main_hash or not gold_hash:
        print("❌ Could not get branch hashes")
        sys.exit(1)
    
    print(f"  Main branch hash: {main_hash[:8]}...")
    print(f"  Gold branch hash: {gold_hash[:8]}...")
    print()
    
    # Confirm with user
    print("⚠️  This will merge GOLD branch into MAIN (production)")
    print("   Production users will see the new aggregations.")
    print()
    
    confirm = input("Continue? (yes/no): ")
    if confirm.lower() != "yes":
        print("❌ Merge cancelled")
        sys.exit(0)
    
    # Promote by assigning main to point to gold's state
    print("\n🔄 Promoting gold → main (assigning branch pointer)...")
    
    # Assign main branch to point to gold's current hash
    assign_response = requests.put(
        f"{NESSIE_URL}/trees/branch/main",
        params={"expectedHash": main_hash},  # Expected current state
        headers={"Content-Type": "application/json"},
        json={
            "type": "BRANCH",
            "name": "main",
            "hash": gold_hash  # New state (point to gold)
        }
    )
    
    if assign_response.status_code not in [200, 204]:
        print(f"❌ Promotion failed: {assign_response.status_code}")
        print(f"   Response: {assign_response.text}")
        sys.exit(1)
    
    print("✅ PROMOTION SUCCESSFUL!")
    print("\n📊 Main branch now points to gold's data")
    print("   BI tools can now query the new aggregations")
    
    print("=" * 70)

if __name__ == "__main__":
    merge_to_main()
