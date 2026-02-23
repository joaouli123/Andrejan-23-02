import sqlite3
c = sqlite3.connect("/app/data/andreja.db")
cur = c.cursor()
cur.execute("SELECT id, filename, status, processed_pages, total_pages FROM documents ORDER BY id")
for r in cur.fetchall():
    print(r)
c.close()
