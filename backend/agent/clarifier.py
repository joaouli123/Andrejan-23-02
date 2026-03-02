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
# Maximum clarification rounds before forcing an answer
# ---------------------------------------------------------------------------
MAX_CLARIFICATION_ROUNDS = 3

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
    r"\b[a-z]{1,5}\s?-?\s?\d{1,5}[a-z]?\b",  # OVF10, XO 508, GEN2, LCB1, LCB2, RCB2, ADV-210
    r"\b\d{3,5}[a-z]{0,3}\b",                 # 560, 210dp
    r"\bgen\s?\d\b",                         # gen2, gen 2
    r"\b[a-z]{3}\d{4,}[a-z]*\b",              # JAA30171AAA, BAA21000S (Otis part numbers)
    r"\b(lcb[i12]|rcb\d|gscb|tcbc|gecb|gdcb)\b",  # Otis boards
    r"\b(otismatic|miconic|mag)\b",            # Otis model families
    r"\b(mrl|do\s?2000|mrds|ledo)\b",          # Otis equipment types
    r"\b(ovf\s?\d{1,2}|cvf|lvf|cfw\s?\d{2})\b",  # Otis drives
    r"\b(advz[aã]o|adv)\b",                   # ADV family
]

TECHNICAL_QUESTION_HINTS = [
    r"\bfalha\b", r"\berro\b", r"\bc[oó]digo\b", r"\bdefeito\b", r"\bproblema\b",
    r"\bn[aã]o\s+funciona\b", r"\bn[aã]o\s+liga\b", r"\bn[aã]o\s+sobe\b", r"\bn[aã]o\s+desce\b",
    r"\bn[aã]o\s+fecha\b", r"\bn[aã]o\s+abre\b", r"\babre\s+e\s+fecha\b",
    r"\bporta\b", r"\btrinco\b", r"\bintertrav\b", r"\bdw\b", r"\bdfc\b", r"\bes\b",
    r"\bliga[cç][aã]o\b", r"\besquema\b", r"\bplaca\b", r"\bdrive\b", r"\binversor\b",
    r"\bcalibra[cç][aã]o\b", r"\bajuste\b", r"\bparametr", r"\bconfigura", r"\bmanual\b",
    r"\bresgate\b", r"\bfreio\b", r"\bencoder\b", r"\bmotor\b", r"\bnivel", r"\bvibra",
]

