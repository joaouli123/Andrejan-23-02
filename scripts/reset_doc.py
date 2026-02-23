"""
Reset document status and trigger reprocessing via the API.
Run inside Docker container.
"""
import sqlite3
import httpx
import sys

DB_PATH = "/app/data/andreja.db"

# Reset document status
c = sqlite3.connect(DB_PATH)
cur = c.cursor()

# Get document info
cur.execute("SELECT id, status, processed_pages, total_pages, original_filename FROM documents")
docs = cur.fetchall()
print(f"Found {len(docs)} documents:")
for d in docs:
    print(f"  id={d[0]}, status={d[1]}, pages={d[2]}/{d[3]}, file={d[4]}")

if not docs:
    print("No documents to reset")
    sys.exit(0)

doc_id = docs[0][0]

# Delete all pages (they have no embeddings anyway)
cur.execute("DELETE FROM pages WHERE document_id = ?", (doc_id,))
deleted = cur.rowcount

# Reset document to pending so processor can pick it up
cur.execute(
    "UPDATE documents SET status = 'pending', processed_pages = 0, error_message = NULL WHERE id = ?",
    (doc_id,)
)
c.commit()
print(f"\nReset doc {doc_id}: deleted {deleted} pages, status → pending")

# Verify
cur.execute("SELECT id, status, processed_pages FROM documents WHERE id = ?", (doc_id,))
print(f"After reset: {cur.fetchone()}")

c.close()
print("\nDone! Now re-upload the PDF via frontend to trigger processing.")
