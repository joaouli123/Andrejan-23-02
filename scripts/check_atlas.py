import sqlite3, os

db_path = os.environ.get("DB_PATH", "/app/data/andreja.db")
conn = sqlite3.connect(db_path)
cur = conn.cursor()

# Find Atlas brand(s)
cur.execute("SELECT id, slug, name FROM brands WHERE LOWER(name) LIKE '%atlas%' OR LOWER(slug) LIKE '%atlas%'")
brands = cur.fetchall()
print("=== BRANDS ATLAS ===")
for b in brands:
    print(f"  ID={b[0]} slug='{b[1]}' name='{b[2]}'")

if not brands:
    print("Nenhuma brand Atlas encontrada!")
    conn.close()
    exit()

brand_ids = [b[0] for b in brands]
placeholders = ','.join(['?' for _ in brand_ids])

# All Atlas documents
cur.execute(f"""
    SELECT d.id, d.original_filename, d.status, d.processed_pages, d.total_pages, d.error_message
    FROM documents d
    WHERE d.brand_id IN ({placeholders})
    ORDER BY d.id
""", brand_ids)
docs = cur.fetchall()

print(f"\n=== DOCUMENTOS ATLAS ({len(docs)} total) ===")
print(f"{'ID':>4} | {'Status':<25} | {'Pages':>10} | Filename")
print("-" * 100)

completed = 0
processing = 0
errors = 0
pending = 0
total_pages = 0

for d in docs:
    doc_id, filename, status, proc_pages, tot_pages, error_msg = d
    pages_str = f"{proc_pages or 0}/{tot_pages or '?'}"
    
    status_display = status
    if error_msg:
        status_display = f"{status} ⚠️"
    
    print(f"{doc_id:>4} | {status_display:<25} | {pages_str:>10} | {filename}")
    
    if error_msg:
        print(f"      ERROR: {error_msg[:120]}")
    
    if status == 'completed':
        completed += 1
        total_pages += (proc_pages or 0)
    elif status == 'completed_with_errors':
        errors += 1
        total_pages += (proc_pages or 0)
    elif status == 'processing':
        processing += 1
    elif status == 'pending':
        pending += 1

print(f"\n=== RESUMO ===")
print(f"  Completed: {completed}")
print(f"  Processing: {processing}")
print(f"  Pending: {pending}")
print(f"  With Errors: {errors}")
print(f"  Total pages processed: {total_pages}")

# Check for pages with no text
cur.execute(f"""
    SELECT d.id, d.original_filename, COUNT(p.id) as empty_pages
    FROM documents d
    JOIN pages p ON p.document_id = d.id
    WHERE d.brand_id IN ({placeholders})
    AND (p.gemini_text IS NULL OR p.gemini_text = '' OR LENGTH(p.gemini_text) < 10)
    GROUP BY d.id
    ORDER BY empty_pages DESC
""", brand_ids)
empty = cur.fetchall()
if empty:
    print(f"\n=== DOCS COM PÁGINAS VAZIAS/CURTAS ===")
    for e in empty:
        print(f"  ID={e[0]} ({e[2]} páginas vazias) - {e[1]}")

# Check for potential duplicates by filename similarity
cur.execute(f"""
    SELECT d.id, d.original_filename
    FROM documents d
    WHERE d.brand_id IN ({placeholders})
    ORDER BY d.original_filename
""", brand_ids)
all_docs = cur.fetchall()
print(f"\n=== VERIFICAÇÃO DE DUPLICATAS ===")
seen = {}
for doc_id, fname in all_docs:
    normalized = fname.lower().replace(' ', '').replace('_', '').replace('-', '')
    if normalized in seen:
        print(f"  POSSÍVEL DUPLICATA: ID={doc_id} '{fname}' ~ ID={seen[normalized]} ")
    else:
        seen[normalized] = doc_id

if not any(True for _ in []):
    print("  Nenhuma duplicata óbvia encontrada.")

# Also check Schindler brand separately
cur.execute("SELECT id, slug, name FROM brands WHERE LOWER(name) LIKE '%schindler%' AND LOWER(name) NOT LIKE '%atlas%'")
schindler_only = cur.fetchall()
if schindler_only:
    print(f"\n=== BRAND 'SCHINDLER' (sem Atlas) ===")
    for b in schindler_only:
        print(f"  ID={b[0]} slug='{b[1]}' name='{b[2]}'")
        cur.execute("SELECT COUNT(*) FROM documents WHERE brand_id=?", (b[0],))
        cnt = cur.fetchone()[0]
        print(f"  Docs: {cnt}")

# Overall stats
cur.execute("SELECT COUNT(*) FROM documents")
total_all = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM documents WHERE status='processing'")
proc_all = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM documents WHERE status='pending'")
pend_all = cur.fetchone()[0]
print(f"\n=== GERAL DO SISTEMA ===")
print(f"  Total docs: {total_all}")
print(f"  Processing: {proc_all}")
print(f"  Pending: {pend_all}")

conn.close()