# ---------------------------------------------------------------------------
# Known Otis equipment/model families → document mapping
# This helps the agent know what documents exist for what equipment
# ---------------------------------------------------------------------------
OTIS_KNOWLEDGE_MAP = {
    "gen2": {
        "docs": ["Manual GEN2.pdf", "Gen2 Comfort - Manual de serviços-1.pdf",
                  "Manual Otis Gen2 Confort-1.pdf", "MAG GEN2-1.pdf",
                  "Treinamento do produto Gen2C.pdf", "Manual  GEN2 Resgate.pdf",
                  "DIAGRAMA GEN2-1.pdf", "Diagrama Gen2 Confort Baa21000j-1.pdf",
                  "GEN 2 esquema.pdf", "GEN 2 MCS 220C GAA21000CJ.pdf"],
        "boards": ["GECB", "LCB2", "MCS220"],
        "drives": ["OVF20", "LVA"],
    },
    "ovf10": {
        "docs": ["Manual CVF - OVF10.pdf", "Calibração do OVF10.pdf",
                  "ADV DP COM OVF10 BAA21340K.pdf", "OVF10 por WEG CFW09.pdf"],
        "boards": ["LCB1", "LCBI", "LCB2"],
        "related": ["ADV-210", "CVF"],
    },
    "ovf20": {
        "docs": ["Manual LVF - OVF 20.pdf", "LFV OVF20 MNUAL DE AJUSTE.pdf",
                  "LCB2 OVF20 VF2 BAA21290AX.pdf", "ADV 210 com OVF20 (BAA21340R).pdf"],
        "boards": ["LCB2"],
    },
    "lcb1": {
        "docs": ["DIAGRAMA DE LCB1 PARA LCB2.pdf", "DIAGRAMA TROCA DE LCB1 POR LCB2.pdf",
                  "LCB1 POR LCB2 SUBSTITUICAO ATC 035.pdf",
                  "Diagrama ADV 210 LCBI.pdf", "ADV210DP - LCBI.pdf"],
        "upgrade": "LCB2",
    },
    "lcb2": {
        "docs": ["LCB2 Resumo.pdf", "WEG LCB2.pdf", "Manual URM LCB2.pdf",
                  "LCB2 OVF20 VF2 BAA21290AX.pdf"],
        "drives": ["OVF20", "CFW09", "CFW11"],
    },
    "lcbii": {
        "docs": ["LCBII NOVA-2.pdf", "Guia URM LCB II.pdf",
                  "VW2 CFW09 com LCBll-1.pdf", "Man CFW09 com LCBII.pdf",
                  "BAA21230AG_ADVDP LCBII.pdf"],
        "drives": ["CFW09", "VW2"],
    },
    "rcb2": {
        "docs": ["RCB2 Manual de Ajuste.pdf", "GUIA DE USO DA URM – RCB 2.PDF-3.pdf",
                  "Lista de IO RCB2 JAA30171AAA.pdf"],
    },
    "gecb": {
        "docs": ["Manual GECB gen2-1.pdf", "GECB+reference+2007.pdf",
                  "MANUAL GECB Guia de uso da URM (GAA30780CAA_Fsd1).pdf",
                  "MANUAL CHINES COM GECB-1.pdf"],
        "related": ["Gen2"],
    },
    "adv210": {
        "docs": ["ADV210DP - LCBI.pdf", "ADVZÃO 210 BOS 9693A.pdf",
                  "adv-210 baa21230b.pdf", "ADV 210 adevesao.pdf",
                  "ADV-210 BOS9693A.pdf", "ADV 210 com OVF20 (BAA21340R).pdf",
                  "ADV DP COM OVF10 BAA21340K.pdf",
                  "Diagrama Controle ADV 210 com OVF10 (BAA21340G).pdf"],
        "boards": ["LCBI", "LCB1", "LCB2", "LCBII"],
        "drives": ["OVF10", "OVF20"],
    },
    "mrl": {
        "docs": ["mrl.pdf", "MRL-W-Malha AbertaServiço[1].pdf", "MRL WEG FOD-BA.pdf",
                  "Diagrama Controle Otis 2000 VF_MRL (BAA21000B)-1.pdf"],
    },
    "do2000": {
        "docs": ["DO 2000.pdf", "Operador OTIS DO 2000.pdf", "Manual Operador DO2000.pdf"],
        "tipo": "operador de porta",
    },
    "xo508": {
        "docs": ["Otis+XO+508.pdf", "otis+XO+508+falhas.pdf"],
    },
    "otismatic": {
        "docs": ["OTISMATIC.pdf"],
    },
    "miconic_bx": {
        "docs": ["Esquema Miconic BX.pdf-1.pdf", "Manual BX_PT_BR_03.pdf",
                  "CONSULTA RÁPIDA_bx-1-1.pdf"],
    },
    "miconic_lx": {
        "docs": ["MANUAL MICONIC LX.pdf"],
    },
    "vw_vw2": {
        "docs": ["VW1_FOD.pdf", "otisVW2 WEG Malha Fechada.pdf",
                  "BAA21290BM VW2-2.pdf", "BAA21290CC VMW VW2-2.pdf"],
        "drives": ["CFW09", "WEG"],
    },
    "lva_ultra_drive": {
        "docs": ["Ultra drive lva -1.pdf", "manual do Ultra Drive.pdf",
                  "Manual de Ajuste LVA-1-3.pdf", "GEN2+LVA+BAA21000S-1.pdf"],
    },
    "cfw": {
        "docs": ["Manual CFW_11 Atualizado revisão 3 (2).pdf",
                  "ATC CFW700rev1.pdf", "OVF10 por WEG CFW09.pdf",
                  "VW2 CFW09 com LCBll-1.pdf", "Man CFW09 com LCBII.pdf",
                  "Malha Fechada VW2 MW2 cfw09.pdf"],
    },
    "gdcb_regen": {
        "docs": ["Otis-GDCB+REGEN.pdf", "Drive Regenerativo (GDCB - 55661).pdf",
                  "BAA21000H_fod (2)_diagrama Regen.pdf"],
    },
    "escada_rolante": {
        "docs": ["Otis escalera NCE manual portugues-1.pdf",
                  "Manual Escada Rolante NCE Corrimão.pdf",
                  "Otis escaleras Xizi diagramas.pdf",
                  "Otis Xizi escaleras digramas.pdf",
                  "Otis escaleras ecs 3 diagramas.pdf"],
    },
    "mag": {
        "docs": ["Mag completo.pdf", "Manual Mag ADV Total 2 pb.pdf",
                  "Mag ADV Total 2 pb.pdf", "MAG GEN2-1.pdf"],
    },
    "diagnostico_falhas": {
        "docs": ["Diagnóstico de Falhas Otis red1-1.pdf",
                  "Otis diversos falhas.pdf",
                  "Manual Diagnóstico de Falhas (Troubleshooting).pdf",
                  "manual geral otis (1).pdf"],
    },
}

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
12. Quando houver muitos modelos antigos e novos, diferencie explicitamente por **modelo, geração/série e placa/controlador**.
13. Se houver risco de confusão entre versões (ex: Gen1, Gen2, revisão de placa), destaque essa diferença antes do procedimento.
14. Se faltar identificação técnica mínima, faça uma pergunta curta e objetiva antes de recomendar ações.
15. Para sintoma "porta abre/fecha e não parte", priorize diagnóstico de **DW, DFC, contato de porta, trinco/intertravamento e cadeia de segurança (ES)** antes de sugerir qualquer outra inspeção.
16. Não sugerir automaticamente "cabo de tração" ou "contrapeso" nesse cenário sem evidência explícita no contexto recuperado.
17. Se o técnico perguntar explicitamente sobre entradas DW/DFC, SEMPRE responda com as entradas/sinais específicos e seus pontos de verificação no diagrama, sem disclaimers sobre "os termos não aparecem nos documentos".
18. Quando responder sobre Otis, SEMPRE complete a resposta inteira. Nunca deixe a resposta pela metade ou termine com "Com base nos sintomas" sem continuar.
19. Se os documentos encontrados vêm de VÁRIOS manuais diferentes (ex.: Gen2, ADV-210, OVF10), cite os mais relevantes e pergunte ao técnico qual equipamento específico ele está trabalhando.
20. Quando responder, mencione se há documentos RELACIONADOS disponíveis que podem complementar a resposta. Exemplo: "Também temos manual do RCB2 e do LCB2 caso precise consultar."
21. Se a busca retornou documentos de MAIS DE UM modelo/geração, NÃO misture as informações. Separe por modelo e pergunte ao técnico qual é o dele.
22. Idioma final obrigatório: **Português (Brasil)**. Se o conteúdo da fonte estiver em espanhol, inglês ou outro idioma, traduza tecnicamente para português.
23. Se houver texto com ruído de OCR, frases truncadas ou fora de contexto, reescreva de forma clara e coerente, sem inventar dados.
24. Preserve exatamente códigos, siglas técnicas, nomes de placas, modelos e valores numéricos (ex.: OVF10, LCB2, GECB, E015).

