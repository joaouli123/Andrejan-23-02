"""Reprocess doc 146 which is stuck at 11/15."""
import sqlite3

c = sqlite3.connect('/app/data/andreja.db')
cur = c.cursor()

# Check current state
cur.execute("SELECT id, status, processed_pages, total_pages, original_filename FROM documents WHERE id=146")
r = cur.fetchone()
print(f"Before: id={r[0]} status={r[1]} {r[2]}/{r[3]} - {r[4]}")

# Reset to pending so the system picks it up again
cur.execute("UPDATE documents SET status='pending', error_message=NULL WHERE id=146")
c.commit()

# Verify
cur.execute("SELECT id, status, processed_pages, total_pages FROM documents WHERE id=146")
r = cur.fetchone()
print(f"After: id={r[0]} status={r[1]} {r[2]}/{r[3]}")
print("Doc 146 reset to pending - will be reprocessed automatically")

c.close()
