import asyncio
import base64
import io
import logging
import re
import time

import fitz
import pytesseract
from PIL import Image

from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# ---------------------------------------------------------------------------
# Prompt de transcrição para Gemini Vision — QUALIDADE MÁXIMA
# ---------------------------------------------------------------------------
GEMINI_OCR_PROMPT = """Transcreva o conteúdo visível desta página de manual técnico de elevadores.

Regras:
1) Transcreva todo texto visível de forma fiel e concisa.
2) Tabelas: reproduza em Markdown com TODAS as colunas e linhas. Cada linha da tabela em UMA linha de texto.
3) Códigos técnicos e valores numéricos: copie EXATAMENTE.
4) NÃO repita conteúdo. NÃO adicione explicações.
5) Trechos ilegíveis: marque como [ilegível].
6) Imagens/diagramas: descreva brevemente entre colchetes.
7) Seja CONCISO. Não repita cabeçalhos. Não adicione formatação extra.
"""

# Limite máximo de caracteres armazenados por página
# Evita que Gemini produza textos enormes (108K+) que geram chunks ruins para embeddings
MAX_PAGE_TEXT_CHARS = 5000

# Modelo Gemini para OCR (grátis, rápido, ótimo para visão)
# 2.5‑flash é estável, free‑tier, melhor em tabelas/imagens que o 2.0‑flash (deprecated)
GEMINI_OCR_MODEL = "gemini-2.5-flash"

# Controle de rate limit do Gemini (free tier: ~15 RPM)
# Intervalo adaptativo: 2s base + retry com backoff em 429
_last_gemini_call: float = 0.0
GEMINI_MIN_INTERVAL: float = 2.0  # segundos entre chamadas (~30 RPM teórico, mas nem toda página chama Gemini)
GEMINI_MAX_RETRIES: int = 3  # tentativas em caso de 429


# ---------------------------------------------------------------------------
#  Helpers de qualidade
# ---------------------------------------------------------------------------
def _has_table_signals(text: str) -> bool:
    """Detecta sinais de tabela no texto."""
    lowered = (text or "").lower()
    return (
        lowered.count("|") >= 8
        or "indicação do display" in lowered
        or "ação corretiva" in lowered
        or "códigos" in lowered
    )


def _estimate_quality(text: str) -> float:
    """Score genérico 0‒1 baseado em tamanho + sinais técnicos."""
    if not text:
        return 0.0

    lowered = text.lower()
    score = min(1.0, len(text) / 3500)

    if _has_table_signals(text):
        score += 0.25
    if re.search(r"\b[a-z]{1,4}\d{1,3}\b", lowered):
        score += 0.2

    return max(0.0, min(1.0, score))


def _is_tesseract_quality_sufficient(text: str, min_chars: int = 200) -> bool:
    """
    Verifica se o texto do Tesseract é realmente LEGÍVEL, não apenas longo.
    Tesseract frequentemente produz 1000+ chars de lixo em páginas com tabelas
    e o pipeline antigo aceitava cegamente por ter >= 200 chars.
    
    Detecta:
    - Palavras grudadas sem espaço (ex: 'Problemasnafonteoupós')
    - Caracteres de borda de tabela lidos como 'Ôö', 'Ôäó'
    - Média de comprimento de palavra muito alta (texto grudado)
    - Baixa proporção de letras (muita sujeira de OCR)
    - TABELAS (muitos '|') — Tesseract erra fatalmente em tabelas técnicas
    """
    if len(text) < min_chars:
        return False

    words = text.split()
    if len(words) < 5:
        return False

    # 0. TABELAS: Se tem muitos pipe chars, Tesseract SEMPRE erra tabelas técnicas
    #    Páginas com tabelas de códigos de erro são críticas e precisam de Gemini
    pipe_count = text.count("|")
    if pipe_count >= 6:
        logger.debug(
            f"Quality check FAIL: {pipe_count} pipe chars (table detected)"
        )
        return False

    # 1. Palavras grudadas (>25 chars) — Tesseract erra tabelas assim
    #    Ex: "Problemasnafonteoupós", "Errodechedsunnaamelidades"
    long_words = [w for w in words if len(w) > 25]
    if len(long_words) > max(2, len(words) * 0.08):
        logger.debug(
            f"Quality check FAIL: {len(long_words)}/{len(words)} merged words"
        )
        return False

    # 2. Caracteres de borda de tabela lidos como 'Ôö', 'Ôäó', etc.
    box_count = text.count("Ôö") + text.count("Ôäó") + text.count("ÔöÔö")
    if box_count > 4:
        logger.debug(f"Quality check FAIL: {box_count} box-drawing artifacts")
        return False

    # 3. Média de comprimento de palavra — texto grudado tem média > 12
    avg_len = sum(len(w) for w in words) / len(words)
    if avg_len > 14:
        logger.debug(f"Quality check FAIL: avg word len {avg_len:.1f}")
        return False

    # 4. Proporção de letras (alpha) no texto — OCR quebrado tem muita sujeira
    alpha_chars = sum(1 for c in text if c.isalpha())
    alpha_ratio = alpha_chars / len(text) if text else 0
    if alpha_ratio < 0.35:
        logger.debug(f"Quality check FAIL: alpha ratio {alpha_ratio:.2f}")
        return False

    return True


