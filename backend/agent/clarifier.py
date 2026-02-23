import re
import logging
from google import genai
from google.genai import types
from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

client = genai.Client(api_key=settings.gemini_api_key)

CHAT_MODEL = "gemini-2.5-flash"

# ---------------------------------------------------------------------------
# Patterns
# ---------------------------------------------------------------------------
GENERIC_INDICATORS = [
    r"\bqualquer\b", r"\btodos\b", r"\bgeral\b", r"\btudo\b",
    r"\bqualquer modelo\b", r"\bqualquer marca\b",
]

SPECIFIC_INDICATORS = [
    r"\bmodelo\b", r"\bmod\b", r"\bsérie\b", r"\bvrs\b",
    r"\bv\d", r"\b\d{3,}\b",
    r"\bgen\d\b", r"\b[a-z]{2,4}\d{3,}\b",
]

MODEL_CODE_PATTERNS = [
    r"\b[a-z]{1,5}\s?-?\s?\d{2,5}[a-z]?\b",  # OVF10, XO 508, GEN2, ADV-210
    r"\b\d{3,5}[a-z]{0,3}\b",                 # 560, 210dp
    r"\bgen\s?\d\b",                         # gen2, gen 2
]

TECHNICAL_QUESTION_HINTS = [
    r"\bfalha\b", r"\berro\b", r"\bc[oó]digo\b", r"\bdefeito\b", r"\bproblema\b",
    r"\bn[aã]o\s+funciona\b", r"\bn[aã]o\s+liga\b", r"\bn[aã]o\s+sobe\b", r"\bn[aã]o\s+desce\b",
    r"\bliga[cç][aã]o\b", r"\besquema\b", r"\bplaca\b", r"\bdrive\b", r"\binversor\b",
    r"\bcalibra[cç][aã]o\b", r"\bajuste\b", r"\bparametr", r"\bconfigura", r"\bmanual\b",
]

# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """Você é um assistente técnico especialista em elevadores da marca {brand_name}.
Você tem acesso ao conteúdo das apostilas e manuais técnicos desta marca, processados por IA.

REGRAS FUNDAMENTAIS:
1. Responda com base nas informações encontradas nos documentos recuperados.
2. Cite SEMPRE a fonte no final: "📄 Fonte: [nome do arquivo], Página [número]"
3. Se houver múltiplas fontes, cite todas.
4. Se encontrou documentos sobre o modelo/placa perguntado, SEMPRE apresente as informações disponíveis,
   mesmo que não respondam exatamente à pergunta. Exemplo: se perguntaram sobre "ligação elétrica do OVF10"
   e o documento é sobre "calibração do OVF10", apresente o que tem sobre o OVF10 e informe que não há
   informação específica sobre ligação elétrica neste documento.
5. SOMENTE diga "não encontrada" se NÃO houver NENHUM documento relevante sobre o modelo/placa no contexto.
6. NUNCA invente especificações técnicas, valores elétricos, ou procedimentos.
7. Para circuitos e esquemas: descreva os componentes e conexões como estão documentados.
8. Seja preciso e técnico — os usuários são técnicos de elevadores.
9. Escreva em português claro, com pontuação completa e frases inteiras.
10. Se os documentos encontrados cobrem VÁRIOS temas mas nenhum exatamente o que foi perguntado,
    mencione o que FOI encontrado e pergunte se algum desses temas é o que o técnico procura.
11. Se o conteúdo encontrado parece ser de um modelo/equipamento DIFERENTE do perguntado,
    informe isso claramente. Exemplo: "Encontrei informações sobre o OVF20, mas não sobre o OVF10.
    Deseja ver as informações do OVF20?"

FORMATAÇÃO OBRIGATÓRIA (Markdown):
- Use **negrito** para termos-chave, nomes de componentes e ações importantes.
- Use listas numeradas (1. 2. 3.) para procedimentos passo-a-passo.
- Use listas com bullet (- ou •) para listar componentes, sintomas ou opções.
- Use ### subtítulos para separar seções quando a resposta tiver mais de um tópico.
- Separe parágrafos com uma linha em branco.
- NUNCA escreva tudo em um único parágrafo — quebre a resposta em blocos visuais.
- Coloque a fonte (📄) em uma linha separada no final.

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

