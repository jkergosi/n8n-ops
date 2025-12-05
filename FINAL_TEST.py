#!/usr/bin/env python
"""Final comprehensive test for workflow tag saving"""
import requests
import time

BASE = "http://localhost:8000/api/v1"
ENV = "dev"

print("="*80)
print("FINAL COMPREHENSIVE TEST - Workflow Tag Saving")
print("="*80)

# Step 1: Get workflows
print("\n[1] Fetching workflows...")
r = requests.get(f"{BASE}/workflows", params={"environment": ENV}, timeout=10)
print(f"    Status: {r.status_code}")
workflows = r.json()
workflow = workflows[0]
wid = workflow['id']
print(f"    Testing with: {workflow['name']} (ID: {wid})")
print(f"    Current tags: {workflow.get('tags', [])}")

# Step 2: Get available tags
all_tags = set()
for w in workflows:
    all_tags.update(w.get('tags', []))
test_tags = sorted(list(all_tags))[:2]
print(f"\n[2] Using test tags: {test_tags}")

# Step 3: Update tags
print(f"\n[3] Updating workflow tags...")
r = requests.put(
    f"{BASE}/workflows/{wid}/tags",
    params={"environment": ENV},
    json=test_tags,
    timeout=10
)
print(f"    Status: {r.status_code}")
if r.status_code == 200:
    print("    SUCCESS: Tags updated in N8N")
else:
    print(f"    ERROR: {r.text}")
    exit(1)

# Step 4: Verify (without force refresh - check cache)
print(f"\n[4] Verifying tags (from cache)...")
time.sleep(1)
r = requests.get(f"{BASE}/workflows", params={"environment": ENV}, timeout=10)
workflows = r.json()
workflow = next((w for w in workflows if w['id'] == wid), None)
cached_tags = workflow.get('tags', [])
print(f"    Cached tags: {cached_tags}")

# Step 5: Verify (with force refresh - check N8N)
print(f"\n[5] Verifying tags (from N8N - force refresh)...")
r = requests.get(f"{BASE}/workflows", params={"environment": ENV, "force_refresh": "true"}, timeout=15)
workflows = r.json()
workflow = next((w for w in workflows if w['id'] == wid), None)
n8n_tags = workflow.get('tags', [])
print(f"    N8N tags: {n8n_tags}")

# Results
print("\n" + "="*80)
if set(cached_tags) == set(test_tags):
    print("PASS: Tags persisted in cache!")
else:
    print(f"FAIL: Cache tags don't match. Expected {test_tags}, got {cached_tags}")

if set(n8n_tags) == set(test_tags):
    print("PASS: Tags persisted in N8N!")
else:
    print(f"FAIL: N8N tags don't match. Expected {test_tags}, got {n8n_tags}")

print("="*80)