CONVENÇÃO DE NOMENCLATURA (OTIS) — REGRAS INVIOLÁVEIS:
- Quando a marca for **Otis**, trate a nomenclatura histórica como consistente entre gerações antigas e novas.
- **DW** (Door Warning) = sinal de **porta aberta** / detecção de posição de porta. É a entrada que indica que a porta está aberta ou em movimento.
- **DFC** (Door Fully Closed) = sinal de **porta totalmente fechada e travada**. É a entrada que confirma fechamento completo da porta (cabine e/ou pavimento, conforme diagrama).
- **ES** = sinal de **segurança** (cadeia de segurança / safety chain).
- NUNCA diga que "DW", "DFC" ou "ES" não existem, não são usados, ou não aparecem nos documentos Otis. Esses são termos-padrão da Otis usados em TODAS as gerações.
- NUNCA invente significados alternativos para DW (ex.: "Door Open", "Door Width"). Use SOMENTE as definições acima.
- Se o técnico perguntar sobre DW ou DFC, responda diretamente com base nos diagramas de porta disponíveis nos documentos.
- Para Otis, não substitua automaticamente esses termos por siglas de outras marcas (ex.: **PC**), pois isso pode gerar diagnóstico incorreto.
- Para sintomas de "porta abre/fecha e não parte", a verificação de **DFC** (porta fechada) e **DW** (porta aberta) são SEMPRE as PRIMEIRAS entradas a orientar o diagnóstico.

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

