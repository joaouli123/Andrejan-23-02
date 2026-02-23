"""Quick fix for e2e test - handle tuple return."""
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
from ingestion.gemini_vision import rerank_chunks
from agent.clarifier import generate_answer

async def test():
    query = "O led vermelho de emergencia nao acende na caixa de inspecao Beneton. Qual o procedimento para corrigir?"
    
    # Search
    chunks = search_brand("otis", query, top_k=15)
    print(f"Search: {len(chunks)} results, #1={chunks[0]['source']} ({chunks[0]['score']:.4f})")
    
    # Rerank  
    reranked = await rerank_chunks(query, chunks)
    reranked = reranked[:7]
    print(f"Rerank: {len(reranked)} results")
    for i,c in enumerate(reranked):
        print(f"  [{i+1}] {c['source']} (rerank={c.get('rerank_score','?')})")
    
    # Answer (returns tuple)
    answer, sources = await generate_answer(query, "Otis", reranked, [])
    print(f"\n=== ANSWER ===\n{answer}\n")
    print(f"Sources: {json.dumps(sources, indent=2, ensure_ascii=False)}")
    
    # Verify
    has_d0510 = "D0510" in answer or any("D0510" in str(s) for s in sources)
    has_procedure = any(kw in answer.lower() for kw in ["ins", "bloco", "desconectar", "inverter", "fiação", "beneton"])
    print(f"\nD0510 cited: {has_d0510}")
    print(f"Procedure in answer: {has_procedure}")
    if has_procedure:
        print("SUCCESS!")

asyncio.run(test())
'''

def run():
    host_key = paramiko.Ed25519Key(data=base64.b64decode(VPS_KEY_DATA))
    ssh = paramiko.SSHClient()
    ssh.get_host_keys().add(VPS_HOST, VPS_KEY_TYPE, host_key)
    ssh.connect(VPS_HOST, username=VPS_USER, password=VPS_PASS)

    sftp = ssh.open_sftp()
    with sftp.file("/root/andreja2/e2e_v3.py", "w") as f:
        f.write(SCRIPT)
    sftp.close()

    cmds = [
        "docker cp /root/andreja2/e2e_v3.py andreja_backend:/app/e2e_v3.py",
        "docker exec andreja_backend python /app/e2e_v3.py 2>&1",
    ]
    for cmd in cmds:
        stdin, stdout, stderr = ssh.exec_command(cmd, timeout=120)
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
