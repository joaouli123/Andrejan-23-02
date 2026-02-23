"""Diagnose why OVF10 is not in final results after enrichment + rerank"""
import paramiko
import base64

VPS_HOST = "72.61.217.143"
VPS_USER = "root"
VPS_PASS = "Proelast1608@"
HOST_KEY_B64 = "AAAAC3NzaC1lZDI1NTE5AAAAIO3C7DkqvmcKI72+gYlrUxOyi5IK6qQCGTvYckDC5WiH"

host_key = paramiko.Ed25519Key(data=base64.b64decode(HOST_KEY_B64))
ssh = paramiko.SSHClient()
ssh.get_host_keys().add(VPS_HOST, "ssh-ed25519", host_key)
ssh.connect(VPS_HOST, username=VPS_USER, password=VPS_PASS)

test_script = r'''
import asyncio, sys, os
sys.path.insert(0, "/app")
os.environ.setdefault("DATABASE_URL", "sqlite:////app/data/andreja.db")

async def test():
    from agent.clarifier import build_enriched_query_from_history
    from ingestion.embedder import search_brand
    from ingestion.gemini_vision import rerank_chunks

    # Simulate the conversation history
    history = [
        {"role": "user", "content": "Quais alteracoes especificas devem ser feitas na ligacao eletrica para garantir a operacao segura do equipamento?"},
        {"role": "assistant", "content": "Para eu te ajudar com precisao em Otis, me informe o modelo exato do elevador (como aparece na etiqueta) e o codigo/erro exibido no painel, se houver."},
    ]
    
    query = "Controles CVF (OVF10)"
    
    # Step 1: Build enriched query
    enriched = await build_enriched_query_from_history(query, "Otis", history)
    print(f"ENRICHED QUERY: '{enriched}'")
    
    # Step 2: Search with enriched query
    chunks = search_brand("otis", enriched, top_k=20)
    print(f"\nSEARCH RESULTS (top 10):")
    for i, c in enumerate(chunks[:10]):
        src = c.get("source","").split("/")[-1]
        print(f"  [{i}] [{c.get('score',0):.3f}] {src} p{c.get('page','')} | {c.get('text','')[:60]}")
    
    # Step 3: Rerank with enriched query
    reranked = await rerank_chunks(enriched, chunks)
    print(f"\nRERANKED (enriched query):")
    for i, c in enumerate(reranked[:7]):
        src = c.get("source","").split("/")[-1]
        print(f"  [{i}] rerank={c.get('rerank_score',0)} [{c.get('score',0):.3f}] {src} p{c.get('page','')}")
    
    # Step 4: Also test reranking with original query for comparison
    chunks2 = search_brand("otis", enriched, top_k=20)
    reranked2 = await rerank_chunks(query, chunks2)
    print(f"\nRERANKED (original query '{query}'):")
    for i, c in enumerate(reranked2[:7]):
        src = c.get("source","").split("/")[-1]
        print(f"  [{i}] rerank={c.get('rerank_score',0)} [{c.get('score',0):.3f}] {src} p{c.get('page','')}")

asyncio.run(test())
'''

stdin, stdout, stderr = ssh.exec_command(f"cat > /tmp/test_diag.py << 'PYEOF'\n{test_script}\nPYEOF")
stdout.channel.recv_exit_status()

stdin2, stdout2, stderr2 = ssh.exec_command(
    "docker cp /tmp/test_diag.py andreja_backend:/tmp/test_diag.py && "
    "docker exec andreja_backend python /tmp/test_diag.py 2>&1",
    timeout=60
)
output = stdout2.read().decode()
print(output[-3000:])
ssh.close()