PORTUGUESE_REWRITE_PROMPT = """Você é um revisor técnico de documentação de elevadores.

Tarefa:
1. Garantir que a resposta final esteja em **português do Brasil**.
2. Se houver trechos em espanhol/inglês/outra língua, traduzir para português técnico.
3. Corrigir texto com ruído de OCR, frases quebradas ou sem contexto.
4. Manter o sentido técnico original e **não inventar informação**.
5. Preservar exatamente códigos e identificadores técnicos (modelos, placas, erros, valores).
6. Manter formato em Markdown e a seção de fontes (📄 Fonte) quando existir.

Marca: {brand_name}
Pergunta do técnico: {query}

Resposta atual para revisar:
{answer}

Retorne somente a versão final revisada em português.
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
1.1 Sempre que possível, peça também geração/série para separar modelos antigos e novos.
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
5. Se a marca for Otis e o tema envolver porta/segurança, preserve e priorize as siglas **DW**, **DFC** e **ES** na consulta final.

Exemplos:
- Pergunta original: "Como calibrar o drive?" → Resposta: "OVF10" → Busca: "calibração drive OVF10 procedimento"
- Pergunta original: "LED não acende" → Resposta: "caixa de inspeção Beneton" → Busca: "LED não acende caixa inspeção Beneton"  
- Pergunta original: "alterações ligação elétrica" → Resposta: "Controles CVF OVF10" → Busca: "alterações ligação elétrica Controles CVF OVF10"

Retorne APENAS a consulta de busca (uma linha), sem explicação.
"""


# ---------------------------------------------------------------------------
# Progressive questioning prompt — asks targeted follow-up based on
# what is already known vs what is still missing
# ---------------------------------------------------------------------------
PROGRESSIVE_QUESTION_PROMPT = """Você é um assistente técnico de elevadores {brand_name}.
Você está fazendo perguntas progressivas para identificar exatamente o equipamento do técnico.

O que já sabemos da conversa:
- Modelo/equipamento: {known_model}
- Placa/controlador: {known_board}
- Drive/inversor: {known_drive}
- Sintoma/erro: {known_symptom}
- Outros detalhes: {known_other}

O que ainda FALTA saber: {missing_info}

Rodada de perguntas: {round_number} de {max_rounds}

A busca nos manuais retornou estes documentos como possíveis fontes:
{found_docs}

REGRAS:
1. Faça UMA ÚNICA pergunta curta e direta que preencha a informação mais importante que está faltando.
2. Se falta MODELO: pergunte qual o modelo/geração do elevador (cite exemplos reais dos documentos encontrados).
3. Se falta PLACA: pergunte qual a placa/controlador (cite opções encontradas: LCB1, LCB2, LCBII, RCB2, GECB, etc.).
4. Se falta DRIVE: pergunte qual o drive/inversor (OVF10, OVF20, CFW09, CFW11, LVA, etc.).
5. Se falta SINTOMA: pergunte o que exatamente está acontecendo (código de erro, comportamento observado).
6. NÃO repita uma pergunta que já foi respondida na conversa.
7. Se esta é a última rodada ({round_number} de {max_rounds}), faça uma pergunta que ajude a FECHAR o diagnóstico.
8. TERMINE sempre com "?"
9. Máximo 2 linhas. Sem explicações extras.
10. Se os documentos encontrados mostram VARIANTES do mesmo modelo (ex: ADV-210 com LCBI vs LCBII), pergunte qual variante.

Responda APENAS com a pergunta (sem prefixo, sem explicação).
"""

