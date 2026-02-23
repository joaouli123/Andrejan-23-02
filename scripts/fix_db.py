"""Delete doc 2 record and update doc 1 file_size from actual file on disk."""
import sqlite3, os

DB = "/app/data/andreja.db"

c = sqlite3.connect(DB)
cur = c.cursor()

# 1. Add file_size column if not exists
try:
    cur.execute("ALTER TABLE documents ADD COLUMN file_size INTEGER DEFAULT 0")
    print("Added file_size column to documents table")
except sqlite3.OperationalError as e:
    if "duplicate column" in str(e).lower():
        print("file_size column already exists")
    else:
        raise

# 2. Delete doc 2 entirely
cur.execute("DELETE FROM pages WHERE document_id=2")
cur.execute("DELETE FROM documents WHERE id=2")
print(f"Deleted doc 2 from database")

# 3. Update file_size for doc 1 from actual file
cur.execute("SELECT filename FROM documents WHERE id=1")
row = cur.fetchone()
if row:
    filepath = os.path.join("/app/data/uploads", row[0])
    if os.path.exists(filepath):
        size = os.path.getsize(filepath)
        cur.execute("UPDATE documents SET file_size=? WHERE id=1", (size,))
        print(f"Doc 1 file_size updated: {size} bytes ({size/1024/1024:.1f} MB)")
    else:
        print(f"File not found: {filepath}")

c.commit()

# Verify
cur.execute("SELECT id, original_filename, file_size, status FROM documents")
for r in cur.fetchall():
    print(f"  {r}")

c.close()
print("Done!")
