"""Reset all docs and trigger reprocess with gemini-2.5-flash."""
import sqlite3, time, requests
from qdrant_client import QdrantClient

DB = "/app/data/andreja.db"

# 1. Reset DB
c = sqlite3.connect(DB)
cur = c.cursor()
cur.execute("SELECT id, brand_id FROM documents")
docs = cur.fetchall()
print(f"Docs encontrados: {docs}")

for doc_id, brand_id in docs:
    cur.execute("DELETE FROM pages WHERE document_id=?", (doc_id,))
    cur.execute(
        "UPDATE documents SET status='pending', processed_pages=0, error_message=NULL WHERE id=?",
        (doc_id,),
    )
    print(f"  Doc {doc_id}: reset para pending")
c.commit()
c.close()

# 2. Limpa Qdrant
qc = QdrantClient(host="qdrant", port=6333)
for col in qc.get_collections().collections:
    qc.delete_collection(col.name)
    print(f"  Qdrant: deletou collection {col.name}")

# 3. Trigger reprocess via API
time.sleep(3)
s = requests.Session()
r = s.post(
    "http://localhost:8000/auth/login",
    data={"username": "admin@andreja.com", "password": "admin123"},
)
token = r.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

for doc_id, _ in docs:
    r = s.post(f"http://localhost:8000/admin/documents/{doc_id}/reprocess", headers=headers)
    print(f"  Doc {doc_id}: reprocess -> {r.status_code} {r.text[:120]}")

print("\nDONE - reprocessamento com gemini-2.5-flash disparado!")
