import asyncio
import os
import re
import unicodedata
import uuid
import json
import logging
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import List, Optional

from database import get_db
from models import Brand, Document, Page, User, UserBrandAccess
from auth import get_current_admin, get_current_user
from ingestion.processor import process_document, get_job_progress
from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/admin", tags=["admin"])


# ── Brand routes ────────────────────────────────────────────────────────────

class BrandCreate(BaseModel):
    slug: str
    name: str
    description: Optional[str] = None


class BrandUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


@router.get("/brands")
async def list_brands(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.is_admin:
        result = await db.execute(select(Brand))
        brands = result.scalars().all()
    else:
        # Non-admin: only accessible brands
        ba_result = await db.execute(
            select(UserBrandAccess).where(UserBrandAccess.user_id == current_user.id)
        )
        brand_ids = [ba.brand_id for ba in ba_result.scalars().all()]
        result = await db.execute(select(Brand).where(Brand.id.in_(brand_ids)))
        brands = result.scalars().all()

    return [
        {
            "id": b.id,
            "slug": b.slug,
            "name": b.name,
            "description": b.description,
            "is_active": b.is_active,
        }
        for b in brands
    ]


@router.post("/brands", dependencies=[Depends(get_current_admin)])
async def create_brand(data: BrandCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Brand).where(Brand.slug == data.slug))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Slug já existe")

    brand = Brand(slug=data.slug, name=data.name, description=data.description)
    db.add(brand)
    await db.commit()
    await db.refresh(brand)
    return {"id": brand.id, "slug": brand.slug, "name": brand.name}


@router.put("/brands/{brand_id}", dependencies=[Depends(get_current_admin)])
async def update_brand(brand_id: int, data: BrandUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Brand).where(Brand.id == brand_id))
    brand = result.scalar_one_or_none()
    if not brand:
        raise HTTPException(status_code=404, detail="Marca não encontrada")

    if data.name is not None:
        brand.name = data.name
    if data.description is not None:
        brand.description = data.description
    if data.is_active is not None:
        brand.is_active = data.is_active

    await db.commit()
    return {"message": "Marca atualizada"}


# ── Document / Ingestion routes ─────────────────────────────────────────────

@router.get("/brands/{brand_id}/documents")
async def list_documents(
    brand_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Permission check
    if not current_user.is_admin:
        ba = await db.execute(
            select(UserBrandAccess).where(
                UserBrandAccess.user_id == current_user.id,
                UserBrandAccess.brand_id == brand_id,
            )
        )
        if not ba.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="Sem acesso a esta marca")

    result = await db.execute(
        select(Document).where(Document.brand_id == brand_id).order_by(Document.uploaded_at.desc())
    )
    docs = result.scalars().all()

    return [
        {
            "id": d.id,
            "filename": d.original_filename,
            "file_size": d.file_size or 0,
            "total_pages": d.total_pages,
            "processed_pages": d.processed_pages,
            "status": d.status,
            "error_message": d.error_message,
            "uploaded_at": d.uploaded_at.isoformat() if d.uploaded_at else None,
            "completed_at": d.completed_at.isoformat() if d.completed_at else None,
        }
        for d in docs
    ]