DISAMBIGUATION_PROMPT = """Você é um assistente técnico de elevadores {brand_name}.
A busca retornou documentos de VÁRIOS modelos/equipamentos diferentes para a pergunta do técnico.

Pergunta do técnico: "{query}"

Documentos encontrados (por relevância):
{found_docs}

Os documentos parecem cobrir estes equipamentos distintos:
{equipment_list}

REGRAS:
1. Faça UMA pergunta curta listando os equipamentos encontrados e pedindo para o técnico escolher.
2. Use nomes claros dos equipamentos separados por vírgula.
3. TERMINE com "?"
4. Máximo 3 linhas.
5. Se um equipamento é claramente mais relevante que os outros, destaque-o no início.

Exemplo BOM: "Encontrei documentação para Gen2 com GECB, ADV-210 com LCB1 e OVF10. Qual desses é o equipamento que você está atendendo?"
Exemplo RUIM: "Qual modelo?"

Responda APENAS com a pergunta.
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


def _needs_portuguese_rewrite(text: str) -> bool:
    """Heuristic to detect non-PT or noisy outputs that should be rewritten."""
    if not text:
        return False

    low = text.lower()

    # Obvious OCR/noise symptoms
    if "�" in text or re.search(r"\b[a-z]{1,2}\s+[a-z]{1,2}\s+[a-z]{1,2}\b", low):
        return True

    # Spanish/English markers in sentence context
    foreign_markers = [
        r"\bfuente\b", r"\bpágina\b", r"\baver[ií]a\b", r"\bfalla\b", r"\busted\b", r"\bpuede\b",
        r"\bsource\b", r"\bpage\b", r"\bwarning\b", r"\bplease\b", r"\bcheck\b", r"\berror code\b",
    ]
    marker_hits = sum(1 for pattern in foreign_markers if re.search(pattern, low, re.IGNORECASE))
    if marker_hits >= 2:
        return True

    # If text uses "Fuente" citation style, convert/rewrite to PT style
    if re.search(r"📄\s*fuente", low):
        return True

    return False


async def _ensure_portuguese_technical_quality(answer: str, query: str, brand_name: str) -> str:
    """Translate/rewrite answer to clean PT-BR when needed, preserving technical fidelity."""
    normalized = _normalize_assistant_text(answer)
    if not normalized:
        return normalized

    if not _needs_portuguese_rewrite(normalized):
        return normalized

    try:
        prompt = PORTUGUESE_REWRITE_PROMPT.format(
            brand_name=brand_name,
            query=query,
            answer=normalized,
        )
        response = await client.aio.models.generate_content(
            model=CHAT_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.0,
                max_output_tokens=4096,
            ),
        )

        rewritten = _normalize_assistant_text(response.text or "")
        return rewritten or normalized
    except Exception as exc:
        logger.warning(f"Portuguese rewrite fallback due to error: {exc}")
        return normalized


def _default_clarification_question(brand_name: str) -> str:
    return (
        f"Para eu te responder com precisão em {brand_name}, me confirme o modelo/geração do elevador "
        "(como aparece na etiqueta), a placa/controlador e o código de erro, se houver."
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

    # Generic troubleshooting asks should clarify equipment/model first
    if re.search(r"\btroubleshooting\b", q, re.IGNORECASE):
        return True
    if re.search(r"\b(divers[oa]s?\s+falhas|falhas\s+divers[oa]s?)\b", q, re.IGNORECASE):
        return True

    # Check for generic indicators only on short queries (≤4 words)
    # Longer queries like "manual geral otis falhas comuns" have enough context
    if len(q.split()) <= 4:
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
    alternative_docs: list[str] | None = None,
) -> tuple[str, list[dict]]:
    """
    Generate final answer using Gemini with retrieved context.
    Returns (answer_text, sources_list).
    If alternative_docs is provided, mention them at the end.
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

        # Add instruction about alternative docs if available
        alt_instruction = ""
        if alternative_docs:
            alt_list = ", ".join(alternative_docs[:5])
            alt_instruction = (
                f"\n\nINSTRUÇÃO ADICIONAL: Ao final da resposta, mencione que também existem "
                f"documentos relacionados disponíveis: {alt_list}. "
                f"Pergunte se o técnico quer consultar algum deles."
            )

        full_prompt = f"{system}{alt_instruction}\n\nPergunta atual: {query}"

        response = await client.aio.models.generate_content(
            model=CHAT_MODEL,
            contents=full_prompt,
            config=types.GenerateContentConfig(
                temperature=0.1,
                max_output_tokens=4096,
            ),
        )

        answer = _normalize_assistant_text(response.text or "")
        if not answer:
            answer = "Não encontrei informação suficiente nos documentos desta marca para responder com segurança."
        answer = await _ensure_portuguese_technical_quality(answer, query, brand_name)

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


