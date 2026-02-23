import sqlite3
c = sqlite3.connect('/app/data/andreja.db')
cur = c.cursor()

# Processing/pending
cur.execute("SELECT id,status,processed_pages,total_pages,original_filename FROM documents WHERE status IN ('processing','pending') ORDER BY id")
rows = cur.fetchall()
print("=== PROCESSANDO ===")
for r in rows:
    pct = r[2]*100//r[3] if r[3] else 0
    print(f"  id={r[0]} [{r[1]}] {r[2]}/{r[3]} ({pct}%) - {r[4]}")
if not rows:
    print("  Nenhum")

# Total
cur.execute("SELECT COUNT(*) FROM documents")
total = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM documents WHERE status='completed'")
ok = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM documents WHERE status='completed_with_errors'")
errs = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM pages")
pgs = cur.fetchone()[0]
print(f"\nTotal: {total} docs | {ok} ok | {errs} com erros parciais")
print(f"Paginas no DB: {pgs}")

# New docs (id > 134)
cur.execute("SELECT id,status,processed_pages,total_pages,original_filename FROM documents WHERE id > 134 ORDER BY id")
rows = cur.fetchall()
print(f"\n=== NOVOS (id>134): {len(rows)} docs ===")
for r in rows:
    flag = " PROCESSANDO" if r[1] == 'processing' else (" PENDENTE" if r[1] == 'pending' else "")
    ok_str = "OK" if r[2]==r[3] else f"{r[2]}/{r[3]}"
    print(f"  id={r[0]} [{ok_str}]{flag} - {r[4]}")

# Qdrant
import sys
sys.path.insert(0, '/app')
from qdrant_client import QdrantClient
qc = QdrantClient(host="localhost", port=6333)
for col in qc.get_collections().collections:
    info = qc.get_collection(col.name)
    print(f"\nQdrant [{col.name}]: {info.points_count} vetores")

c.close()
