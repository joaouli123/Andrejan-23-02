import uuid
import logging
import re
import sqlite3
import httpx
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

# Conditional import for text search support
try:
    from qdrant_client.models import MatchText
    HAS_MATCH_TEXT = True
except ImportError:
    HAS_MATCH_TEXT = False

logger = logging.getLogger(__name__)
settings = get_settings()

EMBEDDING_MODEL = "gemini-embedding-001"
VECTOR_SIZE = settings.embedding_vector_size
PROVIDER_GEMINI = "gemini"
PROVIDER_OPEN_SOURCE = "open_source"

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
    if len(normalized) <= 2000:
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


def _normalize_for_matching(text: str) -> str:
    """
    Normalize text for fuzzy matching:
    - lowercase
    - remove accents (ã→a, ç→c, é→e)
    - remove dots, dashes, underscores, special chars
    - collapse spaces
    Example: "ATC - C.07.10" → "atc c0710"
             "Calibração do OVF10" → "calibracao do ovf10"
    """
    import unicodedata
    t = text.lower()
    # Remove accents
    t = unicodedata.normalize("NFD", t)
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    # Remove dots, dashes, underscores
    t = re.sub(r"[.\-_/\\]", " ", t)
    # Remove non-alphanumeric except spaces
    t = re.sub(r"[^a-z0-9 ]", "", t)
    # Collapse multiple spaces
    t = re.sub(r"\s+", " ", t).strip()
    return t


def _extract_key_tokens(text: str) -> list[str]:
    """
    Extract meaningful tokens for matching from a query or filename.
    Focuses on model codes, numbers, and significant words.
    Returns normalized tokens.
    """
    normalized = _normalize_for_matching(text)
    tokens = []
    for word in normalized.split():
        # Skip very common words
        if word in {"de", "do", "da", "dos", "das", "um", "uma", "o", "a",
                     "os", "as", "e", "ou", "em", "no", "na", "nos", "nas",
                     "com", "para", "por", "se", "que", "pdf", "otis"}:
            continue
        if len(word) >= 2:
            tokens.append(word)
    return tokens


def _extract_search_keywords(query: str) -> list[str]:
    """
    Extract important keywords from a query for exact-text content search.
    Focuses on model codes, alphanumeric identifiers, and technical terms
    that should be searched literally in document content.

    Examples:
        "Falhas no XO 508" → ["XO 508", "XO508"]
        "calibração OVF10" → ["OVF10"]
        "placa LCB2" → ["LCB2"]
        "diagrama ATC C.07.10" → ["ATC", "C.07.10", "C0710"]
    """
    import unicodedata
    q = query.strip()
    words = q.split()

    keywords = []

    # 1. Find individual model codes: alphanumeric with letters+digits (OVF10, LCB2, GEN2)
    for word in words:
        clean = re.sub(r'[().,;:!?]', '', word).strip()
        if not clean or len(clean) < 2:
            continue
        # Alphanumeric codes with mixed letters+digits
        if (re.match(r'^[A-Za-z]+\d+', clean) or
            re.match(r'^\d+[A-Za-z]+', clean)):
            keywords.append(clean)
        # Pure uppercase model names (3+ chars): ATC, CVF, ADV, MRL
        elif re.match(r'^[A-Z]{3,}$', clean):
            keywords.append(clean)
        # Dotted codes: C.07.10, B.03.05
        elif re.match(r'^[A-Za-z]?\.?\d+\.\d+', clean):
            keywords.append(clean)
            # Also add version without dots
            nodots = clean.replace('.', '')
            if nodots != clean:
                keywords.append(nodots)

    # 2. Combine adjacent words that form a model name: "XO 508" → "XO 508" and "XO508"
    for i in range(len(words) - 1):
        w1 = re.sub(r'[().,;:!?]', '', words[i]).strip()
        w2 = re.sub(r'[().,;:!?]', '', words[i + 1]).strip()
        if not w1 or not w2:
            continue
        # Pattern: letters + number ("XO 508", "ADV 210", "DO 2000")
        if (re.match(r'^[A-Za-z]{1,5}$', w1) and re.match(r'^\d{2,5}$', w2)):
            keywords.append(f"{w1} {w2}")
            keywords.append(f"{w1}{w2}")  # combined version
        # Pattern: letters + alphanumeric ("ADV Total")
        elif (re.match(r'^[A-Za-z]{2,5}$', w1) and
              re.match(r'^[A-Za-z0-9]{2,}$', w2) and
              w1.upper() not in {'DE', 'DO', 'DA', 'NO', 'NA', 'EM', 'POR', 'PARA', 'COM',
                                  'OS', 'AS', 'UM', 'UMA', 'QUE', 'SEM', 'NOS', 'NAS'}):
            keywords.append(f"{w1} {w2}")

    # 3. Three-word combinations: "ADV Total 2", "DO 2000 Gearless"
    for i in range(len(words) - 2):
        w1 = re.sub(r'[().,;:!?]', '', words[i]).strip()
        w2 = re.sub(r'[().,;:!?]', '', words[i + 1]).strip()
        w3 = re.sub(r'[().,;:!?]', '', words[i + 2]).strip()
        if not w1 or not w2 or not w3:
            continue
        if (re.match(r'^[A-Za-z]{2,5}$', w1) and
            w1.upper() not in {'DE', 'DO', 'DA', 'NO', 'NA', 'EM', 'POR', 'PARA', 'COM',
                                'OS', 'AS', 'UM', 'UMA', 'QUE', 'SEM', 'NOS', 'NAS'}):
            keywords.append(f"{w1} {w2} {w3}")

    # Dedupe preserving order
    seen = set()
    unique = []
    for k in keywords:
        kl = k.lower().strip()
        if kl and kl not in seen and len(kl) >= 2:
            seen.add(kl)
            unique.append(k)

    return unique


