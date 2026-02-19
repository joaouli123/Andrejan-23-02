import asyncio
import sys
sys.path.insert(0, '/app')
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


async def main():
    engine = create_async_engine('sqlite+aiosqlite:////app/data/andreja.db')
    async with engine.connect() as conn:
        docs = await conn.execute(text("SELECT id, original_filename FROM documents ORDER BY id"))
        print('DOCS:')
        for row in docs.fetchall():
            print(row)

        print('\nMAG PAGES 49-54:')
        result = await conn.execute(text("""
            SELECT p.page_number,
                   LENGTH(p.gemini_text) AS len_text,
                   SUBSTR(p.gemini_text, 1, 700) AS snippet
            FROM pages p
            JOIN documents d ON p.document_id = d.id
            WHERE d.original_filename LIKE '%Mag completo%'
              AND p.page_number IN (49,50,51,52,53,54)
            ORDER BY p.page_number
        """))

        rows = result.fetchall()
        for page_number, length, snippet in rows:
            print(f"\nPAGE {page_number} | LEN {length}")
            print((snippet or '').replace('\n', ' '))

        print('\nEXACT SEARCH UV3/UV1 in Mag pages:')
        exact = await conn.execute(text("""
            SELECT p.page_number,
                   CASE WHEN LOWER(p.gemini_text) LIKE '%uv3%' THEN 1 ELSE 0 END AS has_uv3,
                   CASE WHEN LOWER(p.gemini_text) LIKE '%uv1%' THEN 1 ELSE 0 END AS has_uv1,
                   CASE WHEN LOWER(p.gemini_text) LIKE '%dc bus undervolt%' THEN 1 ELSE 0 END AS has_dc_bus
            FROM pages p
            JOIN documents d ON p.document_id = d.id
            WHERE d.original_filename LIKE '%Mag completo%'
              AND p.page_number BETWEEN 45 AND 60
            ORDER BY p.page_number
        """))
        for row in exact.fetchall():
            print(row)

    await engine.dispose()


asyncio.run(main())
