#!/usr/bin/env python3
"""
Diagnostic: simulate the exact search the chatbot does
for the query 'apareceu erro 100 no meu display oq é??'
"""
import os, sys
sys.path.insert(0, "/app")

from qdrant_client import QdrantClient
from google import genai
from google.genai import types
import sqlite3

# --- Config ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
QDRANT_HOST = os.environ.get("QDRANT_HOST", "qdrant")
QDRANT_PORT = int(os.environ.get("QDRANT_PORT", "6333"))
EMBEDDING_MODEL = "gemini-embedding-001"
VECTOR_SIZE = 768
COLLECTION = "brand_lg"
QUERY = "apareceu erro 100 no meu display oq é??"

print(f"Query: {QUERY}")
print(f"Collection: {COLLECTION}")
print()

# --- 1. Generate query embedding ---
gclient = genai.Client(api_key=GEMINI_API_KEY)
result = gclient.models.embed_content(
    model=EMBEDDING_MODEL,
    contents=[QUERY],
    config=types.EmbedContentConfig(
        task_type="RETRIEVAL_QUERY",
        output_dimensionality=VECTOR_SIZE,
    ),
)
query_vector = result.embeddings[0].values
print(f"Query embedding generated: {len(query_vector)} dims")

# --- 2. Search Qdrant (same as search_brand) ---
qclient = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
collections = [c.name for c in qclient.get_collections().collections]
print(f"Collections: {collections}")

if COLLECTION not in collections:
    print(f"ERROR: Collection {COLLECTION} not found!")
    sys.exit(1)

info = qclient.get_collection(COLLECTION)
print(f"Collection {COLLECTION}: {info.points_count} points, vector_size={info.config.params.vectors.size}")
print()

# Search with LOW threshold first to see ALL potential matches
results_low = qclient.search(
    collection_name=COLLECTION,
    query_vector=query_vector,
    limit=30,
    with_payload=True,
    score_threshold=0.0,  # show everything
)

print("=" * 70)
print(f"SEARCH RESULTS (threshold=0.0, top 30)")
print("=" * 70)
for i, hit in enumerate(results_low):
    payload = hit.payload or {}
    text = payload.get("text", "")[:200].replace("\n", " ")
    page = payload.get("page_number", "?")
    doc_id = payload.get("doc_id", "?")
    print(f"  #{i+1} score={hit.score:.4f} | Doc {doc_id}, Page {page}")
    print(f"       {text}")
    print()

# Now with the actual threshold used in production
print("=" * 70)
print(f"FILTERED RESULTS (threshold=0.3, same as production)")
print("=" * 70)
above = [r for r in results_low if r.score >= 0.3]
print(f"  {len(above)} results above 0.3 threshold")
for r in above:
    payload = r.payload or {}
    print(f"  score={r.score:.4f} | Doc {payload.get('doc_id')}, Page {payload.get('page_number')}")

# --- 3. Check what text is stored for page 64 chunks ---
print()
print("=" * 70)
print("PAGE 64 CHUNKS IN QDRANT")
print("=" * 70)
from qdrant_client.models import Filter, FieldCondition, MatchValue
page64_results = qclient.scroll(
    collection_name=COLLECTION,
    scroll_filter=Filter(
        must=[
            FieldCondition(key="page_number", match=MatchValue(value=64)),
            FieldCondition(key="doc_id", match=MatchValue(value=1)),
        ]
    ),
    limit=20,
    with_payload=True,
)
points, _ = page64_results
print(f"Found {len(points)} chunks for doc 1, page 64")
for p in points:
    text = p.payload.get("text", "")
    print(f"  Chunk (len={len(text)}):")
    print(f"    {text[:300].replace(chr(10), ' ')}")
    print()

# --- 4. Check raw text from SQLite for page 64 ---
print("=" * 70)
print("PAGE 64 RAW TEXT FROM SQLITE")
print("=" * 70)
db = sqlite3.connect("/app/data/andreja.db")
cur = db.cursor()
cur.execute("SELECT gemini_text FROM pages WHERE document_id=1 AND page_number=64")
row = cur.fetchone()
if row:
    text = row[0]
    print(f"  Length: {len(text)}")
    print(f"  Full text:")
    print(text[:800])
    print("...")
    # Check for encoding issues
    bad_chars = sum(1 for c in text if ord(c) > 127 and c not in 'áàâãéèêíìîóòôõúùûçÁÀÂÃÉÈÊÍÌÎÓÒÔÕÚÙÛÇ""''–—•…°±²³¹ºª®©™')
    print(f"\n  Suspicious non-ASCII chars: {bad_chars}")
    # Find '100' mentions
    idx = text.find("100")
    if idx >= 0:
        print(f"  Context around '100': ...{text[max(0,idx-80):idx+120]}...")
db.close()

print()
print("=" * 70)
print("DIAGNOSIS")
print("=" * 70)
if not above:
    print("  NO RESULTS found above 0.3 threshold!")
    print("  This means the search returns EMPTY to the chatbot.")
    print("  The chatbot then says 'informação não encontrada'.")
    if results_low:
        best = results_low[0]
        print(f"  Best match was score={best.score:.4f} (below 0.3)")
        print(f"  Root cause: OCR text quality is too poor for good embeddings")
    else:
        print("  No matches at all - collection may be empty or wrong")
else:
    print(f"  {len(above)} results found. Check if they contain error 100 info.")
