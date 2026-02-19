import re
import logging
from google import genai
from google.genai import types
from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

client = genai.Client(api_key=settings.gemini_api_key)

CHAT_MODEL = "gemini-2.5-flash"

# Keywords that indicate a query is too generic and needs clarification
GENERIC_INDICATORS = [
    r"\bqualquer\b", r"\btodos\b", r"\bgeral\b", r"\btudo\b",
    r"\bqualquer modelo\b", r"\bqualquer marca\b",
]

# Keywords indicating a specific model/component was mentioned
SPECIFIC_INDICATORS = [
    r"\bmodelo\b", r"\bmod\b", r"\bsérie\b", r"\bvrs\b",
    r"\bv\d", r"\b\d{3,}\b",  # model numbers
    r"\bgen\d\b", r"\b[a-z]{2,4}\d{3,}\b",  # alphanumeric model codes
]

SYSTEM_PROMPT = """Você é um assistente técnico especialista em elevadores da marca {brand_name}.
Você tem acesso ao conteúdo das apostilas e manuais técnicos desta marca, processados por IA.

REGRAS FUNDAMENTAIS:
1. Responda APENAS com base nas informações encontradas nos documentos recuperados.
2. Cite SEMPRE a fonte no final: "📄 Fonte: [nome do arquivo], Página [número]"
3. Se houver múltiplas fontes, cite todas.
4. Se a informação NÃO estiver nos documentos, diga claramente: "Esta informação não foi encontrada nos documentos disponíveis desta marca."
5. NUNCA invente especificações técnicas, valores elétricos, ou procedimentos.
6. Para circuitos e esquemas: descreva os componentes e conexões como estão documentados.
7. Seja preciso e técnico — os usuários são técnicos de elevadores.
8. Escreva em português claro, com pontuação completa e frases inteiras.
9. Quando útil, use Markdown simples (listas e subtítulos curtos) para organizar a resposta.

Contexto dos documentos:
{context}

Histórico da conversa:
{history}
"""

CLARIFICATION_PROMPT = """O usuário fez uma pergunta sobre elevadores {brand_name}, mas ela pode ser muito genérica.

Pergunta: {query}

Determine se você precisa de mais informações para dar uma resposta precisa.
Se sim, faça UMA pergunta de clarificação objetiva (ex: modelo, código, sintoma específico).
Se não precisar de esclarecimento, responda diretamente.

Responda APENAS com:
- "CLARIFY: [sua pergunta de clarificação]" — se precisar de mais info
- "PROCEED" — se puder responder com as informações atuais
"""


def _normalize_assistant_text(text: str) -> str:
    """Normalize assistant output to avoid broken spacing/punctuation."""
    cleaned = re.sub(r"\s+", " ", (text or "")).strip()
    if not cleaned:
        return ""

    cleaned = cleaned.replace(" ?", "?").replace(" .", ".").replace(" ,", ",")

    if cleaned.endswith(":"):
        return cleaned

    if not re.search(r"[.!?…]$", cleaned):
        cleaned += "."

    return cleaned


def _default_clarification_question(brand_name: str) -> str:
    return (
        f"Para eu te ajudar com precisão em {brand_name}, me informe o modelo exato do elevador "
        "(como aparece na etiqueta) e o código/erro exibido no painel, se houver."
    )


def _looks_like_bad_clarification(text: str) -> bool:
    """Detect incomplete or low-quality clarification outputs."""
    t = (text or "").strip()
    if not t:
        return True

    low = t.lower()
    if low in {"proceed", "ok", "certo", "entendi"}:
        return True

    # Clarification should have enough detail
    if len(t.split()) < 10:
        return True

    # Should look like a full question/request
    if not re.search(r"[?]$", t):
        return True

    # Reject common abbreviations/truncation artifacts
    if re.search(r"\belev\.?$", t.lower()) or "..." in t:
        return True

    # Require key diagnostic context terms
    lowered = t.lower()
    required_hits = sum(
        1 for token in ["modelo", "código", "erro", "painel", "etiqueta"] if token in lowered
    )
    if required_hits < 2:
        return True

    # Common truncation pattern: ends in connector/article
    if re.search(r"\b(de|do|da|dos|das|um|uma|e|ou|com|para|sobre|no|na|nos|nas)$", low):
        return True

    return False


