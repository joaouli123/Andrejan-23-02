"""Diagnosis v2: check Qdrant collections and search simulation."""
import os
from qdrant_client import QdrantClient
import google.genai

# 1. Qdrant collections
print("=== QDRANT COLLECTIONS ===")
qc = QdrantClient(host="qdrant", port=6333)
for col in qc.get_collections().collections:
    info = qc.get_collection(col.name)
    print(f"  {col.name}: {info.points_count} points")

# 2. Search simulation for "erro 100" in brand_lg
print("\n=== SEARCH 'oq significa erro 100' in brand_lg ===")
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
            limit=10,
            with_payload=True,
            score_threshold=0.3,
        )
        print(f"\n  Collection {col_name}: {len(results.points)} results")
        for p in results.points:
            text = p.payload.get("text", "")[:200]
            print(f"    score={p.score:.4f} page={p.payload.get('page_number')} text={text}")
    except Exception as e:
        print(f"\n  Collection {col_name}: ERROR - {e}")

# 3. Check what page 64 chunks look like
print("\n=== PAGE 64 CHUNKS in brand_lg ===")
from qdrant_client.models import Filter, FieldCondition, MatchValue
try:
    results = qc.scroll(
        collection_name="brand_lg",
        scroll_filter=Filter(
            must=[FieldCondition(key="page_number", match=MatchValue(value=64))]
        ),
        limit=20,
        with_payload=True,
    )
    for p in results[0]:
        text = p.payload.get("text", "")
        print(f"  chunk (len={len(text)}): {text[:300]}")
except Exception as e:
    print(f"  ERROR: {e}")
