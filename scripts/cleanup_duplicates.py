"""Cleanup: remove orphan files and duplicate documents from VPS."""
import sqlite3
import os
import glob

DB = "/app/data/andreja.db"
UPLOADS = "/app/data/uploads"

c = sqlite3.connect(DB)
cur = c.cursor()

print("=" * 60)
print("LIMPEZA DE DUPLICATAS E ORFÃOS")
print("=" * 60)

# 1. Remove orphan files (on disk but not in DB)
print("\n1. Removendo arquivos órfãos...")
cur.execute("SELECT filename FROM documents")
db_filenames = set(r[0] for r in cur.fetchall())

all_pdfs = glob.glob(os.path.join(UPLOADS, "**", "*.pdf"), recursive=True)
removed_orphans = 0
for f in all_pdfs:
    rel = os.path.relpath(f, UPLOADS)
    if rel not in db_filenames:
        size_mb = os.path.getsize(f) / (1024 * 1024)
        print(f"  REMOVENDO ÓRFÃO: {os.path.basename(f)} ({size_mb:.1f} MB)")
        os.remove(f)
        removed_orphans += 1

if removed_orphans == 0:
    print("  Nenhum órfão encontrado.")
else:
    print(f"  {removed_orphans} arquivo(s) órfão(s) removido(s).")

# 2. Check for near-duplicate documents (one name contains the other)
print("\n2. Verificando documentos similares...")
cur.execute("SELECT id, original_filename, brand_id, status, filename FROM documents ORDER BY id")
all_docs = cur.fetchall()

# Normalize for comparison
import unicodedata, re
def normalize(name):
    name = re.sub(r'\.pdf$', '', name.strip(), flags=re.IGNORECASE)
    name = re.sub(r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}_', '', name)
    nfkd = unicodedata.normalize('NFKD', name)
    name = ''.join(ch for ch in nfkd if not unicodedata.combining(ch))
    name = name.lower()
    name = re.sub(r'[^a-z0-9\s]', ' ', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name

# Find groups with same normalized name (or containment)
def is_duplicate(a, b):
    if a == b:
        return True
    shorter = min(a, b, key=len)
    longer = max(a, b, key=len)
    if len(shorter.split()) >= 3 and shorter in longer:
        return True
    return False

groups = {}
for doc in all_docs:
    norm = normalize(doc[1])
    found_group = None
    for group_key in groups:
        if is_duplicate(norm, group_key):
            found_group = group_key
            break
    if found_group:
        groups[found_group].append(doc)
    else:
        groups[norm] = [doc]

removed_dupes = 0
for norm, docs_in_group in groups.items():
    if len(docs_in_group) <= 1:
        continue
    
    print(f"\n  GRUPO SIMILAR (normalizado: '{norm}'):")
    for d in docs_in_group:
        print(f"    id={d[0]} | '{d[1]}' | status={d[3]}")
    
    # Keep the first completed one (lowest id), remove others
    keeper = None
    for d in sorted(docs_in_group, key=lambda x: x[0]):
        if d[3] == "completed":
            keeper = d
            break
    if not keeper:
        keeper = docs_in_group[0]
    
    print(f"  MANTENDO: id={keeper[0]} '{keeper[1]}'")
    
    for d in docs_in_group:
        if d[0] == keeper[0]:
            continue
        doc_id = d[0]
        filename = d[4]  # filename with UUID prefix
        filepath = os.path.join(UPLOADS, filename)
        
        # Delete Qdrant vectors
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.models import Filter, FieldCondition, MatchValue
            qc = QdrantClient(host="qdrant", port=6333)
            # Determine collection from brand
            cur2 = c.cursor()
            cur2.execute("SELECT slug FROM brands WHERE id=?", (d[2],))
            brand_row = cur2.fetchone()
            if brand_row:
                col_name = f"brand_{brand_row[0]}"
                qc.delete(
                    collection_name=col_name,
                    points_selector=Filter(
                        must=[FieldCondition(key="doc_id", match=MatchValue(value=doc_id))]
                    )
                )
                print(f"  REMOVIDO vetores Qdrant de doc_id={doc_id} em {col_name}")
        except Exception as e:
            print(f"  Erro ao remover vetores: {e}")
        
        # Delete pages from DB
        cur.execute("DELETE FROM pages WHERE document_id=?", (doc_id,))
        deleted_pages = cur.rowcount
        
        # Delete document record
        cur.execute("DELETE FROM documents WHERE id=?", (doc_id,))
        
        # Delete file from disk
        if os.path.exists(filepath):
            os.remove(filepath)
            print(f"  REMOVIDO: id={doc_id} '{d[1]}' ({deleted_pages} pages, arquivo deletado)")
        else:
            print(f"  REMOVIDO: id={doc_id} '{d[1]}' ({deleted_pages} pages, arquivo já não existia)")
        
        removed_dupes += 1

c.commit()

if removed_dupes == 0:
    print("  Nenhuma duplicata similar encontrada.")

# 3. Final state
print("\n" + "=" * 60)
print("RESULTADO FINAL")
print("=" * 60)
cur.execute("SELECT COUNT(*) FROM documents")
total_docs = cur.fetchone()[0]
remaining_pdfs = len(glob.glob(os.path.join(UPLOADS, "**", "*.pdf"), recursive=True))
print(f"  Documentos no DB:  {total_docs}")
print(f"  PDFs no disco:     {remaining_pdfs}")
print(f"  Órfãos removidos:  {removed_orphans}")
print(f"  Duplicatas removidas: {removed_dupes}")
if total_docs == remaining_pdfs:
    print("  ✓ DB e disco estão sincronizados!")
else:
    print(f"  ⚠ DIFERENÇA: {remaining_pdfs - total_docs} arquivo(s) de diferença")

c.close()
