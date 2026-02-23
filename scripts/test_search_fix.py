"""
Test the search pipeline after fixes.
Runs search_test.py inside the backend container to verify D0510.pdf chunks appear.
"""
import paramiko
import base64
import textwrap

VPS_HOST = "72.61.217.143"
VPS_USER = "root"
VPS_PASS = "Proelast1608@"
VPS_KEY_TYPE = "ssh-ed25519"
VPS_KEY_DATA = "AAAAC3NzaC1lZDI1NTE5AAAAIO3C7DkqvmcKI72+gYlrUxOyi5IK6qQCGTvYckDC5WiH"

SEARCH_SCRIPT = textwrap.dedent(r'''
import sys, os
sys.path.insert(0, "/app")
os.environ.setdefault("DATABASE_URL", "sqlite:////app/data/andreja.db")

from ingestion.embedder import search_brand

queries = [
    "led vermelho emergência caixa inspeção Beneton não acende",
    "led vermelho de emergência que não acende na caixa de inspeção Beneton",
    "D0510 Beneton emergência",
]

for q in queries:
    print(f"\n{'='*60}")
    print(f"Query: {q}")
    results = search_brand("otis", q, top_k=15)
    print(f"Total results: {len(results)}")
    
    d0510_found = False
    for i, r in enumerate(results):
        is_d0510 = "D0510" in r.get("source", "")
        marker = " *** D0510 ***" if is_d0510 else ""
        if is_d0510:
            d0510_found = True
        print(f"  [{i+1}] score={r['score']:.4f} doc_id={r.get('doc_id',0)} source={r.get('source','')}{marker}")
        if is_d0510:
            print(f"       text: {r['text'][:150]}...")
    
    if not d0510_found:
        print("  *** D0510.pdf NOT found in results! ***")
    else:
        print("  ✓ D0510.pdf found in results")
''')

def test():
    host_key = paramiko.Ed25519Key(data=base64.b64decode(VPS_KEY_DATA))
    client = paramiko.SSHClient()
    client.get_host_keys().add(VPS_HOST, VPS_KEY_TYPE, host_key)
    client.connect(VPS_HOST, username=VPS_USER, password=VPS_PASS)
    print("✓ SSH connected")

    # Write script to container
    sftp = client.open_sftp()
    with sftp.file("/root/andreja2/search_test_v2.py", "w") as f:
        f.write(SEARCH_SCRIPT)
    sftp.close()

    # Run inside container
    cmd = 'docker exec andreja_backend python /app/../search_test_v2.py 2>&1'
    # Actually, copy into container first
    copy_cmd = 'docker cp /root/andreja2/search_test_v2.py andreja_backend:/app/search_test_v2.py'
    stdin, stdout, stderr = client.exec_command(copy_cmd)
    stdout.channel.recv_exit_status()

    run_cmd = 'docker exec andreja_backend python /app/search_test_v2.py 2>&1'
    stdin, stdout, stderr = client.exec_command(run_cmd, timeout=60)
    exit_code = stdout.channel.recv_exit_status()
    output = stdout.read().decode()
    err = stderr.read().decode()
    
    print(output)
    if err:
        print("STDERR:", err[-500:])
    
    client.close()

if __name__ == "__main__":
    test()