def needs_clarification(query: str, chat_history: list[dict]) -> bool:
    """
    Determine if the query is too generic and needs clarification.
    Uses heuristics first, then Gemini if needed.
    """
    q = query.lower().strip()

    # Very short queries almost always need clarification
    if len(q.split()) <= 2:
        return True

    # Check if already in clarification flow (user already answered)
    if len(chat_history) >= 2:
        last_assistant = next(
            (m["content"] for m in reversed(chat_history) if m["role"] == "assistant"),
            ""
        )
        if "qual" in last_assistant.lower() and "?" in last_assistant:
            # User is answering a clarification question — proceed
            return False

    # Check for specific model indicators
    for pattern in SPECIFIC_INDICATORS:
        if re.search(pattern, q, re.IGNORECASE):
            return False

    # Check for generic indicators
    for pattern in GENERIC_INDICATORS:
        if re.search(pattern, q, re.IGNORECASE):
            return True

    return False


async def get_clarification_question(query: str, brand_name: str) -> str:
    """Ask Gemini to generate a smart clarification question."""
    try:
        prompt = CLARIFICATION_PROMPT.format(query=query, brand_name=brand_name)

        response = await client.aio.models.generate_content(
            model=CHAT_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.2, max_output_tokens=256),
        )

        text = (response.text or "").strip()
        if text.startswith("CLARIFY:"):
            question = text.replace("CLARIFY:", "", 1).strip()
            question = _normalize_assistant_text(question)
            if _looks_like_bad_clarification(question):
                return _default_clarification_question(brand_name)
            return question

        if text.strip().upper().startswith("PROCEED"):
            return None

        # Model can sometimes return plain question instead of CLARIFY prefix
        normalized = _normalize_assistant_text(text)
        if _looks_like_bad_clarification(normalized):
            return _default_clarification_question(brand_name)
        return normalized

        return None  # PROCEED

    except Exception as e:
        logger.error(f"Clarification error: {e}")
        return _default_clarification_question(brand_name)


async def generate_answer(
    query: str,
    brand_name: str,
    chunks: list[dict],
    chat_history: list[dict],
) -> tuple[str, list[dict]]:
    """
    Generate final answer using Gemini with retrieved context.
    Returns (answer_text, sources_list).
    """
    try:
        # Build context from chunks
        context_parts = []
        for i, chunk in enumerate(chunks, 1):
            context_parts.append(
                f"[Trecho {i}]\n"
                f"Arquivo: {chunk['source']}\n"
                f"Página: {chunk['page']}\n"
                f"Conteúdo: {chunk['text']}\n"
            )
        context = "\n---\n".join(context_parts) if context_parts else "Nenhum documento relevante encontrado."

        # Build history text
        history_parts = []
        for msg in chat_history[-6:]:  # last 3 turns
            role = "Técnico" if msg["role"] == "user" else "Assistente"
            history_parts.append(f"{role}: {msg['content']}")
        history = "\n".join(history_parts) if history_parts else "Início da conversa."

        system = SYSTEM_PROMPT.format(
            brand_name=brand_name,
            context=context,
            history=history,
        )

        full_prompt = f"{system}\n\nPergunta atual: {query}"

        response = await client.aio.models.generate_content(
            model=CHAT_MODEL,
            contents=full_prompt,
            config=types.GenerateContentConfig(
                temperature=0.1,
                max_output_tokens=2048,
            ),
        )

        answer = _normalize_assistant_text(response.text or "")
        if not answer:
            answer = "Não encontrei informação suficiente nos documentos desta marca para responder com segurança."

        # Extract sources from chunks used
        sources = [
            {
                "filename": c["source"],
                "page": c["page"],
                "doc_id": c.get("doc_id"),
                "score": round(c.get("rerank_score", c.get("score", 0)), 3),
            }
            for c in chunks
        ]

        return answer, sources

    except Exception as e:
        logger.error(f"Answer generation error: {e}")
        return (
            "Desculpe, ocorreu um erro ao gerar a resposta. Tente novamente.",
            [],
        )
