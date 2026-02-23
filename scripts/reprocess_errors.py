"""Reprocess 3 documents with errors: 115, 116, 134"""
import requests
import sys
import time

BASE = "http://localhost:8000"
DOC_IDS = [115, 116, 134]

# Login
r = requests.post(f"{BASE}/auth/login", data={
    "username": "admin@andreja.com",
    "password": "admin123",
})
if r.status_code != 200:
    print(f"Login failed: {r.status_code}")
    sys.exit(1)

token = r.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}
print(f"Login OK")

# Trigger reprocess for each
for doc_id in DOC_IDS:
    r = requests.post(f"{BASE}/admin/documents/{doc_id}/reprocess", headers=headers)
    print(f"  Doc {doc_id}: {r.status_code} - {r.json()}")
    time.sleep(1)

print("\nReprocessamento disparado! Aguarde os PDFs serem processados.")