def _db_keyword_search(keywords: list[str], brand_slug: str) -> set[int]:
    """
    Search the SQLite database (pages.gemini_text) for exact keyword matches.
    Returns doc_ids that contain any of the keywords in their content.
    This is critical for finding documents where the filename doesn't match
    but the content mentions the queried model/code.
    """
    if not keywords:
        return set()

    db_path = "/app/data/andreja.db"
    try:
        conn = sqlite3.connect(db_path, timeout=5)
        cursor = conn.cursor()

        matching_doc_ids = set()
        for kw in keywords:
            # Search case-insensitive in page content
            # Also join with documents table to filter by brand
            cursor.execute("""
                SELECT DISTINCT p.document_id
                FROM pages p
                JOIN documents d ON p.document_id = d.id
                JOIN brands b ON d.brand_id = b.id
                WHERE b.slug = ?
                AND (p.gemini_text LIKE ? COLLATE NOCASE
                     OR d.original_filename LIKE ? COLLATE NOCASE)
            """, (brand_slug, f"%{kw}%", f"%{kw}%"))
            for row in cursor.fetchall():
                matching_doc_ids.add(row[0])

        conn.close()
        if matching_doc_ids:
            logger.info(f"DB keyword search for {keywords}: found doc_ids {matching_doc_ids}")
        return matching_doc_ids

    except Exception as e:
        logger.warning(f"DB keyword search failed: {e}")
        return set()


def _content_keyword_bonus(text: str, keywords: list[str]) -> float:
    """
    Bonus when the chunk text literally contains the queried keywords.
    This is distinct from semantic similarity — it rewards exact matches.
    """
    if not text or not keywords:
        return 0.0

    text_lower = text.lower()
    bonus = 0.0
    for kw in keywords:
        kw_lower = kw.lower()
        if kw_lower in text_lower:
            bonus += 0.10  # Strong bonus for exact content match
        # Also check without spaces/dots (e.g., "C0710" matches "C.07.10")
        kw_compact = re.sub(r'[.\s\-]', '', kw_lower)
        text_compact = re.sub(r'[.\s\-]', '', text_lower)
        if len(kw_compact) >= 3 and kw_compact in text_compact and kw_lower not in text_lower:
            bonus += 0.06

    return min(bonus, 0.25)


