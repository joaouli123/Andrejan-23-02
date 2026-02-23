"""Test OVF10 search on the VPS"""
import paramiko
import os

VPS_HOST = "72.61.217.143"
VPS_USER = "root"
VPS_PASS = "Proelast1608@"
HOST_KEY_B64 = "AAAAC3NzaC1lZDI1NTE5AAAAIO3C7DkqvmcKI72+gYlrUxOyi5IK6qQCGTvYckDC5WiH"

# Build host key
import paramiko.ed25519key, base64
pub_bytes = base64.b64decode(HOST_KEY_B64)
host_key = paramiko.Ed25519Key(data=pub_bytes)

ssh = paramiko.SSHClient()
ssh.get_host_keys().add(VPS_HOST, "ssh-ed25519", host_key)
ssh.connect(VPS_HOST, username=VPS_USER, password=VPS_PASS)

test_script = r'''
import sys, json
sys.path.insert(0, "/app")
from ingestion.embedder import search_brand

queries = [
    "calibracao OVF10 drive",
    "Controles CVF OVF10",
    "ATC C.07.10 Otis",
    "alteracoes ligacao eletrica operacao segura equipamento",
    "procedimento calibracao drive OVF10",
]

for q in queries:
    print(f"\n=== Query: {q} ===")
    results = search_brand("otis", q, top_k=10)
    for r in results[:5]:
        src = r.get("source","")
        display = src.split("/")[-1] if "/" in src else src
        pg = r.get("page","")
        sc = r.get("score",0)
        txt = r.get("text","")[:80].replace("\n"," ")
        print(f"  [{sc:.3f}] {display} p{pg}: {txt}")

# Also check Qdrant directly for OVF10 points
print("\n=== Qdrant points for OVF10 doc ===")
from qdrant_client import QdrantClient
qc = QdrantClient(host="qdrant", port=6333)
from qdrant_client.models import Filter, FieldCondition, MatchText
scroll_result = qc.scroll(
    collection_name="brand_otis",
    scroll_filter=Filter(
        should=[
            FieldCondition(key="doc_filename", match=MatchText(text="OVF10")),
        ]
    ),
    limit=20,
    with_payload=True,
    with_vectors=False,
)
points, _ = scroll_result
print(f"Found {len(points)} points for OVF10")
for p in points:
    payload = p.payload or {}
    fn = payload.get("doc_filename","")
    pg = payload.get("page_number","")
    txt = payload.get("text","")[:100].replace("\n"," ")
    print(f"  ID={p.id} | {fn} p{pg}: {txt}")
'''

# Write test script to VPS and run
stdin, stdout, stderr = ssh.exec_command(f"cat > /tmp/test_ovf10.py << 'PYEOF'\n{test_script}\nPYEOF")
stdout.channel.recv_exit_status()

stdin, stdout, stderr = ssh.exec_command("docker exec andreja_backend python /tmp/test_ovf10.py 2>&1", timeout=30)
# /tmp is on host, need to copy to container
stdin2, stdout2, stderr2 = ssh.exec_command("docker cp /tmp/test_ovf10.py andreja_backend:/tmp/test_ovf10.py && docker exec andreja_backend python /tmp/test_ovf10.py 2>&1", timeout=30)
output = stdout2.read().decode()
print(output)

ssh.close()
