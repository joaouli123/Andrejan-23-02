"""Check all document statuses - processing, completed, errors."""
import sqlite3
import os

c = sqlite3.connect('/app/data/andreja.db')
cur = c.cursor()

# Total counts by status
cur.execute('SELECT status, COUNT(*) FROM documents GROUP BY status ORDER BY status')
print('=== STATUS GERAL ===')
for row in cur.fetchall():
    print(f'  {row[0]}: {row[1]}')

# Currently processing
cur.execute("""SELECT id, original_filename, processed_pages, total_pages, status 
               FROM documents WHERE status IN ('processing','pending') ORDER BY id""")
rows = cur.fetchall()
if rows:
    print(f'\n=== EM PROCESSAMENTO/PENDENTE ({len(rows)}) ===')
    for r in rows:
        pct = f"{r[2]*100//r[3]}%" if r[3] else "?"
        print(f'  id={r[0]} [{r[4]}] {r[2]}/{r[3]} pags ({pct}) - {r[1][:65]}')
else:
    print('\nNenhum doc em processamento no momento.')

# Recently completed (last 25 by id desc)
cur.execute("""SELECT id, original_filename, processed_pages, total_pages, status 
               FROM documents WHERE status IN ('completed','completed_with_errors') 
               ORDER BY id DESC LIMIT 25""")
rows = cur.fetchall()
print(f'\n=== ULTIMOS COMPLETADOS ({len(rows)}) ===')
for r in rows:
    flag = ' !!ERROS!!' if r[4] == 'completed_with_errors' else ''
    ok = "OK" if r[2] == r[3] else f"{r[2]}/{r[3]}"
    print(f'  id={r[0]} [{ok}]{flag} - {r[1][:65]}')

# Errors
cur.execute("""SELECT id, original_filename, processed_pages, total_pages, error_message 
               FROM documents WHERE status='error' ORDER BY id""")
rows = cur.fetchall()
if rows:
    print(f'\n=== COM ERRO ({len(rows)}) ===')
    for r in rows:
        print(f'  id={r[0]} {r[2]}/{r[3]} pags - {r[1][:50]} | {(r[4] or "")[:60]}')

# Total pages
cur.execute("SELECT count(*) FROM pages")
print(f'\nTotal paginas no DB: {cur.fetchone()[0]}')

# Qdrant stats
try:
    from qdrant_client import QdrantClient
    qc = QdrantClient(host="localhost", port=6333)
    for col in qc.get_collections().collections:
        info = qc.get_collection(col.name)
        print(f'\nQdrant [{col.name}]: {info.points_count} vetores')
except Exception as e:
    print(f'\nQdrant error: {e}')

c.close()