def _filename_match_bonus(filename: str, query: str) -> float:
    """
    Bonus when query terms match the document filename.
    Uses aggressive normalization to handle user typing variations:
    - "atc c0710" matches "ATC - C.07.10"
    - "ovf10" matches "Calibração do OVF10.pdf"
    - "gen2" matches "Manual GEN2 Resgate.pdf"
    - "calibracao ovf10" matches "Calibração do OVF10.pdf"
    """
    if not filename or not query:
        return 0.0

    # Normalize both for comparison
    fn_normalized = _normalize_for_matching(filename)
    query_normalized = _normalize_for_matching(query)

    # Also create "squished" versions (no spaces) for matching things like
    # "c0710" in "c 07 10" or "ovf10" in "ovf 10"
    fn_squished = fn_normalized.replace(" ", "")
    query_squished = query_normalized.replace(" ", "")

    # Extract meaningful tokens from query
    query_tokens = _extract_key_tokens(query)
    if not query_tokens:
        return 0.0

    bonus = 0.0
    matched_tokens = 0

    for token in query_tokens:
        # Direct match in normalized filename
        if token in fn_normalized:
            bonus += 0.08
            matched_tokens += 1
        # Squished match (e.g., "c0710" in "c0710" from "C.07.10")
        elif token in fn_squished:
            bonus += 0.08
            matched_tokens += 1
        # Try squished token in squished filename (e.g., "ovf10" in "ovf10")
        elif token.replace(" ", "") in fn_squished:
            bonus += 0.06
            matched_tokens += 1

    # Extra bonus if multiple tokens match (more specific = more relevant)
    if matched_tokens >= 2:
        bonus += 0.05

    return min(bonus, 0.25)


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
    """Generate embedding using selected provider."""
    provider = (settings.embedding_provider or PROVIDER_GEMINI).strip().lower()

    if provider == PROVIDER_OPEN_SOURCE:
        return _get_ollama_embedding(text)

    result = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=[text],
        config=types.EmbedContentConfig(
            task_type="RETRIEVAL_DOCUMENT",
            output_dimensionality=VECTOR_SIZE,
        ),
    )
    return result.embeddings[0].values


def get_embeddings_batch(texts: list[str]) -> list[list[float]]:
    """Generate embeddings for multiple texts in a single API call (batch)."""
    if not texts:
        return []

    provider = (settings.embedding_provider or PROVIDER_GEMINI).strip().lower()

    if provider == PROVIDER_OPEN_SOURCE:
        return [_get_ollama_embedding(t) for t in texts]

    result = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=texts,
        config=types.EmbedContentConfig(
            task_type="RETRIEVAL_DOCUMENT",
            output_dimensionality=VECTOR_SIZE,
        ),
    )
    return [e.values for e in result.embeddings]


def get_query_embedding(text: str) -> list[float]:
    """Generate embedding for query using selected provider."""
    provider = (settings.embedding_provider or PROVIDER_GEMINI).strip().lower()

    if provider == PROVIDER_OPEN_SOURCE:
        return _get_ollama_embedding(text)

    result = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=[text],
        config=types.EmbedContentConfig(
            task_type="RETRIEVAL_QUERY",
            output_dimensionality=VECTOR_SIZE,
        ),
    )
    return result.embeddings[0].values


def _get_ollama_embedding(text: str) -> list[float]:
    payload = {
        "model": settings.ollama_embedding_model,
        "prompt": text,
    }
    timeout = httpx.Timeout(settings.ollama_timeout_seconds)
    with httpx.Client(timeout=timeout) as http_client:
        response = http_client.post(
            f"{settings.ollama_base_url.rstrip('/')}/api/embeddings",
            json=payload,
        )
        response.raise_for_status()
        data = response.json()
        embedding = data.get("embedding")
        if not embedding:
            raise RuntimeError("Ollama embedding response sem vetor")
        if len(embedding) != VECTOR_SIZE:
            raise RuntimeError(
                f"Dimensão do embedding incompatível: esperado {VECTOR_SIZE}, recebido {len(embedding)}"
            )
        return embedding


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

    # Batch embed all chunks in a single API call (much faster)
    embeddings = get_embeddings_batch(chunks)

    points: list[PointStruct] = []
    point_ids: list[str] = []
    chunk_total = len(chunks)

    for index, (chunk_text, embedding) in enumerate(zip(chunks, embeddings)):
        point_id = str(uuid.uuid4())
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
    invalidate_filename_cache(collection_name)
    return point_ids[0]