# ---------------------------------------------------------------------------
# Progressive intelligence functions
# ---------------------------------------------------------------------------

def count_clarification_rounds(history: list[dict]) -> int:
    """
    Count how many consecutive clarification rounds (question → answer) have occurred.
    A round = assistant asked a question, then user replied.
    """
    if not history:
        return 0

    count = 0
    i = len(history) - 1
    while i >= 1:
        asst_msg = history[i] if history[i]["role"] == "assistant" else None
        user_msg = history[i - 1] if history[i - 1]["role"] == "user" else None

        # Go back looking for assistant question → user answer pairs
        if not asst_msg:
            # Look for the pattern: user answers, then assistant question before that
            for j in range(i, -1, -1):
                if history[j]["role"] == "assistant" and "?" in history[j].get("content", ""):
                    count += 1
                    i = j - 1
                    break
                elif history[j]["role"] == "user":
                    continue
                else:
                    break
            else:
                break
        elif "?" in asst_msg.get("content", ""):
            count += 1
            i -= 2
        else:
            break

    return count


def extract_known_context(query: str, history: list[dict]) -> dict:
    """
    Extract all technical context accumulated from the entire conversation.
    Returns dict with: model, board, drive, symptom, error_code, other.
    """
    all_user_text = " ".join(
        m.get("content", "") for m in (history or []) if m.get("role") == "user"
    )
    all_user_text = f"{all_user_text} {query}".strip().lower()

    context = {
        "model": None,
        "board": None,
        "drive": None,
        "symptom": None,
        "error_code": None,
        "other": [],
    }

    # --- Extract model ---
    model_patterns = [
        (r"\b(gen\s?\d\w*)\b", "Gen2"),
        (r"\b(adv\s?-?\s?\d{3}\w*)\b", None),
        (r"\b(advz[aã]o)\b", "ADVzão"),
        (r"\b(mrl)\b", "MRL"),
        (r"\b(otismatic)\b", "OTISMATIC"),
        (r"\b(miconic\s*(bx|lx)?)\b", None),
        (r"\b(mag)\b", "MAG"),
        (r"\b(xo\s?508)\b", "XO 508"),
        (r"\b(do\s?2000)\b", "DO 2000"),
        (r"\b(mrds)\b", "MRDS"),
        (r"\b(ledo)\b", "LEDO"),
        (r"\b(vw\s?\d?)\b", None),
        (r"\b(escada\s*rolante|nce)\b", "Escada Rolante"),
        (r"\b(bx)\b", "BX"),
    ]
    for pat, name in model_patterns:
        m = re.search(pat, all_user_text, re.IGNORECASE)
        if m:
            context["model"] = name or m.group(1).upper().strip()
            break

    # --- Extract board ---
    board_patterns = [
        (r"\b(gecb)\b", "GECB"),
        (r"\b(gdcb)\b", "GDCB"),
        (r"\b(lcb\s?ii|lcb\s?2|lcbii)\b", None),
        (r"\b(lcb\s?[i1]|lcbi)\b", None),
        (r"\b(rcb\s?\d)\b", None),
        (r"\b(gscb)\b", "GSCB"),
        (r"\b(tcbc)\b", "TCBC"),
        (r"\b(mcs\s?\d{3})\b", None),
    ]
    for pat, name in board_patterns:
        m = re.search(pat, all_user_text, re.IGNORECASE)
        if m:
            raw = name or m.group(1).upper().strip()
            # Normalize LCB II → LCBII, LCB 2 → LCB2
            raw = re.sub(r"\s+", "", raw)
            context["board"] = raw
            break

    # --- Extract drive ---
    drive_patterns = [
        (r"\b(ovf\s?\d{1,2})\b", None),
        (r"\b(cvf)\b", "CVF"),
        (r"\b(lvf)\b", "LVF"),
        (r"\b(lva|ultra\s*drive)\b", "LVA"),
        (r"\b(cfw\s?\d{2})\b", None),
        (r"\b(weg)\b", "WEG"),
    ]
    for pat, name in drive_patterns:
        m = re.search(pat, all_user_text, re.IGNORECASE)
        if m:
            raw = name or m.group(1).upper().strip()
            raw = re.sub(r"\s+", "", raw)
            context["drive"] = raw
            break

    # --- Extract symptom ---
    symptom_patterns = [
        (r"(porta\s+abre\s+e\s+fecha)", "porta abre e fecha"),
        (r"(n[aã]o\s+parte|n[aã]o\s+anda|n[aã]o\s+funciona)", None),
        (r"(n[aã]o\s+sobe|n[aã]o\s+desce)", None),
        (r"(n[aã]o\s+fecha|n[aã]o\s+abre)", None),
        (r"(n[aã]o\s+liga)", "não liga"),
        (r"(trem?e|vibra|ru[ií]do)", None),
        (r"(para\s+entre\s+andares|para\s+no\s+meio)", "para entre andares"),
        (r"(desnivelad|desenivel)", "desnivelamento"),
    ]
    for pat, name in symptom_patterns:
        m = re.search(pat, all_user_text, re.IGNORECASE)
        if m:
            context["symptom"] = name or m.group(1).strip()
            break

    # --- Extract error code ---
    error_patterns = [
        r"\berro\s+([A-Za-z]?\d{2,4})\b",
        r"\bc[oó]digo\s+([A-Za-z]?\d{2,4})\b",
        r"\bfalha\s+([A-Za-z]?\d{2,4})\b",
        r"\b(e\d{3})\b",
        r"\b(uv\d{1,2})\b",
        r"\b(oc\d{1,2})\b",
        r"\b(ol\d{1,2})\b",
    ]
    for pat in error_patterns:
        m = re.search(pat, all_user_text, re.IGNORECASE)
        if m:
            context["error_code"] = m.group(1).upper().strip()
            break

    # --- Extract part numbers ---
    pn_match = re.search(r"\b([a-z]{3}\d{4,}[a-z]*)\b", all_user_text, re.IGNORECASE)
    if pn_match:
        context["other"].append(f"Part number: {pn_match.group(1).upper()}")

    return context