SMART_CLARIFICATION_PROMPT = """Você é um assistente técnico de elevadores {brand_name}.
O técnico perguntou: "{query}"

A busca nos manuais retornou resultados de VÁRIOS documentos diferentes, sem um match forte.
Motivo da incerteza: {confidence_reason}
Os documentos encontrados foram:
{found_docs}

O técnico provavelmente precisa de ajuda com um modelo/placa/equipamento específico,
mas a pergunta dele pode se aplicar a vários modelos.

REGRAS OBRIGATÓRIAS:
1. Faça UMA pergunta curta para identificar o modelo/placa/equipamento exato.
2. A pergunta DEVE ser uma frase completa que TERMINA com "?"
3. NÃO use parênteses, NÃO dê exemplos dentro de parênteses.
4. Se quiser listar opções, use "como" ou "por exemplo" seguido dos nomes separados por vírgula, e TERMINE com "?"
5. Máximo 2 linhas. Seja direto.
6. NÃO faça mais de uma pergunta.
7. Se o motivo é "terms_not_found", pergunte se o nome do modelo/equipamento está correto,
   pois às vezes o nome no manual é diferente do nome popular.

Exemplo BOM: "Qual o modelo do controlador que você está trabalhando, como GEN2, OVF20 ou MRL?"
Exemplo RUIM: "Qual o modelo do controlador (por exemplo, GEN2, OVF20)?"

Responda APENAS com a pergunta (sem prefixo, sem explicação).
"""

PROGRESSIVE_SEARCH_PROMPT = """Analise o histórico desta conversa técnica sobre elevadores {brand_name}
e construa uma consulta de busca otimizada.

Histórico:
{history}

Pergunta/resposta atual: {query}

REGRAS:
1. Combine TODAS as informações relevantes numa frase de busca.
2. Se o técnico respondeu com um modelo/placa (ex: "OVF10", "GEN2", "LCB2"), 
   combine com a pergunta ORIGINAL que ele fez antes.
3. Inclua: modelo, placa, código de erro, sintoma, procedimento — tudo que foi mencionado.
4. Se o técnico só disse "sim" ou "ok", use a pergunta original sem mudança.

Exemplos:
- Pergunta original: "Como calibrar o drive?" → Resposta: "OVF10" → Busca: "calibração drive OVF10 procedimento"
- Pergunta original: "LED não acende" → Resposta: "caixa de inspeção Beneton" → Busca: "LED não acende caixa inspeção Beneton"  
- Pergunta original: "alterações ligação elétrica" → Resposta: "Controles CVF OVF10" → Busca: "alterações ligação elétrica Controles CVF OVF10"

Retorne APENAS a consulta de busca (uma linha), sem explicação.
"""


def _normalize_assistant_text(text: str) -> str:
    """Normalize assistant output while preserving markdown formatting."""
    if not text:
        return ""

    cleaned = text.strip()

    # Remove excessive blank lines (3+ → 2)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    # Clean trailing spaces on each line
    cleaned = re.sub(r"[ \t]+\n", "\n", cleaned)
    # Fix broken punctuation spacing
    cleaned = cleaned.replace(" ?", "?").replace(" .", ".").replace(" ,", ",")

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

    if len(t.split()) < 5:
        return True

    # Must end with "?" — it's supposed to be a question
    if not t.endswith("?"):
        return True

    # Unbalanced parentheses = truncated
    if t.count("(") != t.count(")"):
        return True

    # Ends with article/preposition = truncated mid-sentence
    if re.search(r"\b(de|do|da|dos|das|um|uma|e|ou|com|para|sobre|no|na|nos|nas)$", low):
        return True

    return False


def _has_model_or_code_hint(text: str) -> bool:
    q = (text or "").lower()
    for pattern in MODEL_CODE_PATTERNS:
        if re.search(pattern, q, re.IGNORECASE):
            return True
    return False