# Cache: collection_name → {doc_id: doc_filename}
_doc_filename_cache: dict[str, dict[int, str]] = {}


def _get_doc_filename_map(collection_name: str, client) -> dict[int, str]:
    """
    Build a mapping of doc_id → doc_filename for all documents in a collection.
    Uses an in-memory cache that survives across queries (invalidated on upsert).
    For 24k+ vectors, scrolling with payload-only (no vectors) takes ~200ms total.
    """
    if collection_name in _doc_filename_cache:
        return _doc_filename_cache[collection_name]

    seen_docs: dict[int, str] = {}
    next_offset = None

    for _ in range(100):  # Safety limit (~50k vectors)
        resp = client.scroll(
            collection_name=collection_name,
            limit=500,
            offset=next_offset,
            with_payload=["doc_id", "doc_filename"],  # Only fetch these fields
        )
        points, next_offset = resp
        for pt in points:
            payload = pt.payload or {}
            did = payload.get("doc_id", 0)
            if did and did not in seen_docs:
                seen_docs[did] = payload.get("doc_filename", "")
        if not next_offset or not points:
            break

    _doc_filename_cache[collection_name] = seen_docs
    logger.info(f"Built filename cache for {collection_name}: {len(seen_docs)} docs")
    return seen_docs


def invalidate_filename_cache(collection_name: str):
    """Call after upsert/delete to refresh the cache on next search."""
    _doc_filename_cache.pop(collection_name, None)


def _find_filename_matching_doc_ids(collection_name: str, query: str, client) -> set[int]:
    """
    Find doc_ids whose filename closely matches the query.
    This ensures documents named after the queried topic are always
    included as candidates, even if their *content* embeddings rank lower
    than other docs in a large collection.
    """
    query_tokens = _extract_key_tokens(query)
    if not query_tokens:
        return set()

    doc_map = _get_doc_filename_map(collection_name, client)

    matching_ids: set[int] = set()
    for did, fname in doc_map.items():
        bonus = _filename_match_bonus(fname, query)
        if bonus >= 0.15:  # Strong filename match (≥2 tokens)
            matching_ids.add(did)

    return matching_ids


