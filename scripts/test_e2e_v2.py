"""
E2E test: search + rerank + answer generation directly.
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
from ingestion.gemini_vision import rerank_chunks
from agent.clarifier import generate_answer

async def test():
    query = "O led vermelho de emergencia nao acende na caixa de inspecao Beneton. Qual o procedimento para corrigir?"
    print(f"Query: {query}\n")
    
    # Step 1: Search
    print("=== STEP 1: Search ===")
    chunks = search_brand("otis", query, top_k=15)
    print(f"Search returned {len(chunks)} chunks")
    for i, c in enumerate(chunks):
        is_d0510 = "D0510" in c.get("source", "")
        marker = " *** D0510 ***" if is_d0510 else ""
        print(f"  [{i+1}] score={c['score']:.4f} source={c['source']}{marker}")
    
    # Step 2: Rerank
    print("\n=== STEP 2: Rerank ===")
    reranked = await rerank_chunks(query, chunks)
    reranked = reranked[:7]
    print(f"After rerank: {len(reranked)} chunks")
    for i, c in enumerate(reranked):
        is_d0510 = "D0510" in c.get("source", "")
        marker = " *** D0510 ***" if is_d0510 else ""
        rs = c.get("rerank_score", "?")
        print(f"  [{i+1}] rerank_score={rs} source={c['source']}{marker}")
    
    # Step 3: Generate answer
    print("\n=== STEP 3: Generate Answer ===")
    answer_data = await generate_answer(query, "Otis", reranked, [])
    answer = answer_data if isinstance(answer_data, str) else answer_data.get("answer", str(answer_data))
    print(f"\nAnswer:\n{answer}")
    
    # Check success
    print("\n=== RESULT ===")
    d0510_in_search = any("D0510" in c.get("source","") for c in chunks)
    d0510_in_rerank = any("D0510" in c.get("source","") for c in reranked)
    answer_has_content = any(kw in answer for kw in ["D0510", "Beneton", "INS", "bloco", "desconectar", "inverter"])
    
    print(f"D0510 in search results: {d0510_in_search}")
    print(f"D0510 in reranked results: {d0510_in_rerank}")
    print(f"Answer contains D0510 content: {answer_has_content}")
    
    if answer_has_content:
        print("\n SUCCESS!")
    else:
        print("\n NEEDS REVIEW")

asyncio.run(test())
'''

def run():
    host_key = paramiko.Ed25519Key(data=base64.b64decode(VPS_KEY_DATA))
    ssh = paramiko.SSHClient()
    ssh.get_host_keys().add(VPS_HOST, VPS_KEY_TYPE, host_key)
    ssh.connect(VPS_HOST, username=VPS_USER, password=VPS_PASS)

    sftp = ssh.open_sftp()
    with sftp.file("/root/andreja2/e2e_test.py", "w") as f:
        f.write(SCRIPT)
    sftp.close()

    cmds = [
        "docker cp /root/andreja2/e2e_test.py andreja_backend:/app/e2e_test.py",
        "docker exec andreja_backend python /app/e2e_test.py 2>&1",
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