def should_require_model_clarification(query: str, chat_history: list[dict]) -> bool:
    """
    Enforce model/board/code clarification for technical troubleshooting queries
    when user didn't provide identifying details yet.
    """
    q = (query or "").strip().lower()
    if not q:
        return False

    # If user already provided model/code in this message, no clarification needed.
    if _has_model_or_code_hint(q):
        return False

    # If user is answering a previous assistant question about model/placa,
    # and this turn contains an identifier, proceed directly.
    if chat_history:
        last_assistant = next(
            (m.get("content", "") for m in reversed(chat_history) if m.get("role") == "assistant"),
            "",
        )
        ask_about_model = bool(re.search(r"modelo|placa|controlador|c[oó]digo", last_assistant.lower()))
        if ask_about_model and _has_model_or_code_hint(q):
            return False

    # If previous USER messages already contain model/code, don't ask again.
    previous_user_text = " ".join(
        m.get("content", "")
        for m in (chat_history or [])
        if m.get("role") == "user"
    )
    if _has_model_or_code_hint(previous_user_text):
        return False

    # Only enforce this for technical troubleshooting-like questions.
    is_technical = any(re.search(p, q, re.IGNORECASE) for p in TECHNICAL_QUESTION_HINTS)
    if not is_technical:
        return False

    # For very short replies after a question (e.g. "sim", "isso") don't force here.
    if len(q.split()) <= 2:
        return False

    return True


# ---------------------------------------------------------------------------
# Search confidence analysis
# ---------------------------------------------------------------------------

def analyze_search_confidence(chunks: list[dict], query: str) -> dict:
    """
    Analyze search results to determine if we have a confident answer
    or need to ask for clarification.

    Returns dict with:
        - confident: bool — True if we can answer directly
        - reason: str — why we're not confident
        - unique_docs: list of unique document filenames found
        - top_score: float — highest score
        - score_spread: float — difference between top and bottom scores
        - terms_in_results: bool — whether queried model/terms appear in results
    """
    if not chunks:
        return {
            "confident": False,
            "reason": "no_results",
            "unique_docs": [],
            "top_score": 0.0,
            "score_spread": 0.0,
            "terms_in_results": False,
        }

    # Unique documents in results
    unique_docs = list(dict.fromkeys(c.get("source", "") for c in chunks))
    scores = [c.get("score", 0) for c in chunks]
    top_score = max(scores)
    min_score = min(scores)
    score_spread = top_score - min_score

    # Score of the top result relative to second-best from a DIFFERENT doc
    top_doc = chunks[0].get("source", "")
    second_doc_score = 0.0
    for c in chunks[1:]:
        if c.get("source", "") != top_doc:
            second_doc_score = c.get("score", 0)
            break

    gap_to_second_doc = top_score - second_doc_score if second_doc_score else top_score

    # --- Check if queried terms actually appear in the results ---
    # This is critical: sometimes the search returns high-scoring results
    # that are semantically similar but don't actually contain the model/code
    # the user asked about.
    from ingestion.embedder import _extract_search_keywords
    search_terms = _extract_search_keywords(query)
    terms_in_results = True  # default to True if no specific terms
    if search_terms:
        terms_found = False
        for c in chunks[:15]:
            combined_text = (c.get("text", "") + " " + c.get("source", "")).lower()
            for term in search_terms:
                if term.lower() in combined_text:
                    terms_found = True
                    break
                # Also check without spaces/dots
                term_compact = re.sub(r'[.\s\-]', '', term.lower())
                text_compact = re.sub(r'[.\s\-]', '', combined_text)
                if len(term_compact) >= 3 and term_compact in text_compact:
                    terms_found = True
                    break
            if terms_found:
                break
        terms_in_results = terms_found

    base_result = {
        "unique_docs": unique_docs,
        "top_score": top_score,
        "score_spread": score_spread,
        "terms_in_results": terms_in_results,
    }

    # --- Confidence heuristics ---

    # If we have specific terms and they appear in results → strong match
    if terms_in_results and top_score >= 0.70:
        return {**base_result, "confident": True, "reason": "strong_match_with_terms"}

    # Strong match: top score is high and clearly ahead
    if top_score >= 0.75:
        return {**base_result, "confident": True, "reason": "strong_match"}

    # Good match with clear leader
    if top_score >= 0.68 and gap_to_second_doc >= 0.03:
        return {**base_result, "confident": True, "reason": "clear_leader"}

    # Specific terms were found even with moderate scores → answer with what we have
    if terms_in_results and top_score >= 0.55:
        return {**base_result, "confident": True, "reason": "terms_found_moderate_score"}

    # Query has specific terms but they don't appear in ANY result
    # This means we couldn't find what they asked about
    if search_terms and not terms_in_results:
        return {**base_result, "confident": False, "reason": "terms_not_found"}

    # Many documents with similar scores = ambiguous (common with 150+ PDFs)
    if len(unique_docs) >= 5 and score_spread < 0.05:
        return {**base_result, "confident": False, "reason": "too_many_similar_docs"}

    # Low scores overall
    if top_score < 0.60:
        return {**base_result, "confident": False, "reason": "low_scores"}

    # Moderate scores, no clear winner among many docs
    if len(unique_docs) >= 4 and gap_to_second_doc < 0.02:
        return {**base_result, "confident": False, "reason": "ambiguous_multi_doc"}

    # Default: proceed
    return {**base_result, "confident": True, "reason": "acceptable"}


