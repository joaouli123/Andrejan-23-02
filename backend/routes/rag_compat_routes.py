import time
import logging
from typing import Optional
import re
import unicodedata
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from agent.chat import chat
from config import get_settings
from database import get_db, AsyncSessionLocal
from ingestion.processor import process_document, get_job_progress
from models import Brand, Document, Page, User


router = APIRouter(prefix="/api", tags=["rag-compat"])
settings = get_settings()
logger = logging.getLogger(__name__)


class QueryRequest(BaseModel):
    question: str
    systemInstruction: Optional[str] = None
    topK: Optional[int] = 10
    brandFilter: Optional[str] = None
    conversationHistory: Optional[list] = None


class CompatBrandCreate(BaseModel):
    name: str


class CompatBrandUpdate(BaseModel):
    name: Optional[str] = None
    is_active: Optional[bool] = None


class DuplicateCheckRequest(BaseModel):
    fileNames: list[str]
    brandId: Optional[str] = None


def _normalize(value: Optional[str]) -> str:
    return (value or "").strip().lower()


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", _normalize(name))
    return slug.strip("-") or "brand"


@router.get("/health")
async def rag_health():
    return {"ok": True, "loading": False, "service": "andreja-rag-compat"}


@router.get("/stats")
async def rag_stats(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(func.count(Document.id)))
    total_documents = int(result.scalar() or 0)
    return {"totalDocuments": total_documents}


@router.get("/brands")
async def compat_list_brands(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Brand).where(Brand.is_active.is_(True)).order_by(Brand.name))
    brands = result.scalars().all()
    return [{"id": str(b.id), "name": b.name, "slug": b.slug} for b in brands]


