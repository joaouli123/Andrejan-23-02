import uuid
import logging
import re
from google import genai
from google.genai import types
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
)
from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

EMBEDDING_MODEL = "gemini-embedding-001"
VECTOR_SIZE = 768

client = genai.Client(api_key=settings.gemini_api_key)

FAULT_CODE_HINTS = {
    "UV", "OV", "OC", "OH", "OL", "FU", "MC", "DC", "PUV", "CUV", "EF", "GF",
}
FAULT_CODE_PATTERN = re.compile(r"\b[A-Z]{1,4}\d{0,3}\b")


def _contains_fault_code(text: str) -> bool:
    if not text:
        return False
    text_upper = text.upper()
    if any(hint in text_upper for hint in FAULT_CODE_HINTS):
        return True
    return bool(FAULT_CODE_PATTERN.search(text_upper))


def _extract_markdown_table_row_chunks(text: str, max_chunks: int = 5) -> list[str]:
    """Build chunks by logical table rows, preserving multi-line continuations."""
    lines = [line.rstrip() for line in text.splitlines() if line.strip()]
    table_lines = [line for line in lines if "|" in line]
    if len(table_lines) < 3:
        return []

    row_chunks: list[str] = []
    current_code = ""
    current_block: list[str] = []

    for line in table_lines:
        compact = line.strip()
        # Skip markdown separator rows
        if re.match(r"^\|?\s*[:\-]{2,}(\s*\|\s*[:\-]{2,})+\|?$", compact):
            continue

        cells = [cell.strip() for cell in compact.strip("|").split("|")]
        first_cell = cells[0] if cells else ""

        code_match = re.search(r"\b[A-Z]{1,4}\d{0,3}\b", first_cell.upper())
        starts_new_row = bool(code_match)

        if starts_new_row:
            if current_block:
                row_chunks.append("\n".join(current_block).strip())
            current_code = code_match.group(0) if code_match else ""
            current_block = [compact]
            continue

        # Continuation of the previous logical row
        if current_block:
            if current_code and first_cell == "":
                current_block.append(f"| {current_code} [continuação] | " + " | ".join(cells[1:]))
            else:
                current_block.append(compact)

    if current_block:
        row_chunks.append("\n".join(current_block).strip())

    deduped: list[str] = []
    seen: set[str] = set()
    for chunk in row_chunks:
        key = re.sub(r"\s+", " ", chunk).strip().lower()
        if len(chunk) < 40 or key in seen:
            continue
        seen.add(key)
        deduped.append(chunk)
        if len(deduped) >= max_chunks:
            break

    return deduped


def _build_contextual_chunks(text: str, max_chunks: int = 8) -> list[str]:
    """Create contextual chunks that preserve multi-line table rows."""
    normalized = text.strip()
    if not normalized:
        return []

    lines = [line.strip() for line in normalized.splitlines() if line.strip()]
    if len(lines) <= 8 and len(normalized) <= 1600:
        return [normalized]

    chunks: list[str] = []

    # Highest priority: logical row blocks for markdown tables.
    chunks.extend(_extract_markdown_table_row_chunks(normalized, max_chunks=4))

    # Prioritize windows around fault-code lines to avoid splitting key + description.
    for idx, line in enumerate(lines):
        if _contains_fault_code(line):
            start = max(0, idx - 1)
            end = min(len(lines), idx + 5)
            candidate = "\n".join(lines[start:end]).strip()
            if len(candidate) >= 60:
                chunks.append(candidate)

    # Add broader windows for general context.
    window_size = 12 if len(lines) > 35 else 9
    step = max(4, window_size - 3)
    for start in range(0, len(lines), step):
        end = min(len(lines), start + window_size)
        candidate = "\n".join(lines[start:end]).strip()
        if len(candidate) >= 120:
            chunks.append(candidate)
        if end >= len(lines):
            break

    deduped: list[str] = []
    seen: set[str] = set()
    for chunk in chunks:
        key = re.sub(r"\s+", " ", chunk).strip().lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(chunk)
        if len(deduped) >= max_chunks:
            break

    if not deduped:
        return [normalized]
    return deduped


def _extract_query_fault_tokens(query: str) -> list[str]:
    raw_tokens = re.findall(r"\b[a-zA-Z]{1,5}\d{0,3}\b", query.lower())
    tokens: list[str] = []
    for token in raw_tokens:
        token_upper = token.upper()
        if any(ch.isdigit() for ch in token_upper) or token_upper in FAULT_CODE_HINTS:
            tokens.append(token_upper)

    # dedupe preserving order
    unique: list[str] = []
    seen: set[str] = set()
    for token in tokens:
        if token not in seen:
            seen.add(token)
            unique.append(token)
    return unique


