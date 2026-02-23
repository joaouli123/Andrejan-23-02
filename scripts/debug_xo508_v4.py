"""Deep investigation: why XO 508 vectors don't match search at all"""
import sys, json
sys.path.insert(0, "/app")
import requests
import numpy as np

QDRANT = "http://qdrant:6333"
COLLECTION = "brand_otis"

# 1. Get a vector from doc 32 to check its dimensions
print("=" * 70)
print("1. VECTOR DIMENSIONS CHECK")
print("=" * 70)
for doc_id in [32, 35, 1, 130]:
    resp = requests.post(
        f"{QDRANT}/collections/{COLLECTION}/points/scroll",
        json={
            "filter": {"must": [{"key": "doc_id", "match": {"value": doc_id}}]},
            "limit": 1,
            "with_payload": False,
            "with_vector": True
        }
    )
    points = resp.json().get("result", {}).get("points", [])
    if points:
        vec = points[0].get("vector", [])
        vec_arr = np.array(vec) if vec else np.array([])
        print(f"  Doc {doc_id}: vector dim={len(vec)}, norm={np.linalg.norm(vec_arr):.4f}, first5={vec[:5]}")
    else:
        print(f"  Doc {doc_id}: NO POINTS FOUND!")

# 2. Get query embedding and compute manual similarity
from ingestion.embedder import get_query_embedding
query = "Falhas no XO 508"
query_vec = get_query_embedding(query)
query_arr = np.array(query_vec)
print(f"\n  Query vector: dim={len(query_vec)}, norm={np.linalg.norm(query_arr):.4f}")

# 3. Manual cosine similarity with doc 32 vectors
print("\n" + "=" * 70)
print("2. MANUAL COSINE SIMILARITY")
print("=" * 70)
for doc_id in [32, 35, 1]:
    resp = requests.post(
        f"{QDRANT}/collections/{COLLECTION}/points/scroll",
        json={
            "filter": {"must": [{"key": "doc_id", "match": {"value": doc_id}}]},
            "limit": 3,
            "with_payload": True,
            "with_vector": True
        }
    )
    points = resp.json().get("result", {}).get("points", [])
    print(f"\n  Doc {doc_id}:")
    for pt in points[:3]:
        vec = np.array(pt.get("vector", []))
        if len(vec) > 0:
            cosine = np.dot(query_arr, vec) / (np.linalg.norm(query_arr) * np.linalg.norm(vec))
            txt = pt.get("payload", {}).get("text", "")[:80]
            print(f"    cosine={cosine:.4f} | {txt}...")

# 4. Check total vectors per doc for XO 508
print("\n" + "=" * 70)
print("3. TOTAL VECTORS FOR XO 508 DOCS")
print("=" * 70)
for doc_id in [32, 35]:
    resp = requests.post(
        f"{QDRANT}/collections/{COLLECTION}/points/scroll",
        json={
            "filter": {"must": [{"key": "doc_id", "match": {"value": doc_id}}]},
            "limit": 100,
            "with_payload": False,
            "with_vector": False
        }
    )
    count = len(resp.json().get("result", {}).get("points", []))
    print(f"  Doc {doc_id}: {count} vectors")