def search_brand(brand_slug: str, query: str, top_k: int = 7) -> list[dict]:
    """
    Comprehensive hybrid search within a brand's collection.

    5-phase approach to ensure maximum recall:
      Phase 1: Semantic search (embedding similarity)
      Phase 2: Filename-aware injection (doc names matching query)
      Phase 3: DB content keyword search (exact terms in page text)
      Phase 4: Multi-query injection (re-embed individual key terms)
      Phase 5: Scoring with bonuses + diversity

    This ensures that documents are found even when:
    - Filename doesn't match the query (content search catches it)
    - Content embeddings rank low (filename + keyword search catches it)
    - Query terms appear literally but aren't semantically similar
    """
    collection_name = f"brand_{brand_slug}"
    qdrant = get_qdrant_client()

    # Check collection exists
    existing = [c.name for c in qdrant.get_collections().collections]
    if collection_name not in existing:
        return []

    query_vector = get_query_embedding(query)
    fault_tokens = _extract_query_fault_tokens(query)
    search_keywords = _extract_search_keywords(query)

    logger.info(f"Search '{query}' | keywords={search_keywords} | fault_tokens={fault_tokens}")

    # --- Phase 1: standard semantic search ---
    results = qdrant.search(
        collection_name=collection_name,
        query_vector=query_vector,
        limit=max(top_k * 10, 100),
        with_payload=True,
        score_threshold=0.3,
    )
    retrieved_ids = {hit.id for hit in results}

    # --- Phase 2: filename-aware retrieval ---
    filename_doc_ids = _find_filename_matching_doc_ids(collection_name, query, qdrant)
    semantic_doc_ids = {(hit.payload or {}).get("doc_id") for hit in results}
    missing_filename_docs = filename_doc_ids - semantic_doc_ids

    if missing_filename_docs:
        logger.info(f"Phase 2 filename inject: docs {missing_filename_docs}")
        for doc_id in missing_filename_docs:
            extra = qdrant.search(
                collection_name=collection_name,
                query_vector=query_vector,
                query_filter=Filter(
                    must=[FieldCondition(key="doc_id", match=MatchValue(value=doc_id))]
                ),
                limit=4,
                with_payload=True,
                score_threshold=0.1,
            )
            for hit in extra:
                if hit.id not in retrieved_ids:
                    results.append(hit)
                    retrieved_ids.add(hit.id)

    # --- Phase 3: DB content keyword search ---
    # Search the SQLite pages table for exact keyword matches in content.
    # This finds documents where the content mentions the queried model/code
    # even when the filename is completely different.
    if search_keywords:
        content_doc_ids = _db_keyword_search(search_keywords, brand_slug)
        current_doc_ids = {(hit.payload or {}).get("doc_id") for hit in results}
        missing_content_docs = content_doc_ids - current_doc_ids

        if missing_content_docs:
            logger.info(f"Phase 3 content keyword inject: docs {missing_content_docs}")
            for doc_id in missing_content_docs:
                extra = qdrant.search(
                    collection_name=collection_name,
                    query_vector=query_vector,
                    query_filter=Filter(
                        must=[FieldCondition(key="doc_id", match=MatchValue(value=doc_id))]
                    ),
                    limit=4,
                    with_payload=True,
                    score_threshold=0.1,
                )
                for hit in extra:
                    if hit.id not in retrieved_ids:
                        results.append(hit)
                        retrieved_ids.add(hit.id)

    # --- Phase 4: Multi-query injection ---
    # Re-embed individual key terms and search separately.
    # "Falhas no XO 508" as a single embedding might miss XO 508 content,
    # but "XO 508" alone as an embedding is more focused.
    if search_keywords:
        for kw in search_keywords[:3]:  # Max 3 extra queries
            if len(kw) < 2:
                continue
            try:
                kw_vector = get_query_embedding(kw)
                kw_results = qdrant.search(
                    collection_name=collection_name,
                    query_vector=kw_vector,
                    limit=20,
                    with_payload=True,
                    score_threshold=0.4,
                )
                for hit in kw_results:
                    if hit.id not in retrieved_ids:
                        results.append(hit)
                        retrieved_ids.add(hit.id)
            except Exception as e:
                logger.warning(f"Multi-query search for '{kw}' failed: {e}")

    # --- Phase 5: scoring with bonuses ---
    chunks = []
    for hit in results:
        payload = hit.payload or {}
        payload_text = payload.get("text", "")
        doc_filename = payload.get("doc_filename", "")
        boosted_score = hit.score
        boosted_score += _lexical_fault_bonus(payload_text, fault_tokens)
        boosted_score += _filename_match_bonus(doc_filename, query)
        boosted_score += _content_keyword_bonus(payload_text, search_keywords)
        chunks.append({
            "text": payload_text,
            "source": doc_filename,
            "page": payload.get("page_number", 0),
            "doc_id": payload.get("doc_id", 0),
            "brand_slug": payload.get("brand_slug", ""),
            "score": boosted_score,
        })

    chunks.sort(key=lambda item: item["score"], reverse=True)

    # Document diversity: ensure no single document dominates results.
    MAX_PER_DOC = 3
    doc_counts: dict[int, int] = {}
    diverse_chunks: list[dict] = []
    for chunk in chunks:
        doc_id = chunk["doc_id"]
        count = doc_counts.get(doc_id, 0)
        if count < MAX_PER_DOC:
            diverse_chunks.append(chunk)
            doc_counts[doc_id] = count + 1
        if len(diverse_chunks) >= top_k:
            break

    # If we didn't fill top_k with diverse chunks, add remaining by score
    if len(diverse_chunks) < top_k:
        seen_ids = {id(c) for c in diverse_chunks}
        for chunk in chunks:
            if id(chunk) not in seen_ids:
                diverse_chunks.append(chunk)
                if len(diverse_chunks) >= top_k:
                    break

    return diverse_chunks


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
    invalidate_filename_cache(collection_name)
