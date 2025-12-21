#!/usr/bin/env python3
"""
Rollback Production to Previous State

Use this if a production release has issues.
Allows selecting from recent commits on main branch.
"""

import requests
import json
import sys

NESSIE_URL = "http://localhost:19120/api/v1"

def list_commits(branch_name, limit=10):
    """Get recent commits on a branch"""
    response = requests.get(
        f"{NESSIE_URL}/trees/tree/{branch_name}/log",
        params={"maxRecords": limit}
    )
    if response.status_code == 200:
        return response.json().get('logEntries', [])
    return []

def rollback():
    """Rollback main branch to previous commit"""
    
    print("=" * 70)
    print("ROLLBACK PRODUCTION")
    print("=" * 70)
    print()
    
    # Get recent commits
    print("📋 Recent commits on MAIN branch:")
    commits = list_commits("main")
    
    if not commits:
        print("❌ No commits found")
        return
    
    for i, entry in enumerate(commits[:5]):
        commit_hash = entry['commitMeta']['hash']
        message = entry['commitMeta'].get('message', 'No message')
        timestamp = entry['commitMeta'].get('commitTime', 'Unknown time')
        print(f"\n{i}. {commit_hash[:8]}... - {message}")
        print(f"   Time: {timestamp}")
    
    print("\nCurrent (HEAD): 0")
    print("Previous: 1")
    print()
    
    choice = input("Rollback to which commit? (0-4, or 'cancel'): ")
    
    if choice.lower() == 'cancel':
        print("❌ Rollback cancelled")
        return
    
    try:
        idx = int(choice)
        if idx < 0 or idx >= len(commits):
            print("❌ Invalid selection")
            return
        
        target_hash = commits[idx]['commitMeta']['hash']
        
        print(f"\n⚠️  Rolling back to: {target_hash[:8]}...")
        confirm = input("Continue? (yes/no): ")
        
        if confirm.lower() != "yes":
            print("❌ Rollback cancelled")
            return
        
        # Assign main branch to target commit
        response = requests.put(
            f"{NESSIE_URL}/trees/branch/main",
            headers={"Content-Type": "application/json"},
            json={
                "hash": target_hash,
                "message": f"Rollback to {target_hash[:8]}"
            }
        )
        
        if response.status_code in [200, 204]:
            print("✅ ROLLBACK SUCCESSFUL!")
            print(f"   Main branch now at: {target_hash[:8]}")
        else:
            print(f"❌ Rollback failed: {response.status_code}")
            print(f"   Response: {response.text}")
            
    except ValueError:
        print("❌ Invalid input")

if __name__ == "__main__":
    rollback()