def determine_missing_info(known: dict) -> list[str]:
    """
    Determine what critical information is still missing for a precise diagnosis.
    Returns list of missing items in priority order.
    """
    missing = []

    if not known.get("model"):
        missing.append("modelo/geração do elevador")

    if not known.get("board") and not known.get("drive"):
        missing.append("placa/controlador ou drive/inversor")

    if not known.get("symptom") and not known.get("error_code"):
        missing.append("sintoma observado ou código de erro")

    return missing


async def generate_progressive_question(
    query: str,
    brand_name: str,
    known_context: dict,
    round_number: int,
    chunks: list[dict],
    history: list[dict],
) -> str | None:
    """
    Generate a targeted follow-up question based on what's known and what's missing.
    Returns the question string, or None if no more questions are needed.
    """
    if round_number > MAX_CLARIFICATION_ROUNDS:
        return None

    missing = determine_missing_info(known_context)
    if not missing:
        return None  # We have enough info

    # Build doc list for context
    doc_list_parts = []
    seen_docs = set()
    for c in chunks[:15]:
        source = c.get("source", "")
        display = source.split("/")[-1] if "/" in source else source
        if display not in seen_docs:
            seen_docs.add(display)
            doc_list_parts.append(f"- {display} (score: {c.get('score', 0):.2f})")
    found_docs_text = "\n".join(doc_list_parts[:10]) if doc_list_parts else "Nenhum"

    try:
        prompt = PROGRESSIVE_QUESTION_PROMPT.format(
            brand_name=brand_name,
            known_model=known_context.get("model") or "não informado",
            known_board=known_context.get("board") or "não informado",
            known_drive=known_context.get("drive") or "não informado",
            known_symptom=known_context.get("symptom") or known_context.get("error_code") or "não informado",
            known_other=", ".join(known_context.get("other", [])) or "nenhum",
            missing_info=", ".join(missing),
            round_number=round_number,
            max_rounds=MAX_CLARIFICATION_ROUNDS,
            found_docs=found_docs_text,
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
        logger.info(f"Progressive question (round {round_number}): '{text}'")

        if _looks_like_bad_clarification(text):
            # Fallback: generate from known missing info
            if "modelo" in missing[0]:
                return (
                    "Qual o modelo ou geração do elevador que você está atendendo, "
                    "como Gen2, ADV-210, MRL, OVF10, Miconic BX ou outro?"
                )
            elif "placa" in missing[0]:
                return (
                    "Qual a placa ou controlador instalado nesse elevador, "
                    "como LCB1, LCB2, LCBII, RCB2, GECB ou outro?"
                )
            elif "sintoma" in missing[0]:
                return (
                    "Qual o sintoma exato ou código de erro que está aparecendo? "
                    "Por exemplo: porta não fecha, erro no display, elevador não parte."
                )
            return None

        return text

    except Exception as e:
        logger.error(f"Progressive question error: {e}")
        return None


async def generate_disambiguation_question(
    query: str,
    brand_name: str,
    chunks: list[dict],
) -> str | None:
    """
    When search results span multiple distinct equipment types,
    generate a question to disambiguate.
    """
    # Group chunks by document
    doc_groups = {}
    for c in chunks[:20]:
        source = c.get("source", "")
        display = source.split("/")[-1] if "/" in source else source
        if display not in doc_groups:
            doc_groups[display] = {
                "score": c.get("score", 0),
                "text_preview": c.get("text", "")[:100],
            }

    if len(doc_groups) < 2:
        return None  # Only one document, no disambiguation needed

    # Extract equipment identifiers from document names
    equipment_set = set()
    doc_list = []
    for doc_name, info in sorted(doc_groups.items(), key=lambda x: x[1]["score"], reverse=True):
        doc_list.append(f"- {doc_name} (score: {info['score']:.2f})")
        # Guess equipment from filename
        name_lower = doc_name.lower()
        for equip in ["gen2", "ovf10", "ovf20", "lcb1", "lcb2", "lcbii", "rcb2",
                       "gecb", "adv", "mrl", "do2000", "xo508", "mag", "otismatic",
                       "miconic", "vw", "lva", "cfw", "gdcb", "escada", "nce", "bx"]:
            if equip in name_lower.replace(" ", "").replace("-", ""):
                equipment_set.add(equip.upper())

    if len(equipment_set) < 2:
        return None  # Documents are about the same equipment

    found_docs_text = "\n".join(doc_list[:8])
    equipment_list = ", ".join(sorted(equipment_set))

    try:
        prompt = DISAMBIGUATION_PROMPT.format(
            brand_name=brand_name,
            query=query,
            found_docs=found_docs_text,
            equipment_list=equipment_list,
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

        if _looks_like_bad_clarification(text):
            return (
                f"Encontrei documentação sobre {equipment_list}. "
                f"Qual desses equipamentos você está trabalhando?"
            )
        return text

    except Exception as e:
        logger.error(f"Disambiguation error: {e}")
        return (
            f"Encontrei documentação sobre {equipment_list}. "
            f"Qual desses equipamentos você está trabalhando?"
        )


def get_alternative_docs_for_context(known_context: dict, chunks: list[dict]) -> list[str]:
    """
    Given what we know about the user's equipment, find related documents
    from the OTIS_KNOWLEDGE_MAP that might be useful but weren't in the search results.
    """
    if not known_context:
        return []

    alternatives = set()
    model = (known_context.get("model") or "").lower().replace(" ", "").replace("-", "")
    board = (known_context.get("board") or "").lower().replace(" ", "")
    drive = (known_context.get("drive") or "").lower().replace(" ", "")

    # Find matching knowledge map entries
    for key, info in OTIS_KNOWLEDGE_MAP.items():
        key_clean = key.lower().replace("_", "").replace("-", "")
        if model and (model in key_clean or key_clean in model):
            # Add related boards/drives as alternatives
            for related_key in info.get("boards", []) + info.get("drives", []):
                related_clean = related_key.lower().replace(" ", "")
                for k2, info2 in OTIS_KNOWLEDGE_MAP.items():
                    if related_clean in k2.lower().replace("_", ""):
                        for doc in info2.get("docs", [])[:2]:
                            alternatives.add(doc)
            if info.get("related"):
                for r in info["related"]:
                    alternatives.add(f"Documentos sobre {r}")

    # Don't include docs already in the search results
    result_docs = set()
    for c in chunks:
        source = c.get("source", "")
        display = source.split("/")[-1] if "/" in source else source
        result_docs.add(display)

    return [a for a in alternatives if a not in result_docs][:5]
