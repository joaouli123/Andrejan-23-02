"""Check all documents status + Qdrant vectors"""
import sqlite3
import os
import requests

DB = "/app/data/andreja.db"
UPLOAD_DIR = "/app/data/uploads"
QDRANT = "http://qdrant:6333"

c = sqlite3.connect(DB)
cur = c.cursor()

# All documents
cur.execute("SELECT id, brand_id, status, processed_pages, total_pages, original_filename, error_message FROM documents ORDER BY id")
rows = cur.fetchall()

# All brands
cur.execute("SELECT id, slug, name FROM brands")
brands = {r[0]: (r[1], r[2]) for r in cur.fetchall()}

print(f"{'='*80}")
print(f"TOTAL: {len(rows)} documentos")
print(f"{'='*80}")

completed = 0
processing = 0
errors = 0
total_vectors = 0

for r in rows:
    doc_id, brand_id, status, proc_pages, tot_pages, filename, err_msg = r
    brand_slug, brand_name = brands.get(brand_id, ("?", "?"))
    
    # Check Qdrant vectors
    collection = f"brand_{brand_slug}"
    try:
        resp = requests.post(
            f"{QDRANT}/collections/{collection}/points/scroll",
            json={"filter": {"must": [{"key": "doc_id", "match": {"value": doc_id}}]}, "limit": 1, "with_payload": False, "with_vector": False}
        )
        if resp.status_code == 200:
            data = resp.json()
            # Count with larger limit
            resp2 = requests.post(
                f"{QDRANT}/collections/{collection}/points/scroll",
                json={"filter": {"must": [{"key": "doc_id", "match": {"value": doc_id}}]}, "limit": 500, "with_payload": False, "with_vector": False}
            )
            vec_count = len(resp2.json().get("result", {}).get("points", []))
        else:
            vec_count = -1
    except:
        vec_count = -1
    
    total_vectors += max(0, vec_count)
    
    # Check file on disk
    brand_dir = os.path.join(UPLOAD_DIR, brand_slug)
    file_exists = False
    if os.path.isdir(brand_dir):
        for f in os.listdir(brand_dir):
            if f.endswith(".pdf"):
                # Strip UUID prefix
                clean = f
                if len(f) > 37 and f[8] == '-' and f[36] == '_':
                    clean = f[37:]
                if clean == filename:
                    file_exists = True
                    break
    
    pages = f"{proc_pages}/{tot_pages}" if tot_pages else f"{proc_pages}/?"
    
    if status == "completed":
        emoji = "OK"
        completed += 1
    elif status == "processing":
        emoji = "PROC"
        processing += 1
    else:
        emoji = "ERRO"
        errors += 1
    
    vec_str = f"{vec_count} vetores" if vec_count >= 0 else "? vetores"
    file_str = "disco:OK" if file_exists else "disco:FALTA"
    err_str = f" | ERR: {err_msg[:60]}" if err_msg else ""
    
    print(f"  id={doc_id:>3} | {emoji:<4} | {pages:>7} pags | {vec_str:>12} | {file_str} | [{brand_name}] {filename}{err_str}")

print(f"\n{'='*80}")
print(f"Completos: {completed} | Processando: {processing} | Erro: {errors}")
print(f"Total vetores: {total_vectors}")
print(f"{'='*80}")

# Check for orphan files on disk
print(f"\nArquivos no disco sem registro no DB:")
cur.execute("SELECT original_filename, b.slug FROM documents d JOIN brands b ON d.brand_id=b.id")
db_files = {(r[0], r[1]) for r in cur.fetchall()}

orphans = 0
for brand_id, (slug, name) in brands.items():
    brand_dir = os.path.join(UPLOAD_DIR, slug)
    if not os.path.isdir(brand_dir):
        continue
    for f in os.listdir(brand_dir):
        if not f.endswith(".pdf"):
            continue
        clean = f
        if len(f) > 37 and f[8] == '-' and f[36] == '_':
            clean = f[37:]
        if (clean, slug) not in db_files:
            size = os.path.getsize(os.path.join(brand_dir, f)) / 1024 / 1024
            print(f"  ORFAO: [{name}] {f} ({size:.1f} MB)")
            orphans += 1

if orphans == 0:
    print("  Nenhum orfao!")

c.close()
