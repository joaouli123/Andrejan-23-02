"""
Scan the Otis Qdrant collection to extract all unique document filenames,
models, boards, error codes mentioned in the indexed content.
Uses the /api/query endpoint with targeted queries to discover content.
"""
import requests
import json
import time
import re
from collections import Counter, defaultdict

API = "https://api.uxcodedev.com.br"

def login():
    r = requests.post(f"{API}/auth/login", data={"username":"admin@andreja.com","password":"admin123"}, timeout=10)
    return r.json().get("access_token","")

def query(q, token, top_k=20):
    r = requests.post(f"{API}/api/query", json={"question":q,"brandFilter":"otis","topK":top_k},
                      headers={"Authorization":f"Bearer {token}","Content-Type":"application/json"}, timeout=60)
    if r.status_code == 200:
        return r.json()
    return {}

# Targeted queries to discover unique doc filenames via sources
DISCOVERY_QUERIES = [
    "calibração drive OVF10",
    "OVF20 ajuste parâmetros",
    "Gen2 Comfort manual serviço",
    "Gen2 LVA diagrama elétrico",
    "LCB1 LCB2 diagrama migração",
    "RCB2 entradas saídas IO",
    "MAG manual completo falhas",
    "OTISMATIC controlador",
    "ATC 043 eliminar ACP",
    "D0510 caixa inspeção Beneton",
    "D0506 boletim técnico",
    "Manual resgate Gen2",
    "XO 508 falha erro",
    "URM 311 uso manual",
    "cadeia segurança ES elevador",
    "porta DW DFC contato trinco",
    "inversor frequência motor",
    "placa controlador GSCB TCBC",
    "MRL machine room less",
    "Gen2 Comfort código erro lista",
    "Miconic manual porta operador",
    "CVF controle variável frequência",
    "painel inspeção carro topo",
    "frenagem regenerativa resistor",
    "LVA BAA21000S diagrama",
    "error code fault UV OV overcurrent",
    "safety chain inspection mode",
    "door operator GAL mechanics",
    "encoder motor feedback",
    "GECB board remote monitoring",
    "OH overheat thermal protection",
    "contactor relay safety",
    "programação parâmetros URM",
    "lista IO placa LCB entradas saídas",
    "manual instalação Gen2 Premier",
    "diagrama unifilar força potência",
    "nivelamento aprendizado viagem",
    "botão chamada hall pavimento",
    "velocidade nominal contrato",
    "peso carga capacidade balanceamento",
]

def main():
    token = login()
    all_sources = Counter()
    all_models = Counter()
    all_boards = Counter()
    all_errors = Counter()
    doc_content_samples = defaultdict(list)

    MODEL_RE = re.compile(r'\b(gen\s*2|gen\s*1|gen2|gen1|ovf\s*10|ovf\s*20|ovf10|ovf20|cvf|mrl|xo\s*508|otismatic|mag|lva|premier|comfort|miconic|2000|3300|skyline)\b', re.I)
    BOARD_RE = re.compile(r'\b(lcb\s*[i12]|lcbi{1,2}|rcb\s*2|rcb2|gscb|gecb|tcbc?|mcp\s*\d+|atc|do\s*\d+|urm|regen)\b', re.I)
    ERROR_RE = re.compile(r'\b(uv\d?|ov\d?|oc\d?|oh\d?|ol\d?|ef\d?|gf\d?|dc\d?|mc\d?|fu\d?|volt\s*dc|e\d{3}|erro?\s+\d+|fault\s+\d+|code?\s+\d+)\b', re.I)

    print(f"Scanning Otis knowledge base with {len(DISCOVERY_QUERIES)} queries...\n")

    for i, q in enumerate(DISCOVERY_QUERIES):
        result = query(q, token)
        sources = result.get("sources", [])
        answer = result.get("answer", "")

        for s in sources:
            fn = s.get("filename", "?")
            all_sources[fn] += 1
            # Sample content
            if len(doc_content_samples[fn]) < 3:
                doc_content_samples[fn].append(q)

        # Extract from answer
        for m in MODEL_RE.findall(answer):
            all_models[m.strip().upper()] += 1
        for b in BOARD_RE.findall(answer):
            all_boards[b.strip().upper()] += 1
        for e in ERROR_RE.findall(answer):
            all_errors[e.strip().upper()] += 1

        if (i+1) % 10 == 0:
            print(f"  [{i+1}/{len(DISCOVERY_QUERIES)}] Found {len(all_sources)} unique docs so far...")
        time.sleep(0.3)

    # Report
    print(f"\n{'='*80}")
    print(f"  OTIS KNOWLEDGE BASE SCAN RESULTS")
    print(f"{'='*80}")

    print(f"\n📄 UNIQUE DOCUMENTS FOUND ({len(all_sources)}):\n")
    for fn, count in all_sources.most_common():
        topics = doc_content_samples.get(fn, [])
        topics_str = " | ".join(topics[:3])
        print(f"  {fn:<60} (hits: {count:>2}) -> {topics_str}")

    print(f"\n🔧 MODELS FOUND ({len(all_models)}):")
    for m, c in all_models.most_common():
        print(f"  {m:<20} ({c} mentions)")

    print(f"\n🔌 BOARDS/CONTROLLERS FOUND ({len(all_boards)}):")
    for b, c in all_boards.most_common():
        print(f"  {b:<20} ({c} mentions)")

    print(f"\n⚠️ ERROR CODES FOUND ({len(all_errors)}):")
    for e, c in all_errors.most_common():
        print(f"  {e:<20} ({c} mentions)")

    # Save for test generation
    data = {
        "documents": list(all_sources.keys()),
        "models": list(all_models.keys()),
        "boards": list(all_boards.keys()),
        "errors": list(all_errors.keys()),
        "doc_topics": {k: v for k, v in doc_content_samples.items()},
    }
    with open("scripts/otis_knowledge_map.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\n✅ Knowledge map saved to scripts/otis_knowledge_map.json")

if __name__ == "__main__":
    main()
