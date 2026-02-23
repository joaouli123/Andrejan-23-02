import asyncio
import logging
import time
from datetime import datetime
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models import Document, Page
from ingestion.gemini_vision import (
    GeminiQuotaExceededError,
    extract_page_from_pdf,
    upload_pdf_to_gemini,
    delete_gemini_file,
)
from ingestion.open_source_vision import extract_page_open_source
from ingestion.embedder import upsert_page, ensure_collection
from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()
PROVIDER_GEMINI = "gemini"
PROVIDER_OPEN_SOURCE = "open_source"

# In-memory job progress tracker
_job_progress: dict[str, dict] = {}
_active_docs: set[int] = set()


def get_job_progress(job_id: str) -> dict:
    return _job_progress.get(job_id, {"status": "not_found"})


def _get_pdf_page_count(pdf_path: str) -> int:
    """Get total number of pages in a PDF using pypdf (pure Python, no system deps)."""
    import pypdf
    with open(pdf_path, "rb") as f:
        reader = pypdf.PdfReader(f)
        return len(reader.pages)


async def process_document(
    db: AsyncSession,
    doc_id: int,
    brand_slug: str,
    job_id: str,
):
    """
    Full ingestion pipeline for a single document:
    1. Upload PDF directly to Gemini File API (no image conversion!)
    2. Gemini reads each page natively from the PDF
    3. embed + store in Qdrant
    4. update DB
    """
    started_at = time.time()
    _job_progress[job_id] = {
        "status": "starting",
        "processed": 0,
        "total": 0,
        "errors": [],
        "started_at": started_at,
        "updated_at": started_at,
        "eta_seconds": None,
    }
    uploaded_file = None

    if doc_id in _active_docs:
        _job_progress[job_id]["status"] = "error"
        _job_progress[job_id]["errors"].append("Documento já está em processamento")
        _job_progress[job_id]["updated_at"] = time.time()
        return

    _active_docs.add(doc_id)

    try:
        # Load document from DB
        result = await db.execute(select(Document).where(Document.id == doc_id))
        doc = result.scalar_one_or_none()
        if not doc:
            _job_progress[job_id]["status"] = "error"
            _job_progress[job_id]["errors"].append(f"Document {doc_id} not found")
            _job_progress[job_id]["updated_at"] = time.time()
            return

        doc.status = "processing"
        await db.commit()

        pdf_path = str(Path(settings.upload_dir) / doc.filename)

        # Ensure Qdrant collection exists
        ensure_collection(brand_slug)

        # Get page count (fast, pure Python)
        _job_progress[job_id]["status"] = "reading_pdf"
        _job_progress[job_id]["updated_at"] = time.time()
        logger.info(f"Reading PDF page count: {pdf_path}")
        total = _get_pdf_page_count(pdf_path)
        doc.total_pages = total
        await db.commit()

        _job_progress[job_id]["total"] = total
        _job_progress[job_id]["updated_at"] = time.time()
        logger.info(f"PDF has {total} pages: {doc.original_filename}")

        provider = (settings.ingestion_provider or PROVIDER_GEMINI).strip().lower()
        if provider not in (PROVIDER_GEMINI, PROVIDER_OPEN_SOURCE):
            raise RuntimeError(
                f"INGESTION_PROVIDER inválido: {settings.ingestion_provider}. Use gemini ou open_source"
            )

        if provider == PROVIDER_GEMINI:
            _job_progress[job_id]["status"] = "uploading_to_gemini"
            _job_progress[job_id]["updated_at"] = time.time()
            logger.info("Uploading PDF to Gemini File API...")
            uploaded_file = upload_pdf_to_gemini(pdf_path)
        else:
            _job_progress[job_id]["status"] = "preparing_open_source"
            _job_progress[job_id]["updated_at"] = time.time()
            logger.info(
                "Using open-source extraction provider via Ollama model %s",
                settings.ollama_model,
            )

        _job_progress[job_id]["status"] = "processing_pages"
        _job_progress[job_id]["updated_at"] = time.time()

        # Checkpoint: skip pages already processed (safe resume)
        pages_result = await db.execute(select(Page).where(Page.document_id == doc_id))
        existing_pages = {p.page_number: p for p in pages_result.scalars().all()}
        completed_pages = {
            page_number
            for page_number, page_obj in existing_pages.items()
            if page_obj.gemini_text and page_obj.embedding_id
        }

        processed = len(completed_pages)
        errors = []

        doc.processed_pages = processed
        await db.commit()
        _job_progress[job_id]["processed"] = processed
        _job_progress[job_id]["updated_at"] = time.time()

        pages_to_process = [p for p in range(1, total + 1) if p not in completed_pages]

        for page_number in pages_to_process:
            try:
                logger.info(f"Processing page {page_number}/{total} of {doc.original_filename}")

                if provider == PROVIDER_GEMINI:
                    text, quality_score = await extract_page_from_pdf(
                        uploaded_file,
                        page_number,
                        pdf_path=pdf_path,
                    )
                else:
                    text, quality_score = await extract_page_open_source(
                        pdf_path=pdf_path,
                        page_number=page_number,
                    )

                embedding_id = upsert_page(
                    brand_slug=brand_slug,
                    doc_id=doc_id,
                    doc_filename=doc.original_filename,
                    page_number=page_number,
                    text=text,
                )
            except GeminiQuotaExceededError as quota_error:
                await db.rollback()
                error_msg = (
                    "Limite da API Gemini excedido (429 RESOURCE_EXHAUSTED). "
                    "Aguarde alguns minutos ou use uma chave com mais quota e tente novamente."
                )
                logger.error(f"Page {page_number}: {quota_error}")
                errors.append(error_msg)
                _job_progress[job_id]["errors"] = errors
                _job_progress[job_id]["updated_at"] = time.time()
                break
            except Exception as e:
                await db.rollback()
                error_msg = f"Page {page_number}: {e}"
                logger.error(error_msg)
                errors.append(error_msg)
                _job_progress[job_id]["errors"] = errors
                _job_progress[job_id]["updated_at"] = time.time()
                continue

            page_obj = existing_pages.get(page_number)
            if page_obj:
                page_obj.gemini_text = text
                page_obj.embedding_id = embedding_id
                page_obj.quality_score = quality_score
                page_obj.processed_at = datetime.utcnow()
            else:
                page_obj = Page(
                    document_id=doc_id,
                    page_number=page_number,
                    gemini_text=text,
                    embedding_id=embedding_id,
                    quality_score=quality_score,
                    processed_at=datetime.utcnow(),
                )
                db.add(page_obj)
                existing_pages[page_number] = page_obj

            processed += 1
            doc.processed_pages = processed
            await db.commit()
            _job_progress[job_id]["processed"] = processed
            _job_progress[job_id]["updated_at"] = time.time()

            elapsed = max(0.001, time.time() - started_at)
            if total > processed and processed > 0:
                rate = processed / elapsed
                _job_progress[job_id]["eta_seconds"] = int(max(0, (total - processed) / max(rate, 1e-6)))
            else:
                _job_progress[job_id]["eta_seconds"] = 0

            page_delay = max(0.0, float(settings.ingestion_page_delay_seconds or 0.0))
            if page_delay > 0 and page_number != pages_to_process[-1]:
                logger.info("Page delay enabled: sleeping %.2fs", page_delay)
                _job_progress[job_id]["status"] = "cooldown_between_pages"
                _job_progress[job_id]["updated_at"] = time.time()
                await asyncio.sleep(page_delay)
                _job_progress[job_id]["status"] = "processing_pages"
                _job_progress[job_id]["updated_at"] = time.time()

        # Final status
        if errors and processed == 0:
            doc.status = "error"
            doc.error_message = "; ".join(errors[:5])
        elif errors:
            doc.status = "completed_with_errors"
            doc.error_message = f"{len(errors)} páginas com erro"
        else:
            doc.status = "completed"

        doc.completed_at = datetime.utcnow()
        await db.commit()

        _job_progress[job_id]["status"] = doc.status
        _job_progress[job_id]["processed"] = processed
        _job_progress[job_id]["updated_at"] = time.time()
        _job_progress[job_id]["eta_seconds"] = 0
        logger.info(f"Document {doc_id} processed: {processed}/{total} pages")

    except Exception as e:
        logger.error(f"Fatal error processing doc {doc_id}: {e}")
        await db.rollback()
        _job_progress[job_id]["status"] = "error"
        _job_progress[job_id]["errors"].append(str(e))
        _job_progress[job_id]["updated_at"] = time.time()

        result = await db.execute(select(Document).where(Document.id == doc_id))
        doc = result.scalar_one_or_none()
        if doc:
            doc.status = "error"
            doc.error_message = str(e)
            await db.commit()

    finally:
        # Always clean up the uploaded file from Gemini
        if uploaded_file:
            delete_gemini_file(uploaded_file)
        _active_docs.discard(doc_id)