@router.post("/brands")
async def compat_create_brand(data: CompatBrandCreate, db: AsyncSession = Depends(get_db)):
    name = (data.name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Nome da marca é obrigatório")

    existing_name = await db.execute(select(Brand).where(func.lower(Brand.name) == name.lower()))
    if existing_name.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Marca já existe")

    base_slug = _slugify(name)
    slug = base_slug
    suffix = 2
    while True:
        existing_slug = await db.execute(select(Brand).where(Brand.slug == slug))
        if not existing_slug.scalar_one_or_none():
            break
        slug = f"{base_slug}-{suffix}"
        suffix += 1

    brand = Brand(slug=slug, name=name, is_active=True)
    db.add(brand)
    await db.commit()
    await db.refresh(brand)
    return {"id": str(brand.id), "name": brand.name, "slug": brand.slug}


@router.patch("/brands/{brand_id}")
async def compat_update_brand(brand_id: str, data: CompatBrandUpdate, db: AsyncSession = Depends(get_db)):
    if not str(brand_id).isdigit():
        raise HTTPException(status_code=400, detail="ID inválido")

    result = await db.execute(select(Brand).where(Brand.id == int(brand_id)))
    brand = result.scalar_one_or_none()
    if not brand:
        raise HTTPException(status_code=404, detail="Marca não encontrada")

    if data.name is not None and data.name.strip():
        brand.name = data.name.strip()
    if data.is_active is not None:
        brand.is_active = data.is_active

    await db.commit()
    return {"id": str(brand.id), "name": brand.name, "slug": brand.slug, "is_active": brand.is_active}


@router.delete("/brands/{brand_id}")
async def compat_delete_brand(brand_id: str, db: AsyncSession = Depends(get_db)):
    if not str(brand_id).isdigit():
        raise HTTPException(status_code=400, detail="ID inválido")

    result = await db.execute(select(Brand).where(Brand.id == int(brand_id)))
    brand = result.scalar_one_or_none()
    if not brand:
        raise HTTPException(status_code=404, detail="Marca não encontrada")

    brand.is_active = False
    await db.commit()
    return {"ok": True}


@router.get("/brands/{brand_id}/documents")
async def compat_brand_documents(brand_id: str, db: AsyncSession = Depends(get_db)):
    if not str(brand_id).isdigit():
        raise HTTPException(status_code=400, detail="ID inválido")

    result = await db.execute(
        select(Document)
        .where(Document.brand_id == int(brand_id))
        .order_by(Document.uploaded_at.desc())
    )
    docs = result.scalars().all()

    return [
        {
            "id": str(d.id),
            "brand_id": str(d.brand_id),
            "title": d.original_filename.rsplit(".", 1)[0],
            "filename": d.original_filename,
            "status": "indexed" if d.status in ("completed", "completed_with_errors") else d.status,
            "processed_pages": d.processed_pages,
            "total_pages": d.total_pages,
            "file_size": d.file_size or 0,
            "created_at": d.uploaded_at.isoformat() if d.uploaded_at else None,
        }
        for d in docs
    ]


@router.delete("/documents/{doc_id}")
async def compat_delete_document(doc_id: str, db: AsyncSession = Depends(get_db)):
    if not str(doc_id).isdigit():
        raise HTTPException(status_code=400, detail="ID inválido")

    doc_id_int = int(doc_id)
    result = await db.execute(select(Document).where(Document.id == doc_id_int))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Documento não encontrado")

    brand_result = await db.execute(select(Brand).where(Brand.id == doc.brand_id))
    brand = brand_result.scalar_one_or_none()

    if brand:
        try:
            from ingestion.embedder import delete_document_vectors
            delete_document_vectors(brand.slug, doc_id_int)
        except Exception:
            pass

    pages_result = await db.execute(select(Page).where(Page.document_id == doc_id_int))
    for page in pages_result.scalars().all():
        await db.delete(page)

    file_path = Path(settings.upload_dir) / doc.filename
    if file_path.exists():
        file_path.unlink()

    await db.delete(doc)
    await db.commit()
    return {"ok": True, "message": "Documento removido"}


@router.post("/check-duplicates")
async def compat_check_duplicates(payload: DuplicateCheckRequest, db: AsyncSession = Depends(get_db)):
    names = [str(name or "").strip() for name in payload.fileNames if str(name or "").strip()]
    if not names:
        return {"duplicates": []}

    normalized_input = {n: _normalize_filename(n) for n in names}

    stmt = select(Document)
    if payload.brandId and str(payload.brandId).isdigit():
        stmt = stmt.where(Document.brand_id == int(payload.brandId))

    result = await db.execute(stmt)
    docs = result.scalars().all()

    existing_normalized = [
        _normalize_filename(doc.original_filename or "")
        for doc in docs
        if doc.status in ("completed", "processing", "pending")
    ]

    duplicates: list[str] = []
    for original_name, norm in normalized_input.items():
        if _is_duplicate_of_any(norm, existing_normalized):
            duplicates.append(original_name)

    return {"duplicates": sorted(set(duplicates), key=str.lower)}


async def _run_ingestion_bg(doc_id: int, brand_slug: str, job_id: str):
    async with AsyncSessionLocal() as session:
        await process_document(session, doc_id, brand_slug, job_id)


@router.post("/brands/{brand_id}/upload")
async def compat_upload_brand_document(
    brand_id: str,
    background_tasks: BackgroundTasks,
    pdf: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    if not str(brand_id).isdigit():
        raise HTTPException(status_code=400, detail="ID inválido")
    if not str(pdf.filename or "").lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Apenas PDF é permitido")

    brand_result = await db.execute(select(Brand).where(Brand.id == int(brand_id), Brand.is_active.is_(True)))
    brand = brand_result.scalar_one_or_none()
    if not brand:
        raise HTTPException(status_code=404, detail="Marca não encontrada")

    brand_upload_dir = Path(settings.upload_dir) / brand.slug
    brand_upload_dir.mkdir(parents=True, exist_ok=True)

    # ── Server-side duplicate check ──
    norm_new = _normalize_filename(pdf.filename)
    existing_result = await db.execute(
        select(Document).where(
            Document.brand_id == int(brand_id),
            Document.status.in_(["completed", "processing", "pending"])
        )
    )
    existing_docs = existing_result.scalars().all()
    for edoc in existing_docs:
        existing_norm = _normalize_filename(edoc.original_filename or "")
        if _is_duplicate_of_any(norm_new, [existing_norm]):
            logger.info(f"Duplicata bloqueada: '{pdf.filename}' já existe como '{edoc.original_filename}' (doc_id={edoc.id})")
            return {
                "skipped": True,
                "reason": f"Arquivo já indexado como '{edoc.original_filename}'",
                "existing_doc_id": str(edoc.id),
                "filename": pdf.filename
            }

    safe_filename = f"{uuid.uuid4()}_{pdf.filename}"
    content = await pdf.read()
    file_path = brand_upload_dir / safe_filename
    with open(file_path, "wb") as file_handler:
        file_handler.write(content)

    document = Document(
        brand_id=brand.id,
        filename=str(Path(brand.slug) / safe_filename),
        original_filename=pdf.filename,
        status="pending",
    )
    db.add(document)
    await db.commit()
    await db.refresh(document)

    job_id = str(uuid.uuid4())
    background_tasks.add_task(_run_ingestion_bg, document.id, brand.slug, job_id)

    return {"job_id": job_id, "doc_id": str(document.id), "filename": document.original_filename}


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


@router.get("/upload/status/{job_id}")
async def compat_upload_status(job_id: str):
    progress = get_job_progress(job_id)
    status = progress.get("status", "not_found")
    processed = int(progress.get("processed", 0) or 0)
    total = int(progress.get("total", 0) or 0)
    errors = progress.get("errors", []) or []
    started_at = progress.get("started_at")
    eta_seconds = progress.get("eta_seconds")
    elapsed_seconds = int(max(0, time.time() - started_at)) if isinstance(started_at, (int, float)) else 0
    stage = str(status or "")

    if status in ("completed", "completed_with_errors"):
        return {
            "status": "done",
            "message": "Processamento concluído",
            "pages": processed,
            "chunks": processed,
            "progress": 100,
            "stage": stage,
            "elapsed_seconds": elapsed_seconds,
            "eta_seconds": 0,
        }

    if status in ("error", "failed"):
        return {
            "status": "error",
            "message": "; ".join(errors) if errors else "Erro no processamento",
            "pages": processed,
            "chunks": processed,
            "progress": 100 if total and processed >= total else 0,
            "stage": stage,
            "elapsed_seconds": elapsed_seconds,
            "eta_seconds": eta_seconds if isinstance(eta_seconds, int) else None,
        }

    if status == "not_found":
        return {
            "status": "not_found",
            "message": "Job não encontrado",
            "progress": 0,
            "stage": stage,
            "elapsed_seconds": 0,
            "eta_seconds": None,
        }

    progress_pct = int((processed / total) * 100) if total > 0 else 0
    return {
        "status": "processing",
        "message": f"Processando {processed}/{total}" if total else "Iniciando...",
        "pages": processed,
        "chunks": processed,
        "progress": progress_pct,
        "stage": stage,
        "elapsed_seconds": elapsed_seconds,
        "eta_seconds": eta_seconds if isinstance(eta_seconds, int) else None,
    }


@router.post("/query")
async def rag_query(request: QueryRequest, db: AsyncSession = Depends(get_db)):
    question = (request.question or "").strip()
    if not question:
        raise HTTPException(status_code=400, detail="Pergunta vazia")

    started = time.time()

    admin_result = await db.execute(
        select(User).where(User.is_admin.is_(True), User.is_active.is_(True)).order_by(User.id)
    )
    admin_user = admin_result.scalars().first()
    if not admin_user:
        raise HTTPException(status_code=500, detail="Usuário admin não encontrado")

    brand: Optional[Brand] = None
    brand_filter = _normalize(request.brandFilter)

    if brand_filter:
        brands_result = await db.execute(select(Brand).where(Brand.is_active.is_(True)))
        brands = brands_result.scalars().all()

        for candidate in brands:
            if _normalize(candidate.name) == brand_filter or _normalize(candidate.slug) == brand_filter:
                brand = candidate
                break

        if not brand:
            for candidate in brands:
                if brand_filter in _normalize(candidate.name) or brand_filter in _normalize(candidate.slug):
                    brand = candidate
                    break

    if not brand:
        fallback_result = await db.execute(
            select(Brand).where(Brand.is_active.is_(True)).order_by(Brand.id)
        )
        brand = fallback_result.scalars().first()

    if not brand:
        raise HTTPException(status_code=404, detail="Nenhuma marca ativa encontrada")

    response = await chat(
        db=db,
        user_id=admin_user.id,
        brand_id=brand.id,
        brand_slug=brand.slug,
        brand_name=brand.name,
        query=question,
        session_id=None,
    )

    answer = response.get("answer", "")
    sources = response.get("sources", [])
    elapsed = int((time.time() - started) * 1000)

    return {
        "answer": answer,
        "sources": sources,
        "documentsFound": len(sources),
        "searchTime": elapsed,
    }
