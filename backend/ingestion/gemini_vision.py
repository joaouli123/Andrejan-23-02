import asyncio
import time
from google import genai
from google.genai import types
from tenacity import retry, retry_if_not_exception_type, stop_after_attempt, wait_exponential
from config import get_settings
import logging
import re

logger = logging.getLogger(__name__)
settings = get_settings()

client = genai.Client(api_key=settings.gemini_api_key)

VISION_MODEL = "gemini-2.5-flash"


class GeminiQuotaExceededError(RuntimeError):
    pass

PAGE_PROMPT_TEMPLATE = """Você é um especialista técnico em elevadores e sistemas de transporte vertical.
Analise a PÁGINA {page_number} deste documento (apostila/manual técnico de elevador) com máxima atenção.
Extraia e documente TUDO que conseguir identificar nessa página específica, COM PRIORIDADE PARA TRANSCRIÇÃO LITERAL:

1. **Textos**: Transcreva todo texto visível, incluindo títulos, subtítulos, notas e rodapés.
2. **Tabelas**: Reproduza tabelas completas com todos os valores, unidades e cabeçalhos.
    - Preserve exatamente códigos alfa-numéricos (ex.: UV1, UV2, UV3, OC, GF, BR1, OL1, etc.).
    - NÃO resuma tabela como "contém tabela"; transcreva linha a linha.
3. **Esquemas elétricos/hidráulicos**: Descreva detalhadamente os componentes, conexões, terminais, códigos de fios, relés, contatores, etc.
4. **Fotos e diagramas**: Descreva o que está na imagem — peças, componentes, modelos de elevadores, painel de controle, etc.
5. **Especificações técnicas**: Tensões, correntes, potências, velocidades, capacidades, dimensões.
6. **Modelos e códigos**: Identifique números de modelo, códigos de peças, seriais se visíveis.
7. **Procedimentos**: Passos de instalação, manutenção, diagnóstico ou ajuste.

Se a qualidade da imagem for baixa, faça o melhor possível e indique quais partes ficaram ilegíveis.
Seja extremamente preciso — técnicos usarão esta informação para manutenção real de elevadores.
Responda em português, de forma estruturada e detalhada.
"""

IMAGE_PAGE_PROMPT_TEMPLATE = """Você está recebendo a IMAGEM EXATA da página {page_number} de um manual técnico.
Sua tarefa é transcrever fielmente o conteúdo visível, principalmente tabelas e códigos de falhas.

REGRAS OBRIGATÓRIAS:
1) TRANSCRIÇÃO LITERAL da tabela (linha a linha, coluna a coluna).
2) Preserve códigos exatamente como aparecem (UV1, UV2, UV3, OC, GF, BR1 etc.).
3) Não faça resumo genérico tipo "a página contém uma tabela".
4) Se algo estiver ilegível, marque explicitamente como [ilegível] no ponto exato.
5) Priorize coluna “Indicação do display”, “Descrição”, “Causas”, “Ação corretiva” quando existir.

Formato de saída:
- Título da página
- Texto geral
- Tabela(s) transcrita(s) em Markdown
- Itens ilegíveis
"""

STRICT_IMAGE_PAGE_PROMPT_TEMPLATE = """Você está recebendo a IMAGEM EXATA da página {page_number} de um manual técnico de elevadores.

OBJETIVO: TRANSCRIÇÃO LITERAL E FORENSE DA PÁGINA.

REGRAS CRÍTICAS (NÃO VIOLAR):
1) NÃO resumir nem explicar; apenas transcrever o que está visível.
2) Em tabelas, preserve estrutura de colunas e transcreva linha por linha em Markdown.
3) Se uma célula continuar na linha seguinte, mantenha como continuação da MESMA linha lógica.
4) Preserve exatamente códigos e siglas: UV1, UV2, UV3, OC, OV, GF, BR1, OL1, MC, PUV, CUV etc.
5) Não trocar caracteres parecidos (O/0, I/1, U/V).
6) Se algo estiver ilegível, use [ilegível] somente no ponto exato.

Formato obrigatório:
- Cabeçalho da página
- Texto corrido literal
- Tabelas literais em Markdown
- Lista de trechos ilegíveis
"""

