"""Check why XO 508 docs don't appear in search at all"""
import sys
sys.path.insert(0, "/app")

from ingestion.embedder import (
    get_query_embedding, get_qdrant_client, 
    _filename_match_bonus, _normalize_for_matching
)

# 1. Test filename matching
print("=" * 70)
print("1. FILENAME MATCH BONUS TEST")
print("=" * 70)
query = "Falhas no XO 508"
filenames = [
    "otis+XO+508+falhas.pdf",
    "Otis+XO+508.pdf",
    "Diagnóstico de Falhas Otis red1-1.pdf",
    "Manual Diagnóstico de Falhas (Troubleshooting).pdf",
]
for fn in filenames:
    bonus = _filename_match_bonus(fn, query)
    norm = _normalize_for_matching(fn)
    print(f"  {fn}")
    print(f"    normalized: '{norm}'")
    print(f"    bonus: {bonus:.4f}")

# 2. Search with low threshold to see ALL results including XO 508
print("\n" + "=" * 70)
print("2. BUSCA COM THRESHOLD BAIXO (0.1)")
print("=" * 70)

collection_name = "brand_otis"
client = get_qdrant_client()
query_vector = get_query_embedding(query)

results = client.search(
    collection_name=collection_name,
    query_vector=query_vector,
    limit=500,
    with_payload=True,
    score_threshold=0.1,
)

# Find XO 508 docs specifically
xo_results = [r for r in results if r.payload.get("doc_id") in (32, 35)]
print(f"\n  Total results at threshold 0.1: {len(results)}")
print(f"  XO 508 doc results (doc_id 32 or 35): {len(xo_results)}")

for hit in xo_results[:10]:
    payload = hit.payload or {}
    fn = payload.get("doc_filename", "?")
    bonus = _filename_match_bonus(fn, query)
    final_score = hit.score + bonus
    print(f"    raw_score={hit.score:.4f} + bonus={bonus:.4f} = {final_score:.4f} | doc_id={payload.get('doc_id')} | page={payload.get('page_number')} | {fn}")
    print(f"    text: {payload.get('text', '')[:150]}...")

# Show ranking distribution
print(f"\n  Score range for XO 508 docs:")
if xo_results:
    scores = [r.score for r in xo_results]
    print(f"    min={min(scores):.4f}, max={max(scores):.4f}, avg={sum(scores)/len(scores):.4f}")

print(f"\n  Top 5 overall (for comparison):")
for hit in results[:5]:
    payload = hit.payload or {}
    print(f"    score={hit.score:.4f} | doc_id={payload.get('doc_id')} | {payload.get('doc_filename', '?')[:50]}")
