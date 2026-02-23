"""Audit: check for duplicate documents and orphan files."""
import sqlite3
import os
import glob

DB = "/app/data/andreja.db"
UPLOADS = "/app/data/uploads"

c = sqlite3.connect(DB)
cur = c.cursor()

# 1. Check for duplicate original_filenames within same brand
print("=" * 60)
print("1. DUPLICATAS NO BANCO (mesmo original_filename + brand_id)")
print("=" * 60)
cur.execute("""
    SELECT original_filename, brand_id, COUNT(*) as cnt, GROUP_CONCAT(id) as doc_ids
    FROM documents 
    GROUP BY LOWER(original_filename), brand_id 
    HAVING cnt > 1
""")
dupes = cur.fetchall()
if dupes:
    for d in dupes:
        print(f"  DUPLICATA: '{d[0]}' brand={d[1]} count={d[2]} doc_ids=[{d[3]}]")
else:
    print("  Nenhuma duplicata exata encontrada.")

# 2. Check for similar names (e.g., with/without prefix)
print()
print("=" * 60)
print("2. NOMES SIMILARES (possivel duplicata com prefixo)")
print("=" * 60)
cur.execute("SELECT id, original_filename, brand_id, status FROM documents ORDER BY id")
all_docs = cur.fetchall()
names_lower = {}
for doc in all_docs:
    key = doc[1].lower().strip()
    if key not in names_lower:
        names_lower[key] = []
    names_lower[key].append(doc)

# Check if one name contains another
for i, doc1 in enumerate(all_docs):
    for doc2 in all_docs[i+1:]:
        n1 = doc1[1].lower().strip()
        n2 = doc2[1].lower().strip()
        if n1 != n2 and (n1 in n2 or n2 in n1):
            print(f"  SIMILAR: id={doc1[0]} '{doc1[1]}' <-> id={doc2[0]} '{doc2[1]}'")

# 3. Files on disk vs DB
print()
print("=" * 60)
print("3. ARQUIVOS NO DISCO vs BANCO DE DADOS")
print("=" * 60)
cur.execute("SELECT filename FROM documents")
db_filenames = set(r[0] for r in cur.fetchall())

all_pdfs = glob.glob(os.path.join(UPLOADS, "**", "*.pdf"), recursive=True)
print(f"  Documentos no DB: {len(all_docs)}")
print(f"  PDFs no disco:    {len(all_pdfs)}")

orphans = []
for f in sorted(all_pdfs):
    rel = os.path.relpath(f, UPLOADS)
    if rel not in db_filenames:
        orphans.append(f)
        
if orphans:
    print(f"\n  ORFÃOS (no disco mas não no DB): {len(orphans)}")
    for o in orphans:
        size_mb = os.path.getsize(o) / (1024 * 1024)
        print(f"    {os.path.basename(o)} ({size_mb:.1f} MB)")
else:
    print("  Todos os arquivos no disco tem registro no DB.")

# 4. DB records without files on disk
print()
print("=" * 60)
print("4. REGISTROS SEM ARQUIVO (no DB mas arquivo sumiu)")
print("=" * 60)
missing = []
for doc in all_docs:
    cur2 = c.cursor()
    cur2.execute("SELECT filename FROM documents WHERE id=?", (doc[0],))
    fn = cur2.fetchone()[0]
    full_path = os.path.join(UPLOADS, fn)
    if not os.path.exists(full_path):
        missing.append((doc[0], doc[1], fn))

if missing:
    for m in missing:
        print(f"  FALTANDO: id={m[0]} '{m[1]}' -> {m[2]}")
else:
    print("  Todos os registros tem arquivo correspondente.")

# 5. Qdrant vectors per document
print()
print("=" * 60)
print("5. VETORES QDRANT POR DOCUMENTO")
print("=" * 60)
try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import Filter, FieldCondition, MatchValue
    qc = QdrantClient(host="qdrant", port=6333)
    for doc in all_docs:
        count = qc.count(
            collection_name="brand_otis",
            count_filter=Filter(must=[FieldCondition(key="doc_id", match=MatchValue(value=doc[0]))]),
            exact=True
        ).count
        status_mark = "✓" if count > 0 else "⚠ SEM VETORES"
        print(f"  id={doc[0]:2d} | {count:3d} vetores | {doc[3]:10s} | {doc[1]} {status_mark}")
except Exception as e:
    print(f"  Erro ao consultar Qdrant: {e}")

print()
print("=" * 60)
print("RESUMO")
print("=" * 60)
print(f"  Documentos: {len(all_docs)}")
print(f"  Duplicatas: {len(dupes)}")
print(f"  Orfãos:     {len(orphans)}")
print(f"  Faltando:   {len(missing)}")
c.close()
