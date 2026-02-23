"""
Re-index D0510.pdf with improved chunking.
1. Deploy updated embedder.py (with 2000 char shortcut)
2. Delete old D0510 chunks from Qdrant
3. Re-embed with single chunk
"""
import paramiko
import base64
import os

VPS_HOST = "72.61.217.143"
VPS_USER = "root"
VPS_PASS = "Proelast1608@"
VPS_KEY_TYPE = "ssh-ed25519"
VPS_KEY_DATA = "AAAAC3NzaC1lZDI1NTE5AAAAIO3C7DkqvmcKI72+gYlrUxOyi5IK6qQCGTvYckDC5WiH"
REMOTE_BASE = "/root/andreja2/backend"

REINDEX_SCRIPT = r'''
import sys, os
sys.path.insert(0, "/app")
os.environ.setdefault("DATABASE_URL", "sqlite:////app/data/andreja.db")

from qdrant_client.models import Filter, FieldCondition, MatchValue
from ingestion.embedder import (
    get_qdrant_client, _build_contextual_chunks,
    get_embeddings_batch, ensure_collection, VECTOR_SIZE
)
from qdrant_client.models import PointStruct
import uuid

DOC_ID = 17  # D0510.pdf
BRAND_SLUG = "otis"
COLLECTION = "brand_otis"

client = get_qdrant_client()

# 1. Find and delete old D0510 chunks
print("Step 1: Finding old D0510 chunks...")
old_points = client.scroll(
    collection_name=COLLECTION,
    scroll_filter=Filter(
        must=[FieldCondition(key="doc_id", match=MatchValue(value=DOC_ID))]
    ),
    limit=100,
    with_payload=True,
    with_vectors=False,
)
old_ids = [p.id for p in old_points[0]]
print(f"  Found {len(old_ids)} old chunks")

if old_ids:
    # Show old chunks
    for p in old_points[0]:
        text = (p.payload or {}).get("text", "")
        print(f"  Old chunk: {text[:80]}...")
    
    client.delete(
        collection_name=COLLECTION,
        points_selector=old_ids,
    )
    print(f"  Deleted {len(old_ids)} old chunks")

# 2. Get the D0510 text from database
print("\nStep 2: Getting D0510 text from database...")
from sqlalchemy import create_engine, text
engine = create_engine(os.environ["DATABASE_URL"])
with engine.connect() as conn:
    rows = list(conn.execute(text(
        "SELECT page_number, extracted_text FROM pages WHERE document_id = :doc_id ORDER BY page_number"
    ), {"doc_id": DOC_ID}))

print(f"  Found {len(rows)} pages")

# 3. Re-chunk and re-embed
print("\nStep 3: Re-chunking and re-embedding...")
for row in rows:
    page_num = row[0]
    page_text = row[1] or ""
    print(f"\n  Page {page_num}: {len(page_text)} chars")
    
    chunks = _build_contextual_chunks(page_text)
    if not chunks:
        chunks = [page_text]
    
    print(f"  New chunks: {len(chunks)}")
    for i, c in enumerate(chunks):
        print(f"    Chunk {i}: {len(c)} chars - {c[:100]}...")
    
    # Embed
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
    print(f"  Upserted {len(points)} new chunks")

# 4. Verify
print("\nStep 4: Verification...")
new_points = client.scroll(
    collection_name=COLLECTION,
    scroll_filter=Filter(
        must=[FieldCondition(key="doc_id", match=MatchValue(value=DOC_ID))]
    ),
    limit=100,
    with_payload=True,
    with_vectors=False,
)
print(f"  D0510 now has {len(new_points[0])} chunks in Qdrant")
for p in new_points[0]:
    text = (p.payload or {}).get("text", "")
    print(f"    Chunk: {len(text)} chars - {text[:100]}...")

# 5. Test search
print("\nStep 5: Test search...")
from ingestion.embedder import search_brand
query = "led vermelho emergência caixa inspeção Beneton não acende"
results = search_brand("otis", query, top_k=15)
d0510_found = False
for i, r in enumerate(results):
    is_d0510 = "D0510" in r.get("source", "")
    if is_d0510:
        d0510_found = True
        print(f"  [{i+1}] score={r['score']:.4f} source={r['source']} *** D0510 ***")
        print(f"       text: {r['text'][:150]}...")
    else:
        print(f"  [{i+1}] score={r['score']:.4f} source={r['source']}")

if d0510_found:
    print("\n✓ SUCCESS: D0510.pdf found in search results!")
else:
    print("\n✗ FAIL: D0510.pdf still not found")

print("\nDone!")
'''

def deploy_and_reindex():
    host_key = paramiko.Ed25519Key(data=base64.b64decode(VPS_KEY_DATA))
    client = paramiko.SSHClient()
    client.get_host_keys().add(VPS_HOST, VPS_KEY_TYPE, host_key)
    client.connect(VPS_HOST, username=VPS_USER, password=VPS_PASS)
    print("✓ SSH connected")

    # Upload updated embedder.py
    sftp = client.open_sftp()
    local_base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    local_path = os.path.join(local_base, "backend", "ingestion", "embedder.py")
    remote_path = f"{REMOTE_BASE}/ingestion/embedder.py"
    print(f"  Uploading embedder.py...")
    sftp.put(local_path, remote_path)

    # Upload reindex script
    with sftp.file("/root/andreja2/reindex_d0510.py", "w") as f:
        f.write(REINDEX_SCRIPT)
    sftp.close()
    print("✓ Files uploaded")

    # Rebuild backend
    print("  Rebuilding backend...")
    stdin, stdout, stderr = client.exec_command(
        "cd /root/andreja2 && docker compose up -d --build backend",
        timeout=180,
    )
    exit_code = stdout.channel.recv_exit_status()
    err = stderr.read().decode()
    if exit_code != 0:
        print(f"✗ Build failed: {err[-500:]}")
        client.close()
        return
    print("✓ Backend rebuilt")

    # Wait for container
    import time
    time.sleep(10)

    # Copy and run reindex script inside container
    print("  Running re-index script inside container...")
    cmds = [
        "docker cp /root/andreja2/reindex_d0510.py andreja_backend:/app/reindex_d0510.py",
        "docker exec andreja_backend python /app/reindex_d0510.py 2>&1",
    ]
    
    for cmd in cmds:
        stdin, stdout, stderr = client.exec_command(cmd, timeout=120)
        exit_code = stdout.channel.recv_exit_status()
        output = stdout.read().decode()
        if output.strip():
            print(output)
        errout = stderr.read().decode()
        if errout.strip() and exit_code != 0:
            print(f"STDERR: {errout[-500:]}")

    client.close()
    print("\n✓ All done!")

if __name__ == "__main__":
    deploy_and_reindex()
