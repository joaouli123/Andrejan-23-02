"""Cancel doc 2 (duplicate) and delete its pages/embeddings. Keep only doc 1."""
import sqlite3
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

DB = "/app/data/andreja.db"

c = sqlite3.connect(DB)
cur = c.cursor()

# Mark doc 2 as error so processor stops picking new pages
cur.execute(
    "UPDATE documents SET status='completed', processed_pages=0, total_pages=0 WHERE id=2"
)

# Delete all pages from doc 2
cur.execute("DELETE FROM pages WHERE document_id=2")
rows = cur.rowcount
print(f"Deleted {rows} pages from doc 2")

c.commit()
c.close()

# Remove doc 2 vectors from Qdrant (if any were already created)
try:
    qc = QdrantClient(host="qdrant", port=6333)
    for col in qc.get_collections().collections:
        result = qc.delete(
            collection_name=col.name,
            points_selector=Filter(
                must=[FieldCondition(key="doc_id", match=MatchValue(value=2))]
            ),
        )
        print(f"  Qdrant {col.name}: deleted doc_id=2 vectors")
except Exception as e:
    print(f"  Qdrant cleanup: {e}")

print("Doc 2 (duplicata) removido. Apenas doc 1 continua processando.")