RERANK_PROMPT = """Avalie cada trecho de 0 a 10 quanto à relevância para a consulta técnica.
Se o trecho menciona o modelo/placa/código exato da consulta, score mínimo 6.

Consulta: {query}

Trechos:
{chunks}

Responda APENAS com JSON (sem explicação, sem markdown):
[{{"index": 0, "score": 9}}, {{"index": 1, "score": 3}}]
"""


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def upload_pdf_to_gemini(pdf_path: str) -> object:
    """
    Upload a PDF file to Gemini File API.
    Returns the uploaded file object (state=ACTIVE when ready).
    """
    logger.info(f"Uploading PDF to Gemini File API: {pdf_path}")
    uploaded = client.files.upload(
        file=pdf_path,
        config=types.UploadFileConfig(mime_type="application/pdf"),
    )

    # Wait until file is processed
    max_wait = 60
    waited = 0
    while hasattr(uploaded, 'state') and str(uploaded.state) in ('FileState.PROCESSING', 'PROCESSING') and waited < max_wait:
        time.sleep(2)
        waited += 2
        uploaded = client.files.get(name=uploaded.name)

    state_name = str(getattr(uploaded, "state", ""))
    if "FAILED" in state_name:
        raise RuntimeError(f"Gemini file upload failed: state={state_name}")

    logger.info(f"PDF uploaded successfully: {uploaded.name}")
    return uploaded


def delete_gemini_file(uploaded_file: object) -> None:
    """Delete a file from Gemini File API after processing."""
    try:
        client.files.delete(name=uploaded_file.name)
        logger.info(f"Deleted Gemini file: {uploaded_file.name}")
    except Exception as e:
        logger.warning(f"Could not delete Gemini file {uploaded_file.name}: {e}")


def _looks_generic_extraction(text: str) -> bool:
    if not text:
        return True
    lowered = text.lower()
    generic_patterns = [
        "contém uma tabela",
        "a página contém",
        "análise da página",
        "extração detalhada",
        "não foi possível",
    ]
    generic_hit = any(pattern in lowered for pattern in generic_patterns)
    has_code = re.search(r"\b[a-z]{1,3}\d{1,3}\b", lowered) is not None
    return (len(text) < 900 and generic_hit) or (generic_hit and not has_code)


def _has_table_signals(text: str) -> bool:
    if not text:
        return False
    lowered = text.lower()
    return (
        lowered.count("|") >= 8
        or "indicação do display" in lowered
        or "ação corretiva" in lowered
        or "códigos de falhas" in lowered
    )


def _score_extraction_candidate(text: str) -> float:
    if not text:
        return 0.0

    lowered = text.lower()
    score = min(1.0, len(text) / 3500)

    if _has_table_signals(text):
        score += 0.25
    if re.search(r"\b[a-z]{1,4}\d{1,3}\b", lowered):
        score += 0.2
    if _looks_generic_extraction(text):
        score -= 0.35

    return max(0.0, min(1.0, score))


