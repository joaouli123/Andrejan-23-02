import sqlite3
c = sqlite3.connect("/app/data/andreja.db")
cur = c.cursor()
cur.execute("SELECT id, status, processed_pages, total_pages, original_filename FROM documents")
for row in cur.fetchall():
    print(row)
c.close()
