import sqlite3
c = sqlite3.connect("/app/data/andreja.db")
cur = c.cursor()

cur.execute("SELECT id, status, processed_pages, total_pages, original_filename, error_message FROM documents")
rows = cur.fetchall()
print(f"Documents ({len(rows)}):")
for row in rows:
    print(f"  id={row[0]}, status={row[1]}, pages={row[2]}/{row[3]}, file={row[4]}")
    if row[5]:
        print(f"    error: {row[5][:200]}")

cur.execute("SELECT count(*), count(embedding_id) FROM pages")
total, with_emb = cur.fetchone()
print(f"\nPages: {total} total, {with_emb} with embeddings")

# Check pages with and without embeddings
cur.execute("SELECT page_number, length(gemini_text), embedding_id FROM pages ORDER BY page_number LIMIT 20")
for row in cur.fetchall():
    print(f"  Page {row[0]}: text={row[1]} chars, embedding={'YES' if row[2] else 'NO'}")

c.close()
