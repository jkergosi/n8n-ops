import requests

print("Verifying tag persistence...")
resp = requests.get("http://localhost:8000/api/v1/workflows", params={"environment": "dev"}, timeout=10)
if resp.status_code == 200:
    workflows = resp.json()
    target = next((w for w in workflows if w['id'] == 'W7r7rNjF7Ol7ajlP'), None)
    if target:
        tags = target.get('tags', [])
        print(f"Workflow: {target['name']}")
        print(f"Tags: {tags}")
        if 'example' in tags and 'mcp' in tags:
            print("\n*** SUCCESS! Tags persisted correctly! ***")
        else:
            print(f"\nWARNING: Expected ['example', 'mcp'], got {tags}")
