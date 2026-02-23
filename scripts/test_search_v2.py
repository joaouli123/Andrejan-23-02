"""Test comprehensive search improvements on VPS."""
import sqlite3
import sys
sys.path.insert(0, "/app")

from ingestion.embedder import search_brand, _extract_search_keywords, _db_keyword_search

def test_query(query, brand="otis"):
    print(f"\n{'='*60}")
    print(f"QUERY: '{query}'")
    
    # Show extracted keywords
    kws = _extract_search_keywords(query)
    print(f"Keywords: {kws}")
    
    # Show DB keyword matches
    if kws:
        db_docs = _db_keyword_search(kws, brand)
        print(f"DB keyword doc_ids: {db_docs}")
    
    # Run search
    results = search_brand(brand, query, top_k=10)
    print(f"Results: {len(results)}")
    for i, r in enumerate(results[:7]):
        print(f"  #{i+1}: score={r['score']:.4f} doc={r['doc_id']} "
              f"p{r['page']} {r['source'][:50]}")
    return results

# Test 1: XO 508 (the original problem)
test_query("Falhas no XO 508")

# Test 2: Short model name
test_query("XO 508")

# Test 3: OVF10
test_query("codigos de falha OVF10")

# Test 4: Generic query (should work normally)
test_query("calibração do drive")

# Test 5: ADV (common elevator model)
test_query("ADV 210")

# Test 6: Placa LCB
test_query("placa LCB2")

# Test 7: Something that might only be in content, not filename
test_query("inversor de frequência")

# Test 8: DO 2000
test_query("DO 2000 gearless")

print("\n" + "="*60)
print("ALL TESTS COMPLETE")