async def generate_smart_clarification(
    query: str,
    brand_name: str,
    chunks: list[dict],
    confidence: dict,
    history: list[dict],
) -> str | None:
    """
    Generate a smart clarification question based on search results.
    Returns the question string, or None if no clarification needed.
    """
    # Don't re-ask if we already asked in the last 2 assistant messages
    if history and len(history) >= 2:
        recent_assistant_msgs = [
            m["content"] for m in history[-4:] if m["role"] == "assistant"
        ]
        if recent_assistant_msgs and "?" in recent_assistant_msgs[-1]:
            # The user is answering our previous question — proceed with search
            return None

    reason = confidence.get("reason", "")
    unique_docs = confidence.get("unique_docs", [])

    # Build list of found documents for prompt context
    doc_list_parts = []
    seen_docs = set()
    for c in chunks[:15]:
        source = c.get("source", "")
        # Clean up path prefixes for display
        display = source.split("/")[-1] if "/" in source else source
        if display not in seen_docs:
            seen_docs.add(display)
            doc_list_parts.append(f"- {display} (score: {c.get('score', 0):.2f})")

    found_docs_text = "\n".join(doc_list_parts[:10]) if doc_list_parts else "Nenhum"

    try:
        prompt = SMART_CLARIFICATION_PROMPT.format(
            brand_name=brand_name,
            query=query,
            found_docs=found_docs_text,
            confidence_reason=reason,
        )

        response = await client.aio.models.generate_content(
            model=CHAT_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.3,
                max_output_tokens=500,
            ),
        )

        text = _normalize_assistant_text(response.text or "")
        logger.info(f"Smart clarification raw: '{text}'")

        if _looks_like_bad_clarification(text):
            logger.warning(f"Bad clarification detected, using fallback. Text was: '{text}'")
            # Fallback based on reason
            if reason == "terms_not_found":
                return (
                    f"Não encontrei documentos com esse termo exato nos manuais. "
                    f"Pode verificar o nome/modelo correto? "
                    f"Às vezes o nome no manual é diferente do nome popular do equipamento."
                )
            elif reason == "too_many_similar_docs":
                return (
                    f"Encontrei informações em vários documentos sobre esse tema. "
                    f"Para ser mais preciso, qual modelo ou placa do elevador você está trabalhando?"
                )
            elif reason == "low_scores":
                return (
                    f"Não encontrei uma correspondência forte nos manuais. "
                    f"Pode me dar mais detalhes, como o modelo do elevador, "
                    f"o código de erro no painel, ou a placa específica?"
                )
            else:
                return _default_clarification_question(brand_name)
        return text

    except Exception as e:
        logger.error(f"Smart clarification error: {e}")
        return _default_clarification_question(brand_name)


