"""Search test script - runs INSIDE the container."""
import sys
sys.path.insert(0, '/app')
from ingestion.embedder import search_brand

queries = [
    "led vermelho emergência caixa inspeção Beneton não acende",
    "procedimento corrigir led vermelho emergência caixa inspeção",
    "D0510 Beneton emergência",
]

for q in queries:
    print(f"\n=== QUERY: {q} ===")
    results = search_brand('otis', q, top_k=5)
    for r in results:
        score = r['score']
        page = r['page']
        doc_id = r['doc_id']
        source = r['source']
        text = r['text'][:300]
        print(f"  score={score:.4f} page={page} doc_id={doc_id} source={source}")
        print(f"  text={text}")
        print()
