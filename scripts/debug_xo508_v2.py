"""Check actual payload fields of XO 508 vectors in Qdrant"""
import requests
import json

QDRANT = "http://qdrant:6333"
COLLECTION = "brand_otis"

# Check doc 32 vectors with full payload
for doc_id in [32, 35]:
    resp = requests.post(
        f"{QDRANT}/collections/{COLLECTION}/points/scroll",
        json={
            "filter": {"must": [{"key": "doc_id", "match": {"value": doc_id}}]},
            "limit": 2,
            "with_payload": True,
            "with_vector": False
        }
    )
    points = resp.json().get("result", {}).get("points", [])
    print(f"\nDoc {doc_id}: {len(points)} pontos")
    if points:
        p = points[0]
        payload = p.get("payload", {})
        print(f"  Payload keys: {list(payload.keys())}")
        print(f"  doc_filename: '{payload.get('doc_filename', 'N/A')}'")
        print(f"  source: '{payload.get('source', 'N/A')}'")
        print(f"  doc_id: {payload.get('doc_id', 'N/A')}")
        print(f"  brand_slug: '{payload.get('brand_slug', 'N/A')}'")
        print(f"  page_number: {payload.get('page_number', 'N/A')}")
        print(f"  text (first 100): {payload.get('text', '')[:100]}")

# Also check a recently uploaded doc like 130 for comparison
for doc_id in [130, 1]:
    resp = requests.post(
        f"{QDRANT}/collections/{COLLECTION}/points/scroll",
        json={
            "filter": {"must": [{"key": "doc_id", "match": {"value": doc_id}}]},
            "limit": 1,
            "with_payload": True,
            "with_vector": False
        }
    )
    points = resp.json().get("result", {}).get("points", [])
    print(f"\nDoc {doc_id} (comparacao):")
    if points:
        payload = points[0].get("payload", {})
        print(f"  Payload keys: {list(payload.keys())}")
        print(f"  doc_filename: '{payload.get('doc_filename', 'N/A')}'")

# Now simulate the actual search for "Falhas no XO 508"
print("\n" + "=" * 70)
print("SIMULANDO BUSCA SEMANTICA: top 10 results")
print("=" * 70)

# Get embedding for query
import sys
sys.path.insert(0, "/app")
from ingestion.embedder import search_brand

results = search_brand("otis", "Falhas no XO 508", top_k=10)
for i, r in enumerate(results):
    print(f"  [{i+1}] score={r['score']:.4f} | doc_id={r['doc_id']} | source={r['source'][:60]} | page={r['page']}")
    print(f"       text: {r['text'][:120]}...")
