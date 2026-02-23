"""
Test the improved chat pipeline:
1. Specific query (D0510 Beneton) — should answer directly
2. Ambiguous query (generic LED problem) — should clarify or still find
3. Progressive search: vague query → user gives model → finds answer
"""
import paramiko
import base64

VPS_HOST = "72.61.217.143"
VPS_USER = "root"
VPS_PASS = "Proelast1608@"
VPS_KEY_TYPE = "ssh-ed25519"
VPS_KEY_DATA = "AAAAC3NzaC1lZDI1NTE5AAAAIO3C7DkqvmcKI72+gYlrUxOyi5IK6qQCGTvYckDC5WiH"

SCRIPT = r'''
import sys, os, json, asyncio
sys.path.insert(0, "/app")
os.environ.setdefault("DATABASE_URL", "sqlite:////app/data/andreja.db")

from ingestion.embedder import search_brand
from agent.clarifier import (
    analyze_search_confidence,
    generate_smart_clarification,
    build_enriched_query_from_history,
    generate_answer,
)
from ingestion.gemini_vision import rerank_chunks

async def test_scenario(name, query, history=None):
    print(f"\n{'='*70}")
    print(f"SCENARIO: {name}")
    print(f"Query: {query}")
    if history:
        print(f"History: {len(history)} messages")
    print(f"{'='*70}")
    
    h = history or []
    
    # Enrich query from history
    if h and len(h) >= 2:
        enriched = await build_enriched_query_from_history(query, "Otis", h)
        print(f"Enriched query: {enriched}")
    else:
        enriched = query
    
    # Search
    chunks = search_brand("otis", enriched, top_k=20)
    print(f"\nSearch: {len(chunks)} results")
    for i, c in enumerate(chunks[:8]):
        src = c['source'].split('/')[-1] if '/' in c['source'] else c['source']
        print(f"  [{i+1}] {c['score']:.4f} {src}")
    
    # Confidence
    confidence = analyze_search_confidence(chunks, query)
    print(f"\nConfidence: {confidence['reason']} (top={confidence['top_score']:.3f}, docs={len(confidence['unique_docs'])})")
    
    if not confidence["confident"]:
        # Smart clarification
        question = await generate_smart_clarification(query, "Otis", chunks, confidence, h)
        print(f"\nCLARIFICATION: {question}")
        return question
    else:
        # Rerank + answer
        reranked = await rerank_chunks(query, chunks)
        reranked = reranked[:7]
        print(f"\nReranked: {len(reranked)} chunks")
        for i, c in enumerate(reranked[:3]):
            src = c['source'].split('/')[-1] if '/' in c['source'] else c['source']
            print(f"  [{i+1}] {src}")
        
        answer, sources = await generate_answer(query, "Otis", reranked, h)
        print(f"\nANSWER: {answer[:300]}...")
        print(f"Sources: {[s['filename'].split('/')[-1] for s in sources[:3]]}")
        return None

async def main():
    # Test 1: Specific query — should answer directly
    await test_scenario(
        "Specific D0510 query",
        "O led vermelho de emergencia nao acende na caixa de inspecao Beneton. Qual o procedimento?"
    )
    
    # Test 2: Generic query about a problem — may need clarification
    await test_scenario(
        "Generic LED query",
        "O led nao acende"
    )
    
    # Test 3: Progressive - user answers with model info
    history_progressive = [
        {"role": "user", "content": "o led nao acende"},
        {"role": "assistant", "content": "Encontrei informacoes sobre LEDs em varios documentos. Qual modelo ou placa do elevador voce esta trabalhando?"},
        {"role": "user", "content": "e a caixa de inspecao Beneton"},
    ]
    await test_scenario(
        "Progressive: user gave model after clarification",
        "e a caixa de inspecao Beneton",
        history=history_progressive,
    )

    # Test 4: Query with model code in it
    await test_scenario(
        "Query with model code GEN2",
        "como fazer resgate manual no GEN2?"
    )

    print("\n\nDONE!")

asyncio.run(main())
'''

def run():
    host_key = paramiko.Ed25519Key(data=base64.b64decode(VPS_KEY_DATA))
    ssh = paramiko.SSHClient()
    ssh.get_host_keys().add(VPS_HOST, VPS_KEY_TYPE, host_key)
    ssh.connect(VPS_HOST, username=VPS_USER, password=VPS_PASS)

    sftp = ssh.open_sftp()
    with sftp.file("/root/andreja2/test_smart.py", "w") as f:
        f.write(SCRIPT)
    sftp.close()

    cmds = [
        "docker cp /root/andreja2/test_smart.py andreja_backend:/app/test_smart.py",
        "docker exec andreja_backend python /app/test_smart.py 2>&1",
    ]
    for cmd in cmds:
        stdin, stdout, stderr = ssh.exec_command(cmd, timeout=180)
        exit_code = stdout.channel.recv_exit_status()
        output = stdout.read().decode()
        if output.strip():
            print(output)
        err = stderr.read().decode()
        if err.strip() and exit_code != 0:
            print(f"ERR: {err[-500:]}")
    ssh.close()

if __name__ == "__main__":
    run()