# ---------------------------------------------------------------------------
#  Renderização de páginas
# ---------------------------------------------------------------------------
def _render_pdf_page_to_png_bytes(pdf_path: str, page_number: int, dpi: int = 200) -> bytes:
    """Renderiza página do PDF em PNG."""
    doc = fitz.open(pdf_path)
    try:
        page = doc.load_page(page_number - 1)
        zoom = max(1.0, dpi / 72.0)
        matrix = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        return pix.tobytes("png")
    finally:
        doc.close()


# ---------------------------------------------------------------------------
#  Tier 1 — Texto nativo (PyMuPDF)
# ---------------------------------------------------------------------------
def _extract_pdf_text_native(pdf_path: str, page_number: int) -> str:
    doc = fitz.open(pdf_path)
    try:
        page = doc.load_page(page_number - 1)
        text = (page.get_text("text") or "").strip()
        return text
    finally:
        doc.close()


# ---------------------------------------------------------------------------
#  Tier 2 — Tesseract OCR (200 DPI, PSM 3 + PSM 6)
# ---------------------------------------------------------------------------
def _run_tesseract_on_image(pil_image: Image.Image) -> tuple[str, str]:
    """
    Roda Tesseract em dois modos na mesma imagem PIL.
    Retorna (texto_psm3, texto_psm6).
    """
    text_psm3 = pytesseract.image_to_string(
        pil_image, lang="por+eng", config="--oem 1 --psm 3"
    ).strip()

    text_psm6 = pytesseract.image_to_string(
        pil_image, lang="por+eng", config="--oem 1 --psm 6"
    ).strip()

    return text_psm3, text_psm6


# ---------------------------------------------------------------------------
#  Tier 3 — Gemini 2.0 Flash Vision (grátis, alta qualidade para fotos)
# ---------------------------------------------------------------------------
async def _extract_page_gemini_flash(
    image_bytes: bytes,
    page_number: int,
) -> tuple[str, float]:
    """
    Usa Gemini 2.5 Flash (tier grátis) para extrair texto de imagem.
    Ideal para páginas com fotos, diagramas, capas — onde Tesseract falha.
    Respeita rate limit com intervalo mínimo + retry automático em 429.
    Thinking desligado (thinking_budget=0) pois OCR não precisa raciocinar.
    """
    global _last_gemini_call

    from google import genai
    from google.genai import types

    # Rate limiting: esperar intervalo mínimo entre chamadas
    now = time.time()
    elapsed = now - _last_gemini_call
    if elapsed < GEMINI_MIN_INTERVAL:
        wait = GEMINI_MIN_INTERVAL - elapsed
        logger.info(f"Page {page_number}: Gemini rate limit — aguardando {wait:.1f}s")
        await asyncio.sleep(wait)

    client = genai.Client(api_key=settings.gemini_api_key)

    prompt = GEMINI_OCR_PROMPT + f"\n\nPágina: {page_number}"

    # Retry com backoff exponencial para 429 (RESOURCE_EXHAUSTED)
    response = None
    for attempt in range(GEMINI_MAX_RETRIES):
        try:
            response = await client.aio.models.generate_content(
                model=GEMINI_OCR_MODEL,
                contents=[
                    prompt,
                    types.Part.from_bytes(data=image_bytes, mime_type="image/png"),
                ],
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    max_output_tokens=2048,
                    thinking_config=types.ThinkingConfig(include_thoughts=False),
                ),
            )
            break  # sucesso
        except Exception as e:
            err_str = str(e).lower()
            if "429" in err_str or "resource_exhausted" in err_str or "rate" in err_str:
                backoff = GEMINI_MIN_INTERVAL * (2 ** attempt)  # 2s, 4s, 8s
                logger.warning(
                    f"Page {page_number}: Gemini 429 (tentativa {attempt+1}/{GEMINI_MAX_RETRIES}) "
                    f"— aguardando {backoff:.1f}s"
                )
                await asyncio.sleep(backoff)
                if attempt == GEMINI_MAX_RETRIES - 1:
                    raise
            else:
                raise

    _last_gemini_call = time.time()

    text = (response.text or "").strip()
    if not text:
        text = f"[Sem conteúdo textual detectável na página {page_number}]"

    # Hard cap — evita chunks enormes que arruinam embeddings/busca
    if len(text) > MAX_PAGE_TEXT_CHARS:
        logger.info(
            f"Page {page_number}: Gemini text truncated {len(text)} → {MAX_PAGE_TEXT_CHARS} chars"
        )
        text = text[:MAX_PAGE_TEXT_CHARS]

    return text, _estimate_quality(text)