@router.post("/brands/{brand_id}/upload")
async def upload_documents(
    brand_id: int,
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Upload one or more PDFs for a brand and start ingestion."""
    result = await db.execute(select(Brand).where(Brand.id == brand_id))
    brand = result.scalar_one_or_none()
    if not brand:
        raise HTTPException(status_code=404, detail="Marca não encontrada")

    brand_upload_dir = Path(settings.upload_dir) / brand.slug
    brand_upload_dir.mkdir(parents=True, exist_ok=True)

    # Pre-load existing docs for this brand to check duplicates
    existing_result = await db.execute(
        select(Document).where(Document.brand_id == brand_id)
    )
    existing_docs = existing_result.scalars().all()
    existing_names = [
        _normalize_filename(doc.original_filename or "")
        for doc in existing_docs
        if doc.status in ("completed", "processing", "pending")
    ]

    jobs = []
    skipped = []
    for file in files:
        if not file.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail=f"{file.filename} não é um PDF")

        # ── Duplicate check (server-side) ──
        norm_name = _normalize_filename(file.filename)
        if _is_duplicate_of_any(norm_name, existing_names):
            logger.info(f"Arquivo duplicado ignorado: {file.filename} (já existe na marca {brand_id})")
            skipped.append(file.filename)
            continue

        # Save file
        safe_filename = f"{uuid.uuid4()}_{file.filename}"
        file_path = brand_upload_dir / safe_filename

        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)

        # Create document record
        doc = Document(
            brand_id=brand_id,
            filename=str(Path(brand.slug) / safe_filename),
            original_filename=file.filename,
            file_size=len(content),
            status="pending",
        )
        db.add(doc)
        await db.flush()

        # Track this name so subsequent files in same batch also deduplicate
        existing_names.append(norm_name)

        job_id = str(uuid.uuid4())

        # Store job_id in document for tracking
        doc.error_message = None
        await db.commit()
        await db.refresh(doc)

        # Start background processing
        background_tasks.add_task(
            _run_ingestion,
            doc_id=doc.id,
            brand_slug=brand.slug,
            job_id=job_id,
        )

        jobs.append({
            "doc_id": doc.id,
            "job_id": job_id,
            "filename": file.filename,
        })

    msg = f"{len(jobs)} arquivo(s) enviado(s)"
    if skipped:
        msg += f", {len(skipped)} ignorado(s) (duplicata)"
    return {"message": msg, "jobs": jobs, "skipped": skipped}


def _normalize_filename(name: str) -> str:
    """Normalize filename for duplicate comparison.
    Removes accents, UUID prefixes, special chars. Case-insensitive.
    'otis INSTALAÇÃO DO ACESSE CODE OTIS.pdf' -> 'instalacao do acesse code otis'
    """
    # Remove .pdf extension
    name = re.sub(r'\.pdf$', '', name.strip(), flags=re.IGNORECASE)
    # Remove UUID prefix (8-4-4-4-12 hex pattern)
    name = re.sub(r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}_', '', name)
    # Remove accents
    nfkd = unicodedata.normalize('NFKD', name)
    name = ''.join(c for c in nfkd if not unicodedata.combining(c))
    # Lowercase
    name = name.lower()
    # Remove special chars, keep only letters, digits, spaces
    name = re.sub(r'[^a-z0-9\s]', ' ', name)
    # Collapse whitespace
    name = re.sub(r'\s+', ' ', name).strip()
    return name


def _is_duplicate_of_any(new_name: str, existing_names: list) -> bool:
    """Check if new_name is a duplicate of any existing name.
    Uses exact normalized match only (safe, no false positives).
    """
    if not new_name:
        return False
    for existing in existing_names:
        if existing and new_name == existing:
            return True
    return False


async def _run_ingestion(doc_id: int, brand_slug: str, job_id: str):
    """Run ingestion in background task with its own DB session."""
    from database import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        await process_document(db, doc_id, brand_slug, job_id)


@router.get("/jobs/{job_id}/status")
async def job_status(job_id: str, _: User = Depends(get_current_user)):
    """Get real-time progress of an ingestion job."""
    progress = get_job_progress(job_id)
    return progress


@router.get("/jobs/{job_id}/stream")
async def job_stream(job_id: str, _: User = Depends(get_current_user)):
    """SSE stream for real-time ingestion progress."""
    async def event_generator():
        import asyncio
        prev = None
        timeout = 0
        while timeout < 600:  # max 10 min per job
            progress = get_job_progress(job_id)
            if progress != prev:
                yield f"data: {json.dumps(progress)}\n\n"
                prev = progress.copy()

            if progress.get("status") in ("completed", "completed_with_errors", "error"):
                break

            await asyncio.sleep(1)
            timeout += 1

        yield f"data: {json.dumps({'status': 'stream_ended'})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.delete("/documents/{doc_id}", dependencies=[Depends(get_current_admin)])
async def delete_document(doc_id: int, db: AsyncSession = Depends(get_db)):
    """Delete document and its vectors from Qdrant."""
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Documento não encontrado")

    # Get brand slug
    brand_result = await db.execute(select(Brand).where(Brand.id == doc.brand_id))
    brand = brand_result.scalar_one_or_none()

    # Delete from Qdrant
    if brand:
        try:
            from ingestion.embedder import delete_document_vectors
            delete_document_vectors(brand.slug, doc_id)
        except Exception as e:
            logger.warning(f"Could not delete vectors for doc {doc_id}: {e}")

    # Delete file
    file_path = Path(settings.upload_dir) / doc.filename
    if file_path.exists():
        file_path.unlink()

    await db.delete(doc)
    await db.commit()
    return {"message": "Documento removido"}


@router.post("/documents/{doc_id}/reprocess", dependencies=[Depends(get_current_admin)])
async def reprocess_document(
    doc_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Re-run ingestion on an existing document (useful for low-quality pages)."""
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Documento não encontrado")

    if doc.status == "processing":
        raise HTTPException(status_code=409, detail="Este documento já está em processamento")

    brand_result = await db.execute(select(Brand).where(Brand.id == doc.brand_id))
    brand = brand_result.scalar_one_or_none()

    # Full reprocess: remove previous vectors and page records for this document
    try:
        from ingestion.embedder import delete_document_vectors
        delete_document_vectors(brand.slug, doc_id)
    except Exception as e:
        logger.warning(f"Could not delete previous vectors for doc {doc_id}: {e}")

    pages_result = await db.execute(select(Page).where(Page.document_id == doc_id))
    old_pages = pages_result.scalars().all()
    for p in old_pages:
        await db.delete(p)

    job_id = str(uuid.uuid4())
    doc.status = "pending"
    doc.processed_pages = 0
    doc.total_pages = 0
    doc.completed_at = None
    doc.error_message = None
    await db.commit()

    background_tasks.add_task(
        _run_ingestion,
        doc_id=doc_id,
        brand_slug=brand.slug,
        job_id=job_id,
    )

    return {"job_id": job_id, "message": "Reprocessamento iniciado"}
