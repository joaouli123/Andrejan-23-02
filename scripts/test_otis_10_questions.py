"""
Test 10 varied Otis questions against the RAG API.
Questions go from short/generic → specific, to validate:
1. Agent asks for clarification on vague questions
2. Agent responds correctly with proper DW/DFC/ES nomenclature
3. Agent provides complete answers with sources
"""
import requests
import json
import time
import sys

API_URL = "https://api.uxcodedev.com.br/api/query"

QUESTIONS = [
    # === FASE 1: Perguntas CURTAS e GENÉRICAS (agente deve pedir mais info) ===
    {
        "id": 1,
        "question": "erro no elevador",
        "expected_behavior": "CLARIFY - deve pedir modelo/placa/código de erro",
        "category": "GENÉRICA CURTA"
    },
    {
        "id": 2,
        "question": "porta não fecha",
        "expected_behavior": "CLARIFY - deve pedir modelo/geração antes de diagnosticar",
        "category": "GENÉRICA TÉCNICA"
    },
    {
        "id": 3,
        "question": "como calibrar o drive?",
        "expected_behavior": "CLARIFY - deve perguntar qual drive (OVF10, OVF20, etc)",
        "category": "GENÉRICA TÉCNICA"
    },

    # === FASE 2: Perguntas com MODELO mas sem detalhe do problema ===
    {
        "id": 4,
        "question": "Gen2 com LCB2 dando problema",
        "expected_behavior": "CLARIFY - tem modelo mas falta sintoma/código específico",
        "category": "MODELO SEM DETALHE"
    },
    {
        "id": 5,
        "question": "OVF10 não funciona",
        "expected_behavior": "CLARIFY ou RESPONDER com diagnóstico geral do OVF10",
        "category": "MODELO VAGO"
    },

    # === FASE 3: Perguntas ESPECÍFICAS (agente deve responder direto) ===
    {
        "id": 6,
        "question": "Otis Gen2 LVA com LCB2: porta abre e fecha 2 vezes e o carro não parte. Quais entradas DW/DFC devo verificar primeiro?",
        "expected_behavior": "ANSWER - deve citar DW, DFC, cadeia de segurança, verificações de porta com fontes",
        "category": "ESPECÍFICA COMPLETA"
    },
    {
        "id": 7,
        "question": "Qual o procedimento de calibração do drive OVF10?",
        "expected_behavior": "ANSWER - deve trazer procedimento do documento 'Calibracao do OVF10.pdf'",
        "category": "ESPECÍFICA MODELO"
    },
    {
        "id": 8,
        "question": "Quais são as entradas e saídas da placa RCB2 JAA30171AAA?",
        "expected_behavior": "ANSWER - deve trazer I/O list do documento 'Lista de IO RCB2 JAA30171AAA.pdf'",
        "category": "ESPECÍFICA PLACA"
    },
    {
        "id": 9,
        "question": "Como migrar a ligação elétrica da LCB1 para LCB2?",
        "expected_behavior": "ANSWER - deve trazer info do 'DIAGRAMA DE LCB1 PARA LCB2.pdf'",
        "category": "ESPECÍFICA MIGRAÇÃO"
    },
    {
        "id": 10,
        "question": "Erro UV1 no drive OVF10, o que pode ser?",
        "expected_behavior": "ANSWER - deve citar undervoltage DC Bus, possíveis causas",
        "category": "ESPECÍFICA ERRO"
    },
]


def test_question(q: dict, history: list = None) -> dict:
    """Send a question to the RAG API and return the result."""
    payload = {
        "question": q["question"],
        "brandFilter": "otis",
        "topK": 10,
        "conversationHistory": history or [],
    }

    try:
        start = time.time()
        resp = requests.post(API_URL, json=payload, timeout=120)
        elapsed = time.time() - start

        if resp.status_code != 200:
            return {
                "status": "ERROR",
                "code": resp.status_code,
                "answer": resp.text[:500],
                "elapsed": round(elapsed, 1),
            }

        data = resp.json()
        return {
            "status": "OK",
            "answer": data.get("answer", ""),
            "sources": data.get("sources", []),
            "docs_found": data.get("documentsFound", 0),
            "search_time": data.get("searchTime", 0),
            "elapsed": round(elapsed, 1),
        }
    except Exception as e:
        return {"status": "EXCEPTION", "answer": str(e), "elapsed": 0}