# ---------------------------------------------------------------------------
#  Orquestrador principal — Tesseract + Gemini Flash (modo híbrido)
# ---------------------------------------------------------------------------
async def extract_page_open_source(pdf_path: str, page_number: int) -> tuple[str, float]:
    """
    Pipeline HÍBRIDO de extração com PRIORIDADE EM QUALIDADE:

    Tier 1: Texto nativo (PyMuPDF) — para PDFs digitais com camada de texto.
    Tier 2: Tesseract OCR (200 DPI, PSM3+PSM6) — rápido, ~4s/página.
            Aceita se >= 200 chars (páginas de texto puro).
    Tier 3: Gemini 2.0 Flash Vision (GRÁTIS) — para páginas com fotos,
            diagramas, capas onde Tesseract extrai < 200 chars de texto.
            Alta qualidade, ~5s/página (com rate limit).
    Fallback: Qualquer texto do Tesseract se Gemini falhar.

    VPS: 15.6 GB RAM, CPU only. Sem Ollama VL (crashava por falta de GPU).
    """

    # --- Tier 1: Texto nativo (camada de texto em PDFs digitais) ---
    native_text = _extract_pdf_text_native(pdf_path, page_number)
    if native_text and len(native_text) >= 200:
        logger.info(
            f"Page {page_number}: ✓ native text ({len(native_text)} chars)"
        )
        return native_text, _estimate_quality(native_text)

    # --- Tier 2: Tesseract OCR — renderiza UMA vez a 200 DPI ---
    tesseract_text = ""
    tesseract_text_psm6 = ""
    image_bytes = b""
    try:
        image_bytes = _render_pdf_page_to_png_bytes(pdf_path, page_number, dpi=200)
        pil_image = Image.open(io.BytesIO(image_bytes))

        tesseract_text, tesseract_text_psm6 = _run_tesseract_on_image(pil_image)

        pil_image.close()
    except Exception as e:
        logger.warning(f"Page {page_number}: Tesseract erro: {e}")

    # Escolher o melhor resultado do Tesseract
    best_tesseract = tesseract_text
    best_mode = "PSM3"
    if len(tesseract_text_psm6) > len(tesseract_text):
        best_tesseract = tesseract_text_psm6
        best_mode = "PSM6"

    # Se Tesseract extraiu >= 200 chars E o texto é legível, ACEITAR
    if _is_tesseract_quality_sufficient(best_tesseract, min_chars=200):
        logger.info(
            f"Page {page_number}: ✓ Tesseract {best_mode} ({len(best_tesseract)} chars, quality OK)"
        )
        return best_tesseract, _estimate_quality(best_tesseract)

    # --- Tier 3: Gemini 2.0 Flash Vision ---
    # Se chegou aqui: Tesseract insuficiente (<200 chars) ou qualidade ruim
    reason = "qualidade insuficiente" if len(best_tesseract) >= 200 else f"pouco texto ({len(best_tesseract)} chars)"
    if settings.gemini_api_key:
        logger.info(
            f"Page {page_number}: Tesseract {best_mode} ({len(best_tesseract)} chars) "
            f"— {reason} → Gemini Flash"
        )
        try:
            # Reutilizar imagem 200 DPI (já renderizada para Tesseract) — evita re-render
            gemini_image = image_bytes if image_bytes else _render_pdf_page_to_png_bytes(pdf_path, page_number, dpi=200)
            text, quality = await _extract_page_gemini_flash(gemini_image, page_number)
            logger.info(
                f"Page {page_number}: ✓ Gemini Flash ({len(text)} chars, q={quality:.2f})"
            )
            return text, quality
        except Exception as e:
            logger.warning(f"Page {page_number}: Gemini Flash falhou: {e}")

    # --- Fallback: qualquer texto disponível ---
    if best_tesseract:
        logger.info(
            f"Page {page_number}: ⚠ fallback Tesseract ({len(best_tesseract)} chars)"
        )
        return best_tesseract, _estimate_quality(best_tesseract)
    if native_text:
        return native_text, _estimate_quality(native_text)

    placeholder = f"[Página {page_number} — conteúdo não extraível]"
    logger.warning(f"Page {page_number}: ⚠ sem texto extraível")
    return placeholder, 0.0
