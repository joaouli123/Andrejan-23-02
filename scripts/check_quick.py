import sqlite3
c = sqlite3.connect('/app/data/andreja.db')
cur = c.cursor()

# Check docs 146 and 164
for doc_id in [146, 164]:
    cur.execute("SELECT id,status,processed_pages,total_pages,error_message FROM documents WHERE id=?", (doc_id,))
    r = cur.fetchone()
    if r:
        print(f"Doc {r[0]}: {r[1]} - {r[2]}/{r[3]} pags | err: {(r[4] or '-')[:80]}")

# Any processing/pending
cur.execute("SELECT id,status,processed_pages,total_pages,original_filename FROM documents WHERE status IN ('processing','pending') ORDER BY id")
rows = cur.fetchall()
print(f"\nProcessando: {len(rows)}")
for r in rows:
    print(f"  id={r[0]} [{r[1]}] {r[2]}/{r[3]} - {r[4][:60]}")

# Total counts
cur.execute("SELECT status, COUNT(*) FROM documents GROUP BY status")
print("\nResumo:")
for r in cur.fetchall():
    print(f"  {r[0]}: {r[1]}")

# Total pages
cur.execute("SELECT COUNT(*) FROM pages")
print(f"Total paginas: {cur.fetchone()[0]}")

# Count new brands
cur.execute("SELECT id, slug, name FROM brands ORDER BY id")
print("\nMarcas:")
for r in cur.fetchall():
    cur.execute("SELECT COUNT(*) FROM documents WHERE brand_id=?", (r[0],))
    cnt = cur.fetchone()[0]
    print(f"  {r[2]} (slug={r[1]}): {cnt} docs")

c.close()
