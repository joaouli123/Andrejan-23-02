import sqlite3
import os
from datetime import datetime

DB_PATH = os.environ.get("DB_PATH", "/app/data/andreja.db")
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

needle = "infolev ifl-750"

cur.execute(
    """
    SELECT d.id, d.original_filename, d.status, d.processed_pages, d.total_pages,
           d.uploaded_at, d.completed_at, d.error_message,
           b.name as brand_name
    FROM documents d
    JOIN brands b ON b.id = d.brand_id
    WHERE LOWER(d.original_filename) LIKE ?
    ORDER BY d.id DESC
    """,
    (f"%{needle}%",),
)
rows = cur.fetchall()

print("=== BUSCA DE DOCUMENTO ===")
print(f"Termo: {needle}")
print(f"Encontrados: {len(rows)}")

if not rows:
    print("Nenhum documento encontrado com esse nome.")
    conn.close()
    raise SystemExit(0)

for r in rows:
    doc_id, filename, status, processed_pages, total_pages, uploaded_at, completed_at, error_message, brand_name = r
    print("\n" + "-"*90)
    print(f"DOC ID: {doc_id}")
    print(f"Arquivo: {filename}")
    print(f"Marca: {brand_name}")
    print(f"Status: {status}")
    print(f"Páginas: {processed_pages}/{total_pages}")
    print(f"Upload: {uploaded_at}")
    print(f"Conclusão: {completed_at}")

    # Calculate processing duration if possible
    duration_sec = None
    if uploaded_at and completed_at:
        try:
            start = datetime.fromisoformat(str(uploaded_at))
            end = datetime.fromisoformat(str(completed_at))
            duration_sec = (end - start).total_seconds()
            print(f"Tempo de processamento: {duration_sec:.1f}s ({duration_sec/60:.2f} min)")
        except Exception:
            pass

    if error_message:
        print(f"Erro: {error_message}")

    # Pages table checks
    cur.execute("SELECT COUNT(*) FROM pages WHERE document_id=?", (doc_id,))
    pages_rows = cur.fetchone()[0]

    cur.execute(
        """
        SELECT COUNT(*) FROM pages
        WHERE document_id=?
          AND gemini_text IS NOT NULL
          AND LENGTH(TRIM(gemini_text)) >= 20
        """,
        (doc_id,),
    )
    pages_with_text = cur.fetchone()[0]

    cur.execute(
        """
        SELECT COUNT(*) FROM pages
        WHERE document_id=?
          AND (gemini_text IS NULL OR LENGTH(TRIM(gemini_text)) < 20)
        """,
        (doc_id,),
    )
    pages_empty_or_short = cur.fetchone()[0]

    cur.execute(
        """
        SELECT COUNT(*) FROM pages
        WHERE document_id=?
          AND embedding_id IS NOT NULL
          AND LENGTH(TRIM(embedding_id)) > 0
        """,
        (doc_id,),
    )
    pages_with_embedding = cur.fetchone()[0]

    print(f"Rows na tabela pages: {pages_rows}")
    print(f"Páginas com texto útil (>=20 chars): {pages_with_text}")
    print(f"Páginas vazias/curtas: {pages_empty_or_short}")
    print(f"Páginas com embedding_id: {pages_with_embedding}")

    # Sample extracted text preview
    cur.execute(
        """
        SELECT page_number, SUBSTR(REPLACE(REPLACE(gemini_text, CHAR(10), ' '), CHAR(13), ' '), 1, 180)
        FROM pages
        WHERE document_id=?
          AND gemini_text IS NOT NULL
          AND LENGTH(TRIM(gemini_text)) >= 20
        ORDER BY page_number ASC
        LIMIT 3
        """,
        (doc_id,),
    )
    previews = cur.fetchall()

    print("\nPrévia do texto extraído (3 páginas):")
    if previews:
        for pnum, txt in previews:
            print(f"  - Página {pnum}: {txt}...")
    else:
        print("  (sem texto útil encontrado)")

print("\n=== FIM ===")
conn.close()