async def _extract_from_page_image(pdf_path: str, page_number: int, dpi: int = 300, strict: bool = False) -> str:
    import fitz

    doc = fitz.open(pdf_path)
    try:
        page = doc.load_page(page_number - 1)
        zoom = max(1.0, dpi / 72.0)
        matrix = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        image_bytes = pix.tobytes("png")

        template = STRICT_IMAGE_PAGE_PROMPT_TEMPLATE if strict else IMAGE_PAGE_PROMPT_TEMPLATE
        prompt = template.format(page_number=page_number)
        response = await client.aio.models.generate_content(
            model=VISION_MODEL,
            contents=[
                prompt,
                types.Part.from_bytes(data=image_bytes, mime_type="image/png"),
            ],
            config=types.GenerateContentConfig(
                temperature=0.0,
                max_output_tokens=4096,
            ),
        )
        return (response.text or "").strip()
    finally:
        doc.close()


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_not_exception_type(GeminiQuotaExceededError),
)
async def extract_page_from_pdf(uploaded_file: object, page_number: int, pdf_path: str | None = None) -> tuple[str, float]:
    """
    Use Gemini 2.0 Flash to extract content from a specific page of an uploaded PDF.
    No image conversion needed — Gemini reads the PDF natively.
    Returns (extracted_text, quality_score).
    """
    try:
        prompt = PAGE_PROMPT_TEMPLATE.format(page_number=page_number)

        response = await client.aio.models.generate_content(
            model=VISION_MODEL,
            contents=[prompt, uploaded_file],
            config=types.GenerateContentConfig(
                temperature=0.1,
                max_output_tokens=4096,
            ),
        )

        raw_text = response.text or ""
        direct_text = raw_text.strip()
        if not direct_text:
            direct_text = f"[Sem conteúdo textual detectável na página {page_number}]"

        best_text = direct_text
        best_score = _score_extraction_candidate(direct_text)

        # Passagem 2: fallback por imagem 300 DPI quando detectar baixa fidelidade.
        needs_image_fallback = _looks_generic_extraction(direct_text) or best_score < 0.5
        if pdf_path and needs_image_fallback:
            logger.info(f"Fallback to page-image extraction (300 DPI) for page {page_number}")
            image_text = await _extract_from_page_image(pdf_path, page_number, dpi=300, strict=False)
            image_score = _score_extraction_candidate(image_text)
            if image_score > best_score:
                best_text = image_text
                best_score = image_score

            # Se ainda estiver genérico, força modo estrito.
            if _looks_generic_extraction(best_text) or best_score < 0.55:
                logger.info(f"Strict image retry for page {page_number}")
                strict_text = await _extract_from_page_image(pdf_path, page_number, dpi=300, strict=True)
                strict_score = _score_extraction_candidate(strict_text)
                if strict_score > best_score:
                    best_text = strict_text
                    best_score = strict_score

        quality_score = max(best_score, _estimate_quality(best_text))
        return best_text, quality_score

    except Exception as e:
        if is_quota_exceeded_error(e):
            logger.error(f"Gemini quota exceeded on page {page_number}: {e}")
            raise GeminiQuotaExceededError("Limite da API Gemini excedido (429 RESOURCE_EXHAUSTED)") from e
        logger.error(f"Gemini error on page {page_number}: {e}")
        raise


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def rerank_chunks(query: str, chunks: list[dict]) -> list[dict]:
    """
    Use Gemini to re-rank retrieved chunks by relevance to the query.
    Only reranks the top candidates to keep prompt short.
    """
    # Only rerank top 10 to avoid prompt being too long
    candidates = chunks[:10]

    try:
        chunks_text = "\n\n".join(
            f"[{i}] Fonte: {c['source'].split('/')[-1]} | Página: {c['page']}\n{c['text'][:300]}"
            for i, c in enumerate(candidates)
        )

        prompt = RERANK_PROMPT.format(query=query, chunks=chunks_text)
        response = await client.aio.models.generate_content(
            model=VISION_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.0,
                max_output_tokens=2048,
                thinking_config=types.ThinkingConfig(include_thoughts=False),
            ),
        )

        import json
        import re
        raw_text = (response.text or "").strip()
        # Strip markdown code fences if present
        raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
        raw_text = re.sub(r"\s*```$", "", raw_text)

        # Try to parse JSON array (may be truncated by model)
        json_match = re.search(r'\[.*\]', raw_text, re.DOTALL)
        if not json_match:
            # Try to fix truncated JSON by closing the array
            if raw_text.strip().startswith("["):
                # Remove any incomplete trailing object and close the array
                fixed = raw_text.strip()
                # Remove trailing incomplete object (e.g., '{"index":')
                last_complete = fixed.rfind("}")
                if last_complete > 0:
                    fixed = fixed[:last_complete + 1] + "]"
                    json_match = re.search(r'\[.*\]', fixed, re.DOTALL)
                    if json_match:
                        logger.info(f"Rerank: fixed truncated JSON ({len(raw_text)} chars)")

        if json_match:
            scores = json.loads(json_match.group())
            reranked = []
            for item in scores:
                idx = item.get("index", 0)
                if idx < len(candidates):
                    candidates[idx]["rerank_score"] = item.get("score", 0)
                    if item.get("score", 0) >= 5:
                        reranked.append(candidates[idx])
            if reranked:
                logger.info(f"Rerank: {len(reranked)} chunks passed (of {len(candidates)})")
                return sorted(reranked, key=lambda x: x.get("rerank_score", 0), reverse=True)
            else:
                logger.warning(f"Rerank: all scores < 5, returning top chunks by original score")
                return candidates[:7]
        else:
            logger.warning(f"Rerank: no JSON found in response ({len(raw_text)} chars): {raw_text[:200]}")
            return candidates[:7]
    except Exception as e:
        logger.warning(f"Rerank failed, returning original order: {e}")

    return candidates[:7]


def _estimate_quality(text: str) -> float:
    """Heuristic quality score based on extracted text length and content."""
    if len(text) < 50:
        return 0.1
    elif len(text) < 200:
        return 0.4
    elif len(text) < 500:
        return 0.7
    else:
        return min(1.0, len(text) / 2000)


def is_quota_exceeded_error(error: Exception) -> bool:
    text = str(error).upper()
    return "RESOURCE_EXHAUSTED" in text or " 429" in text or "'CODE': 429" in text
