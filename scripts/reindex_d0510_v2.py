"""
URGENT: Re-insert D0510.pdf chunks (old ones were deleted).
Uses correct column name: gemini_text
"""
import paramiko
import base64

VPS_HOST = "72.61.217.143"
VPS_USER = "root"
VPS_PASS = "Proelast1608@"
VPS_KEY_TYPE = "ssh-ed25519"
VPS_KEY_DATA = "AAAAC3NzaC1lZDI1NTE5AAAAIO3C7DkqvmcKI72+gYlrUxOyi5IK6qQCGTvYckDC5WiH"

REINDEX_SCRIPT = r'''
import sys, os
sys.path.insert(0, "/app")
os.environ.setdefault("DATABASE_URL", "sqlite:////app/data/andreja.db")

from qdrant_client.models import Filter, FieldCondition, MatchValue, PointStruct
from ingestion.embedder import (
    get_qdrant_client, _build_contextual_chunks,
    get_embeddings_batch, ensure_collection
)
import uuid

DOC_ID = 17
BRAND_SLUG = "otis"
COLLECTION = "brand_otis"

client = get_qdrant_client()

# Check current state
print("Checking current D0510 chunks in Qdrant...")
current = client.scroll(
    collection_name=COLLECTION,
    scroll_filter=Filter(
        must=[FieldCondition(key="doc_id", match=MatchValue(value=DOC_ID))]
    ),
    limit=100,
    with_payload=True,
    with_vectors=False,
)
print(f"  Current chunks: {len(current[0])}")

# Get text from DB (correct column: gemini_text)
print("\nGetting D0510 text from database...")
from sqlalchemy import create_engine, text
engine = create_engine(os.environ["DATABASE_URL"])
with engine.connect() as conn:
    rows = list(conn.execute(text(
        "SELECT page_number, gemini_text FROM pages WHERE document_id = :doc_id ORDER BY page_number"
    ), {"doc_id": DOC_ID}))

print(f"  Found {len(rows)} pages")
for row in rows:
    page_text = row[1] or ""
    print(f"  Page {row[0]}: {len(page_text)} chars")
    print(f"  Preview: {page_text[:200]}...")

# Build chunks with improved logic (<=2000 chars = single chunk)
print("\nBuilding chunks...")
for row in rows:
    page_num = row[0]
    page_text = row[1] or ""
    
    chunks = _build_contextual_chunks(page_text)
    if not chunks:
        chunks = [page_text]
    
    print(f"  Page {page_num}: {len(chunks)} chunk(s)")
    for i, c in enumerate(chunks):
        print(f"    Chunk {i}: {len(c)} chars")
    
    # Embed
    print("  Embedding...")
    embeddings = get_embeddings_batch(chunks)
    
    points = []
    for index, (chunk_text, embedding) in enumerate(zip(chunks, embeddings)):
        point_id = str(uuid.uuid4())
        points.append(PointStruct(
            id=point_id,
            vector=embedding,
            payload={
                "brand_slug": BRAND_SLUG,
                "doc_id": DOC_ID,
                "doc_filename": "D0510.pdf",
                "page_number": page_num,
                "text": chunk_text,
                "chunk_index": index,
                "chunk_total": len(chunks),
            },
        ))
    
    client.upsert(collection_name=COLLECTION, points=points)
    print(f"  Upserted {len(points)} chunks")

# Verify
print("\nVerification...")
new_points = client.scroll(
    collection_name=COLLECTION,
    scroll_filter=Filter(
        must=[FieldCondition(key="doc_id", match=MatchValue(value=DOC_ID))]
    ),
    limit=100,
    with_payload=True,
    with_vectors=False,
)
print(f"  D0510 now has {len(new_points[0])} chunk(s) in Qdrant")
for p in new_points[0]:
    t = (p.payload or {}).get("text", "")
    print(f"    {len(t)} chars: {t[:100]}...")

# Test search
print("\nSearch test...")
from ingestion.embedder import search_brand
query = "led vermelho emergencia caixa inspecao Beneton nao acende"
results = search_brand("otis", query, top_k=15)
d0510_found = False
for i, r in enumerate(results):
    is_d0510 = "D0510" in r.get("source", "")
    if is_d0510:
        d0510_found = True
    marker = " *** D0510 ***" if is_d0510 else ""
    print(f"  [{i+1}] score={r['score']:.4f} source={r['source']}{marker}")

if d0510_found:
    print("\n SUCCESS: D0510.pdf found in search results!")
else:
    print("\n FAIL: D0510.pdf still not found")
'''

def run():
    host_key = paramiko.Ed25519Key(data=base64.b64decode(VPS_KEY_DATA))
    client = paramiko.SSHClient()
    client.get_host_keys().add(VPS_HOST, VPS_KEY_TYPE, host_key)
    client.connect(VPS_HOST, username=VPS_USER, password=VPS_PASS)
    print("Connected")

    # Upload script
    sftp = client.open_sftp()
    with sftp.file("/root/andreja2/reindex_d0510_v2.py", "w") as f:
        f.write(REINDEX_SCRIPT)
    sftp.close()

    # Copy into container and run
    cmds = [
        "docker cp /root/andreja2/reindex_d0510_v2.py andreja_backend:/app/reindex_d0510_v2.py",
        "docker exec andreja_backend python /app/reindex_d0510_v2.py 2>&1",
    ]
    for cmd in cmds:
        stdin, stdout, stderr = client.exec_command(cmd, timeout=120)
        exit_code = stdout.channel.recv_exit_status()
        output = stdout.read().decode()
        if output.strip():
            print(output)
        err = stderr.read().decode()
        if err.strip() and exit_code != 0:
            print(f"ERR: {err[-300:]}")

    client.close()

if __name__ == "__main__":
    run()
