"""Trigger reprocess of document 1 via API from inside the container."""
import httpx
import sys
sys.path.insert(0, "/app")

BASE = "http://localhost:8000"

# Login
r = httpx.post(f"{BASE}/auth/login", data={"username": "admin@andreja.com", "password": "admin123"})
print(f"Login: {r.status_code}")
if r.status_code != 200:
    print(r.text)
    sys.exit(1)

token = r.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# Trigger reprocess
r = httpx.post(f"{BASE}/admin/documents/1/reprocess", headers=headers)
print(f"Reprocess: {r.status_code}")
print(r.json())
