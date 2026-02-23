"""Trigger reprocess for doc 146 via API."""
import requests

BASE = "http://localhost:8000"

# Login
r = requests.post(f"{BASE}/auth/login", data={"username": "admin@andreja.com", "password": "admin123"})
token = r.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# Reprocess doc 146
r = requests.post(f"{BASE}/admin/documents/146/reprocess", headers=headers)
print(f"Reprocess 146: {r.status_code} - {r.json()}")
