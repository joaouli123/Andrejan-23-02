"""Debug XO 508 search: check vectors, content, and search results"""
import sqlite3
import requests
import json

DB = "/app/data/andreja.db"
QDRANT = "http://qdrant:6333"
COLLECTION = "brand_otis"

c = sqlite3.connect(DB)
cur = c.cursor()

# 1. Check docs 32 and 35
print("=" * 70)
print("1. DOCUMENTOS XO 508 NO DB")
print("=" * 70)
cur.execute("SELECT id, status, processed_pages, total_pages, original_filename FROM documents WHERE id IN (32, 35)")
for r in cur.fetchall():
    print(f"  id={r[0]} | {r[1]} | {r[2]}/{r[3]} pags | {r[4]}")

# 2. Check pages content for these docs
print("\n" + "=" * 70)
print("2. PAGINAS SALVAS NO DB (primeiros 200 chars de cada)")
print("=" * 70)
for doc_id in [32, 35]:
    cur.execute("SELECT page_number, length(gemini_text), substr(gemini_text, 1, 200) FROM pages WHERE document_id=? ORDER BY page_number", (doc_id,))
    pages = cur.fetchall()
    print(f"\n  Doc {doc_id}: {len(pages)} paginas")
    for p in pages[:3]:  # first 3 pages
        print(f"    Pag {p[0]} ({p[1]} chars): {p[2][:150]}...")

# 3. Check Qdrant vectors for these docs
print("\n" + "=" * 70)
print("3. VETORES NO QDRANT")
print("=" * 70)
for doc_id in [32, 35]:
    resp = requests.post(
        f"{QDRANT}/collections/{COLLECTION}/points/scroll",
        json={
            "filter": {"must": [{"key": "doc_id", "match": {"value": doc_id}}]},
            "limit": 5,
            "with_payload": True,
            "with_vector": False
        }
    )
    if resp.status_code == 200:
        points = resp.json().get("result", {}).get("points", [])
        print(f"\n  Doc {doc_id}: {len(points)} vetores (mostrando primeiros 5)")
        for pt in points[:3]:
            payload = pt.get("payload", {})
            text = payload.get("text", "")[:200]
            source = payload.get("source", "?")
            print(f"    id={pt['id']} | source={source}")
            print(f"    text: {text}...")
    else:
        print(f"  Doc {doc_id}: ERRO {resp.status_code}")

# 4. Try searching for "XO 508" directly in Qdrant text field
print("\n" + "=" * 70)
print("4. BUSCA POR 'XO 508' NOS PAYLOADS (text filter)")
print("=" * 70)
# Search all points that have "XO 508" or "xo 508" in text
resp = requests.post(
    f"{QDRANT}/collections/{COLLECTION}/points/scroll",
    json={
        "filter": {
            "should": [
                {"key": "source", "match": {"text": "XO"}},
                {"key": "source", "match": {"text": "xo"}},
            ]
        },
        "limit": 20,
        "with_payload": True,
        "with_vector": False
    }
)
if resp.status_code == 200:
    points = resp.json().get("result", {}).get("points", [])
    print(f"  Encontrados: {len(points)} vetores com 'XO' no source")
    for pt in points[:10]:
        payload = pt.get("payload", {})
        print(f"    source={payload.get('source', '?')} | doc_id={payload.get('doc_id', '?')}")
        print(f"    text: {payload.get('text', '')[:120]}...")
else:
    print(f"  ERRO: {resp.status_code} {resp.text[:200]}")

# 5. Check collection info
print("\n" + "=" * 70)
print("5. INFO DA COLLECTION")
print("=" * 70)
resp = requests.get(f"{QDRANT}/collections/{COLLECTION}")
if resp.status_code == 200:
    info = resp.json().get("result", {})
    print(f"  Vectors count: {info.get('vectors_count', '?')}")
    print(f"  Points count: {info.get('points_count', '?')}")
    print(f"  Config: {json.dumps(info.get('config', {}).get('params', {}), indent=2)[:500]}")

c.close()