async def build_enriched_query_from_history(
    query: str,
    brand_name: str,
    history: list[dict],
) -> str:
    """
    Build an optimized search query from the conversation history.
    Combines model info, symptoms, codes from the whole conversation.
    Uses both a fast heuristic and Gemini for enrichment.
    """
    if not history or len(history) < 2:
        return query

    # --- Fast heuristic: combine all user messages ---
    user_messages = [m["content"] for m in history if m["role"] == "user"]
    # Add current query
    all_user_text = " ".join(user_messages) + " " + query
    # Remove duplicated words while preserving order
    seen_words = set()
    unique_parts = []
    for word in all_user_text.split():
        low = word.lower()
        if low not in seen_words and len(low) > 1:
            seen_words.add(low)
            unique_parts.append(word)
    heuristic_query = " ".join(unique_parts)

    # Extract key terms from current user query (model codes, alphanumeric IDs)
    # These MUST appear in the enriched result
    # Normalize: remove dots, dashes, accents so "C.07.10" → "c0710", "OVF-10" → "ovf10"
    current_key_terms = set()
    for word in query.split():
        clean = re.sub(r"[().,;:!?\-/]", "", word).strip()
        if clean and (
            re.match(r"(?i)[A-Z0-9]{2,}", clean)  # OVF10, GEN2, LCB2, CVF, ATC, c0710
            or re.match(r"\d+", clean)              # numeric codes
            or len(clean) >= 4                      # significant words
        ):
            current_key_terms.add(clean.lower())

    # Use Gemini to make a cleaner version
    history_parts = []
    for msg in history[-8:]:
        role = "Técnico" if msg["role"] == "user" else "Assistente"
        history_parts.append(f"{role}: {msg['content']}")
    history_text = "\n".join(history_parts)

    try:
        prompt = PROGRESSIVE_SEARCH_PROMPT.format(
            brand_name=brand_name,
            history=history_text,
            query=query,
        )

        response = await client.aio.models.generate_content(
            model=CHAT_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.0,
                max_output_tokens=200,
            ),
        )

        enriched = (response.text or "").strip()
        # Sanity: single line, not too short, not too long
        if enriched and 5 < len(enriched) < 300 and "\n" not in enriched:
            # CRITICAL: check that key terms from current query are preserved
            enriched_lower = enriched.lower()
            missing_terms = [t for t in current_key_terms if t not in enriched_lower]
            if missing_terms:
                # Gemini dropped important terms — append them
                enriched = enriched + " " + " ".join(missing_terms)
                logger.info(f"Enriched query (patched missing {missing_terms}): '{query}' -> '{enriched}'")
            else:
                logger.info(f"Enriched query: '{query}' -> '{enriched}'")
            return enriched
        else:
            logger.info(f"Enriched query (heuristic): '{query}' -> '{heuristic_query}'")
            return heuristic_query

    except Exception as e:
        logger.warning(f"Query enrichment failed, using heuristic: {e}")
        return heuristic_query


# ---------------------------------------------------------------------------
# Original functions (backward compat)
# ---------------------------------------------------------------------------

def needs_clarification(query: str, chat_history: list[dict]) -> bool:
    """
    Quick heuristic check if query is too short/generic.
    NOTE: The main clarification logic is now in analyze_search_confidence
    which runs AFTER search to make smarter decisions.
    """
    q = query.lower().strip()

    # FIRST: If user is answering our clarification, NEVER re-ask
    # This is critical — "Simm", "OVF10", "GEN2" are valid answers
    if chat_history and len(chat_history) >= 2:
        last_assistant = next(
            (m["content"] for m in reversed(chat_history) if m["role"] == "assistant"),
            ""
        )
        if "?" in last_assistant:
            # The last thing the assistant said was a question — user is answering
            return False

    # Very short queries with no history context need clarification
    if len(q.split()) <= 2:
        return True

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

        normalized = _normalize_assistant_text(text)
        if _looks_like_bad_clarification(normalized):
            return _default_clarification_question(brand_name)
        return normalized

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
            source = chunk["source"]
            display = source.split("/")[-1] if "/" in source else source
            context_parts.append(
                f"[Trecho {i}]\n"
                f"Arquivo: {display}\n"
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

        # Extract sources from chunks used (clean display names)
        sources = []
        seen_sources = set()
        for c in chunks:
            source = c["source"]
            display = source.split("/")[-1] if "/" in source else source
            key = f"{display}-{c['page']}"
            if key not in seen_sources:
                seen_sources.add(key)
                sources.append({
                    "filename": display,
                    "page": c["page"],
                    "doc_id": c.get("doc_id"),
                    "score": round(c.get("rerank_score", c.get("score", 0)), 3),
                })

        return answer, sources

    except Exception as e:
        logger.error(f"Answer generation error: {e}")
        return (
            "Desculpe, ocorreu um erro ao gerar a resposta. Tente novamente.",
            [],
        )
