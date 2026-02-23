"""
Find all small documents (pages with <=2000 chars) that have multiple chunks
in Qdrant and re-index them as single chunks.
"""
import paramiko
import base64

VPS_HOST = "72.61.217.143"
VPS_USER = "root"
VPS_PASS = "Proelast1608@"
VPS_KEY_TYPE = "ssh-ed25519"
VPS_KEY_DATA = "AAAAC3NzaC1lZDI1NTE5AAAAIO3C7DkqvmcKI72+gYlrUxOyi5IK6qQCGTvYckDC5WiH"

SCRIPT = r'''
import sys, os
sys.path.insert(0, "/app")
os.environ.setdefault("DATABASE_URL", "sqlite:////app/data/andreja.db")

from qdrant_client.models import Filter, FieldCondition, MatchValue, PointStruct
from ingestion.embedder import (
    get_qdrant_client, _build_contextual_chunks,
    get_embeddings_batch
)
from sqlalchemy import create_engine, text
import uuid

COLLECTION = "brand_otis"
BRAND_SLUG = "otis"
engine = create_engine(os.environ["DATABASE_URL"])
client = get_qdrant_client()

# Find all pages with text <= 2000 chars
with engine.connect() as conn:
    pages = list(conn.execute(text(
        "SELECT p.id, p.document_id, p.page_number, p.gemini_text, d.filename "
        "FROM pages p JOIN documents d ON p.document_id = d.id "
        "WHERE length(p.gemini_text) > 0 AND length(p.gemini_text) <= 2000 "
        "ORDER BY d.id, p.page_number"
    )))

print(f"Found {len(pages)} pages with text <= 2000 chars")

reindexed = 0
for page in pages:
    page_id, doc_id, page_num, page_text, filename = page
    
    # Count current chunks for this doc+page
    current = client.scroll(
        collection_name=COLLECTION,
        scroll_filter=Filter(
            must=[
                FieldCondition(key="doc_id", match=MatchValue(value=doc_id)),
                FieldCondition(key="page_number", match=MatchValue(value=page_num)),
            ]
        ),
        limit=100,
        with_payload=False,
        with_vectors=False,
    )
    chunk_count = len(current[0])
    
    if chunk_count <= 1:
        continue  # Already optimal
    
    print(f"\n{filename} page {page_num}: {len(page_text)} chars, {chunk_count} chunks -> needs re-index")
    
    # Delete old chunks
    old_ids = [p.id for p in current[0]]
    client.delete(collection_name=COLLECTION, points_selector=old_ids)
    
    # Build new chunks (should be single chunk for <=2000 chars)
    chunks = _build_contextual_chunks(page_text)
    if not chunks:
        chunks = [page_text]
    
    print(f"  New: {len(chunks)} chunk(s)")
    
    # Embed and upsert
    embeddings = get_embeddings_batch(chunks)
    points = []
    for index, (chunk_text, embedding) in enumerate(zip(chunks, embeddings)):
        points.append(PointStruct(
            id=str(uuid.uuid4()),
            vector=embedding,
            payload={
                "brand_slug": BRAND_SLUG,
                "doc_id": doc_id,
                "doc_filename": filename,
                "page_number": page_num,
                "text": chunk_text,
                "chunk_index": index,
                "chunk_total": len(chunks),
            },
        ))
    
    client.upsert(collection_name=COLLECTION, points=points)
    reindexed += 1
    print(f"  Done: {chunk_count} -> {len(chunks)} chunks")

print(f"\nRe-indexed {reindexed} pages")

# Final count
info = client.get_collection(COLLECTION)
print(f"Total points in Qdrant: {info.points_count}")
'''

def run():
    host_key = paramiko.Ed25519Key(data=base64.b64decode(VPS_KEY_DATA))
    ssh = paramiko.SSHClient()
    ssh.get_host_keys().add(VPS_HOST, VPS_KEY_TYPE, host_key)
    ssh.connect(VPS_HOST, username=VPS_USER, password=VPS_PASS)

    sftp = ssh.open_sftp()
    with sftp.file("/root/andreja2/reindex_small.py", "w") as f:
        f.write(SCRIPT)
    sftp.close()

    cmds = [
        "docker cp /root/andreja2/reindex_small.py andreja_backend:/app/reindex_small.py",
        "docker exec andreja_backend python /app/reindex_small.py 2>&1",
    ]
    for cmd in cmds:
        stdin, stdout, stderr = ssh.exec_command(cmd, timeout=300)
        exit_code = stdout.channel.recv_exit_status()
        output = stdout.read().decode()
        if output.strip():
            print(output)
        err = stderr.read().decode()
        if err.strip() and exit_code != 0:
            print(f"ERR: {err[-300:]}")

    ssh.close()

if __name__ == "__main__":
    run()
