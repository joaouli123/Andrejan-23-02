"""Test that XO 508 now appears in search results"""
import sys
sys.path.insert(0, "/app")
from ingestion.embedder import search_brand

query = "Falhas no XO 508"
print(f"Query: '{query}'")
print("=" * 70)

results = search_brand("otis", query, top_k=10)
xo_found = False
for i, r in enumerate(results):
    is_xo = r["doc_id"] in (32, 35)
    marker = " <<< XO 508!" if is_xo else ""
    if is_xo:
        xo_found = True
    print(f"  [{i+1}] score={r['score']:.4f} | doc_id={r['doc_id']} | page={r['page']} | {r['source'][:55]}{marker}")
    print(f"       {r['text'][:120]}...")

print()
if xo_found:
    print("SUCCESS: XO 508 docs found in results!")
else:
    print("FAIL: XO 508 docs NOT found!")

# Also test other queries
print("\n" + "=" * 70)
print("Test 2: 'XO 508'")
print("=" * 70)
results2 = search_brand("otis", "XO 508", top_k=5)
for i, r in enumerate(results2):
    is_xo = r["doc_id"] in (32, 35)
    marker = " <<< XO 508!" if is_xo else ""
    print(f"  [{i+1}] score={r['score']:.4f} | doc_id={r['doc_id']} | {r['source'][:55]}{marker}")

print("\n" + "=" * 70)
print("Test 3: 'codigos de falha OVF10'")
print("=" * 70)
results3 = search_brand("otis", "codigos de falha OVF10", top_k=5)
for i, r in enumerate(results3):
    print(f"  [{i+1}] score={r['score']:.4f} | doc_id={r['doc_id']} | {r['source'][:55]}")
