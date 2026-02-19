import asyncio
import sys
sys.path.insert(0, '/app')

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from config import get_settings
from ingestion.gemini_vision import upload_pdf_to_gemini, extract_page_from_pdf, delete_gemini_file


async def main():
    settings = get_settings()
    engine = create_async_engine('sqlite+aiosqlite:////app/data/andreja.db')

    async with engine.connect() as conn:
        result = await conn.execute(text("""
            SELECT filename, original_filename
            FROM documents
            WHERE original_filename LIKE '%Mag completo%'
            ORDER BY id DESC
            LIMIT 1
        """))
        row = result.fetchone()
        if not row:
            print('Mag completo.pdf not found in documents')
            return

        rel_filename, original_filename = row
        pdf_path = f"{settings.upload_dir}/{rel_filename}"
        print('Testing:', original_filename)
        print('Path:', pdf_path)

    uploaded = None
    try:
        uploaded = upload_pdf_to_gemini(pdf_path)
        extracted_text, score = await extract_page_from_pdf(uploaded, 50, pdf_path=pdf_path)
        print('\n=== PAGE 50 RESULT (first 1800 chars) ===')
        print(extracted_text[:1800])
        lower = extracted_text.lower()
        print('\ncontains UV3?', 'uv3' in lower)
        print('contains UV1?', 'uv1' in lower)
        print('contains DC Bus Undervolt?', 'dc bus undervolt' in lower)
        print('quality score:', score)
    finally:
        if uploaded:
            delete_gemini_file(uploaded)
        await engine.dispose()


asyncio.run(main())