def _lexical_fault_bonus(text: str, tokens: list[str]) -> float:
    if not text or not tokens:
        return 0.0

    text_upper = text.upper()
    bonus = 0.0
    for token in tokens:
        if re.search(rf"\b{re.escape(token)}\b", text_upper):
            bonus += 0.08
        elif token in text_upper:
            bonus += 0.04
    return min(bonus, 0.24)


def get_qdrant_client() -> QdrantClient:
    return QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)


def ensure_collection(brand_slug: str):
    """Create Qdrant collection for a brand if it doesn't exist."""
    client = get_qdrant_client()
    collection_name = f"brand_{brand_slug}"

    existing = [c.name for c in client.get_collections().collections]
    if collection_name not in existing:
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
        )
        logger.info(f"Created Qdrant collection: {collection_name}")

    return collection_name


def get_embedding(text: str) -> list[float]:
    """Generate embedding using Gemini Embedding model."""
    result = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=[text],
        config=types.EmbedContentConfig(
            task_type="RETRIEVAL_DOCUMENT",
            output_dimensionality=VECTOR_SIZE,
        ),
    )
    return result.embeddings[0].values


def get_query_embedding(text: str) -> list[float]:
    """Generate embedding for query (different task type)."""
    result = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=[text],
        config=types.EmbedContentConfig(
            task_type="RETRIEVAL_QUERY",
            output_dimensionality=VECTOR_SIZE,
        ),
    )
    return result.embeddings[0].values


def upsert_page(
    brand_slug: str,
    doc_id: int,
    doc_filename: str,
    page_number: int,
    text: str,
) -> str:
    """
    Embed text and store in Qdrant.
    Returns the point ID (UUID string).
    """
    collection_name = ensure_collection(brand_slug)
    client = get_qdrant_client()

    chunks = _build_contextual_chunks(text)
    if not chunks:
        chunks = [text]

    points: list[PointStruct] = []
    point_ids: list[str] = []
    chunk_total = len(chunks)

    for index, chunk_text in enumerate(chunks):
        point_id = str(uuid.uuid4())
        embedding = get_embedding(chunk_text)
        points.append(
            PointStruct(
                id=point_id,
                vector=embedding,
                payload={
                    "brand_slug": brand_slug,
                    "doc_id": doc_id,
                    "doc_filename": doc_filename,
                    "page_number": page_number,
                    "text": chunk_text,
                    "chunk_index": index,
                    "chunk_total": chunk_total,
                },
            )
        )
        point_ids.append(point_id)

    client.upsert(collection_name=collection_name, points=points)
    return point_ids[0]


def search_brand(brand_slug: str, query: str, top_k: int = 7) -> list[dict]:
    """
    Semantic search within a brand's collection.
    Returns list of chunks with metadata.
    """
    collection_name = f"brand_{brand_slug}"
    client = get_qdrant_client()

    # Check collection exists
    existing = [c.name for c in client.get_collections().collections]
    if collection_name not in existing:
        return []

    query_vector = get_query_embedding(query)

    fault_tokens = _extract_query_fault_tokens(query)

    results = client.search(
        collection_name=collection_name,
        query_vector=query_vector,
        limit=max(top_k * 3, 12),
        with_payload=True,
        score_threshold=0.3,
    )

    chunks = []
    for hit in results:
        payload = hit.payload or {}
        payload_text = payload.get("text", "")
        boosted_score = hit.score + _lexical_fault_bonus(payload_text, fault_tokens)
        chunks.append({
            "text": payload_text,
            "source": payload.get("doc_filename", ""),
            "page": payload.get("page_number", 0),
            "doc_id": payload.get("doc_id", 0),
            "brand_slug": payload.get("brand_slug", ""),
            "score": boosted_score,
        })

    chunks.sort(key=lambda item: item["score"], reverse=True)
    return chunks[:top_k]


def delete_document_vectors(brand_slug: str, doc_id: int):
    """Remove all vectors for a specific document."""
    collection_name = f"brand_{brand_slug}"
    client = get_qdrant_client()

    client.delete(
        collection_name=collection_name,
        points_selector=Filter(
            must=[FieldCondition(key="doc_id", match=MatchValue(value=doc_id))]
        ),
    )
