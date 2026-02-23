#!/usr/bin/env python3
"""
Reset documents to pending and trigger reprocess via API.
Deletes old pages and vectors, then triggers reprocessing.
"""
import sqlite3
import requests
import sys

DB = "/app/data/andreja.db"
API_BASE = "http://localhost:8000"

# 1. Login
print("=== Logging in ===")
resp = requests.post(f"{API_BASE}/auth/login", data={
    "username": "admin@andreja.com",
    "password": "admin123",
})
if resp.status_code != 200:
    print(f"Login failed: {resp.status_code} {resp.text}")
    sys.exit(1)
token = resp.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}
print(f"Token: {token[:30]}...")

# 2. Get documents
print("\n=== Current documents ===")
conn = sqlite3.connect(DB)
cur = conn.cursor()
cur.execute("SELECT id, status, total_pages, processed_pages, filename FROM documents ORDER BY id")
docs = cur.fetchall()
for d in docs:
    print(f"  Doc {d[0]}: status={d[1]}, pages={d[3]}/{d[2]}, file={d[4]}")

# 3. Reset all documents to pending  
print("\n=== Resetting documents to pending ===")
cur.execute("UPDATE documents SET status='pending', processed_pages=0, error_message=NULL")

# 4. Delete all pages (will be recreated during reprocessing)
cur.execute("DELETE FROM pages")
print(f"  Deleted all pages from DB")

conn.commit()
conn.close()

# 5. Trigger reprocessing for each doc
for d in docs:
    doc_id = d[0]
    print(f"\n=== Triggering reprocess for doc {doc_id} ===")
    resp = requests.post(
        f"{API_BASE}/admin/documents/{doc_id}/reprocess",
        headers=headers,
    )
    print(f"  Response: {resp.status_code} {resp.text[:200]}")

print("\n=== DONE - Reprocessing triggered ===")
print("Monitor with: docker logs -f andreja_backend")
