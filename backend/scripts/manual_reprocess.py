import asyncio
import sys
import uuid
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from sqlalchemy import select

from database import AsyncSessionLocal
from models import Document, Brand, Page
from ingestion.embedder import delete_document_vectors
from ingestion.processor import process_document


async def run(doc_id: int):
    async with AsyncSessionLocal() as db:
        doc_result = await db.execute(select(Document).where(Document.id == doc_id))
        doc = doc_result.scalar_one_or_none()
        if not doc:
            raise RuntimeError(f"Documento {doc_id} não encontrado")

        brand_result = await db.execute(select(Brand).where(Brand.id == doc.brand_id))
        brand = brand_result.scalar_one_or_none()
        if not brand:
            raise RuntimeError(f"Marca do documento {doc_id} não encontrada")

        try:
            delete_document_vectors(brand.slug, doc_id)
        except Exception:
            pass

        pages_result = await db.execute(select(Page).where(Page.document_id == doc_id))
        for page in pages_result.scalars().all():
            await db.delete(page)

        doc.status = "pending"
        doc.processed_pages = 0
        doc.total_pages = 0
        doc.completed_at = None
        doc.error_message = None
        await db.commit()

        job_id = str(uuid.uuid4())
        print(f"job_id={job_id}")
        await process_document(db=db, doc_id=doc_id, brand_slug=brand.slug, job_id=job_id)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("Uso: python scripts/manual_reprocess.py <doc_id>")
    asyncio.run(run(int(sys.argv[1])))
