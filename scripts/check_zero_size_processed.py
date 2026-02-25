import sqlite3
import os

DB_PATH = os.environ.get("DB_PATH", "/app/data/andreja.db")
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

print("=== RESUMO GERAL ===")
cur.execute("SELECT COUNT(*) FROM documents")
total_docs = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM documents WHERE file_size IS NULL OR file_size=0")
zero_size_docs = cur.fetchone()[0]
print(f"Total docs: {total_docs}")
print(f"Docs com file_size=0/null: {zero_size_docs}")

print("\n=== STATUS DOS DOCS COM file_size=0 ===")
cur.execute(
    """
    SELECT status, COUNT(*)
    FROM documents
    WHERE file_size IS NULL OR file_size=0
    GROUP BY status
    ORDER BY COUNT(*) DESC
    """
)
for status, cnt in cur.fetchall():
    print(f"{status}: {cnt}")

print("\n=== VALIDAÇÃO DE PROCESSAMENTO (file_size=0) ===")
cur.execute(
    """
    SELECT
        COUNT(*) as total_zero,
        SUM(CASE WHEN status IN ('completed', 'completed_with_errors') THEN 1 ELSE 0 END) as completed_like,
        SUM(CASE WHEN processed_pages > 0 THEN 1 ELSE 0 END) as with_processed_pages,
        SUM(CASE WHEN total_pages > 0 THEN 1 ELSE 0 END) as with_total_pages
    FROM documents
    WHERE file_size IS NULL OR file_size=0
    """
)
row = cur.fetchone()
print(f"Total zero-size: {row[0]}")
print(f"Status completo/completo_com_erros: {row[1]}")
print(f"Com processed_pages > 0: {row[2]}")
print(f"Com total_pages > 0: {row[3]}")

print("\n=== AMOSTRA (20 docs zero-size mais recentes) ===")
cur.execute(
    """
    SELECT d.id, b.name, d.original_filename, d.status, d.processed_pages, d.total_pages
    FROM documents d
    JOIN brands b ON b.id=d.brand_id
    WHERE d.file_size IS NULL OR d.file_size=0
    ORDER BY d.id DESC
    LIMIT 20
    """
)
for doc_id, brand, filename, status, processed_pages, total_pages in cur.fetchall():
    print(f"ID={doc_id} | {brand} | {status} | {processed_pages}/{total_pages} | {filename}")

print("\n=== CHECAGEM DE TEXTO/EMBEDDING (amostra 10 docs zero-size) ===")
cur.execute(
    """
    SELECT id, original_filename
    FROM documents
    WHERE file_size IS NULL OR file_size=0
    ORDER BY id DESC
    LIMIT 10
    """
)
sample_docs = cur.fetchall()

for doc_id, filename in sample_docs:
    cur.execute("SELECT COUNT(*) FROM pages WHERE document_id=?", (doc_id,))
    page_rows = cur.fetchone()[0]
    cur.execute(
        """
        SELECT COUNT(*) FROM pages
        WHERE document_id=?
          AND gemini_text IS NOT NULL
          AND LENGTH(TRIM(gemini_text)) >= 20
        """,
        (doc_id,),
    )
    with_text = cur.fetchone()[0]
    cur.execute(
        """
        SELECT COUNT(*) FROM pages
        WHERE document_id=?
          AND embedding_id IS NOT NULL
          AND LENGTH(TRIM(embedding_id)) > 0
        """,
        (doc_id,),
    )
    with_embed = cur.fetchone()[0]

    print(f"ID={doc_id} | pages={page_rows} | text_ok={with_text} | embeddings={with_embed} | {filename}")

conn.close()
