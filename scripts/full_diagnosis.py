"""Full diagnosis: brands, docs, Qdrant collections, page 64 text, simulated search."""
import sqlite3
from qdrant_client import QdrantClient

DB = "/app/data/andreja.db"

c = sqlite3.connect(DB)
cur = c.cursor()

# 1. List all brands
print("=== BRANDS ===")
cur.execute("SELECT id, name, slug FROM brands ORDER BY id")
for r in cur.fetchall():
    print(f"  {r}")

# 2. List all docs
print("\n=== DOCUMENTS ===")
cur.execute("SELECT id, brand_id, filename, status, processed_pages, total_pages FROM documents ORDER BY id")
for r in cur.fetchall():
    print(f"  {r}")

# 3. Page 64 text (where erro 100 should be)
print("\n=== PAGE 64 TEXT (first 500 chars) ===")
cur.execute("SELECT id, document_id, page_number, length(text) as tlen, substr(text, 1, 500) FROM pages WHERE page_number=64 AND document_id=1")
for r in cur.fetchall():
    print(f"  page_id={r[0]}, doc_id={r[1]}, page={r[2]}, text_len={r[3]}")
    print(f"  TEXT: {r[4]}")

# 4. Pages with 'erro' and '100'
print("\n=== PAGES WITH 'erro' near '100' ===")
cur.execute("SELECT page_number, length(text), substr(text, 1, 200) FROM pages WHERE document_id=1 AND lower(text) LIKE '%erro%' AND text LIKE '%100%'")
for r in cur.fetchall():
    print(f"  Page {r[0]} ({r[1]} chars): {r[2][:150]}...")

c.close()

# 5. Qdrant collections
print("\n=== QDRANT COLLECTIONS ===")
qc = QdrantClient(host="qdrant", port=6333)
for col in qc.get_collections().collections:
    info = qc.get_collection(col.name)
    print(f"  {col.name}: {info.points_count} points, {info.vectors_count} vectors")

# 6. Search simulation for "erro 100"
print("\n=== SEARCH SIMULATION for 'oq significa erro 100' ===")
import os, google.genai

client = google.genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
query = "oq significa erro 100"
resp = client.models.embed_content(
    model="gemini-embedding-001",
    contents=query,
    config={"task_type": "RETRIEVAL_QUERY", "output_dimensionality": 768},
)
qvec = resp.embeddings[0].values

for col_name in ["brand_lg", "brand_otis"]:
    try:
        results = qc.query_points(
            collection_name=col_name,
            query=qvec,
            limit=5,
            with_payload=True,
            score_threshold=0.3,
        )
        print(f"\n  Collection {col_name}: {len(results.points)} results")
        for p in results.points:
            text = p.payload.get("text", "")[:150]
            print(f"    score={p.score:.4f} page={p.payload.get('page_number')} doc={p.payload.get('doc_id')} text={text}...")
    except Exception as e:
        print(f"\n  Collection {col_name}: ERROR - {e}")