def classify_response(answer: str) -> str:
    """Classify if the response is a clarification request or an answer."""
    low = answer.lower()
    clarify_signals = [
        "me confirme", "me informe", "qual modelo", "qual o modelo",
        "qual a placa", "qual o código", "qual controlador",
        "pode me dizer", "me diga", "preciso saber",
        "para te responder", "para eu te ajudar",
        "me confirme o modelo", "qual geração",
        "para te responder com precisão",
        "preciso destes dados",
        "me informe primeiro",
    ]
    has_question = "?" in answer
    has_clarify = any(s in low for s in clarify_signals)
    has_source = "📄" in answer or "fonte:" in low
    has_procedure = any(w in low for w in ["1.", "2.", "3.", "passo", "procedimento", "verifique", "verificar"])

    if has_clarify and not has_source:
        return "🟡 CLARIFICATION"
    elif has_source or has_procedure:
        return "🟢 ANSWER"
    elif has_question and not has_source:
        return "🟡 CLARIFICATION"
    else:
        return "🔵 PARTIAL"


def truncate(text: str, max_len: int = 500) -> str:
    if len(text) <= max_len:
        return text
    return text[:max_len] + "... [TRUNCADO]"


def main():
    print("=" * 80)
    print("  TESTE DE 10 PERGUNTAS OTIS — RAG API")
    print(f"  API: {API_URL}")
    print(f"  Brand: otis")
    print("=" * 80)

    results = []

    for q in QUESTIONS:
        print(f"\n{'─' * 80}")
        print(f"  Q{q['id']} [{q['category']}]")
        print(f"  Pergunta: {q['question']}")
        print(f"  Esperado: {q['expected_behavior']}")
        print(f"{'─' * 80}")

        result = test_question(q)
        classification = classify_response(result.get("answer", ""))

        print(f"\n  ⏱️  Tempo: {result['elapsed']}s")
        print(f"  📊 Status: {result['status']}")
        print(f"  🏷️  Classificação: {classification}")

        if result.get("sources"):
            src_names = [s.get("filename", "?") for s in result["sources"][:3]]
            print(f"  📄 Fontes: {', '.join(src_names)}")

        print(f"\n  💬 Resposta:")
        for line in truncate(result.get("answer", "")).split("\n"):
            print(f"     {line}")

        results.append({
            "id": q["id"],
            "category": q["category"],
            "question": q["question"],
            "expected": q["expected_behavior"],
            "classification": classification,
            "answer_preview": truncate(result.get("answer", ""), 300),
            "sources": [s.get("filename", "?") for s in result.get("sources", [])[:3]],
            "elapsed": result["elapsed"],
        })

        # Small delay between questions
        time.sleep(1)

    # === SUMMARY ===
    print(f"\n\n{'=' * 80}")
    print("  RESUMO FINAL")
    print(f"{'=' * 80}")

    clarify_count = sum(1 for r in results if "CLARIFICATION" in r["classification"])
    answer_count = sum(1 for r in results if "ANSWER" in r["classification"])
    partial_count = sum(1 for r in results if "PARTIAL" in r["classification"])

    print(f"\n  🟡 Pedidos de Clarificação: {clarify_count}")
    print(f"  🟢 Respostas Completas:     {answer_count}")
    print(f"  🔵 Parciais:                {partial_count}")
    print(f"  ⏱️  Tempo médio:             {sum(r['elapsed'] for r in results) / len(results):.1f}s")

    print(f"\n  {'ID':<4} {'Categoria':<25} {'Classificação':<20} {'Esperado':<10} {'Match?':<6}")
    print(f"  {'─'*4} {'─'*25} {'─'*20} {'─'*10} {'─'*6}")

    correct = 0
    for r in results:
        expected_type = "CLARIFY" if "CLARIFY" in r["expected"] else "ANSWER"
        actual_type = "CLARIFY" if "CLARIFICATION" in r["classification"] else "ANSWER"
        match = "✅" if expected_type == actual_type else "❌"
        if expected_type == actual_type:
            correct += 1
        print(f"  Q{r['id']:<3} {r['category']:<25} {r['classification']:<20} {expected_type:<10} {match}")

    accuracy = (correct / len(results)) * 100
    print(f"\n  🎯 Precisão do comportamento: {correct}/{len(results)} ({accuracy:.0f}%)")
    print(f"{'=' * 80}")


if __name__ == "__main__":
    main()
