"""
Deploy search pipeline fixes to VPS:
1. embedder.py - Document diversity + larger Qdrant fetch
2. chat.py - top_k=15, chunks[:7]
3. gemini_vision.py - rerank threshold >= 5
"""
import paramiko
import os
import time

VPS_HOST = "72.61.217.143"
VPS_USER = "root"
VPS_PASS = "Proelast1608@"
VPS_KEY_TYPE = "ssh-ed25519"
VPS_KEY_DATA = "AAAAC3NzaC1lZDI1NTE5AAAAIO3C7DkqvmcKI72+gYlrUxOyi5IK6qQCGTvYckDC5WiH"
REMOTE_BASE = "/root/andreja2/backend"

FILES_TO_DEPLOY = {
    "backend/ingestion/embedder.py": f"{REMOTE_BASE}/ingestion/embedder.py",
    "backend/agent/chat.py": f"{REMOTE_BASE}/agent/chat.py",
    "backend/ingestion/gemini_vision.py": f"{REMOTE_BASE}/ingestion/gemini_vision.py",
}

def deploy():
    import base64
    host_key = paramiko.Ed25519Key(data=base64.b64decode(VPS_KEY_DATA))
    
    client = paramiko.SSHClient()
    client.get_host_keys().add(VPS_HOST, VPS_KEY_TYPE, host_key)
    client.connect(VPS_HOST, username=VPS_USER, password=VPS_PASS)
    print("✓ SSH connected")

    sftp = client.open_sftp()
    local_base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    for local_rel, remote_path in FILES_TO_DEPLOY.items():
        local_path = os.path.join(local_base, local_rel)
        print(f"  Uploading {local_rel} → {remote_path}")
        sftp.put(local_path, remote_path)
    
    sftp.close()
    print("✓ All files uploaded")

    # Rebuild backend
    print("  Rebuilding backend container...")
    stdin, stdout, stderr = client.exec_command(
        "cd /root/andreja2 && docker compose up -d --build backend",
        timeout=180,
    )
    exit_code = stdout.channel.recv_exit_status()
    out = stdout.read().decode()
    err = stderr.read().decode()
    print(f"  Exit code: {exit_code}")
    if out.strip():
        print(f"  stdout: {out[-500:]}")
    if err.strip():
        print(f"  stderr: {err[-500:]}")
    
    if exit_code == 0:
        print("✓ Backend rebuilt successfully")
    else:
        print("✗ Build failed!")
        client.close()
        return

    # Wait for container to be healthy
    print("  Waiting for backend to start...")
    time.sleep(8)
    
    stdin, stdout, stderr = client.exec_command(
        "docker ps --filter name=andreja_backend --format '{{.Status}}'",
    )
    status = stdout.read().decode().strip()
    print(f"  Backend status: {status}")

    client.close()
    print("✓ Deploy complete!")

if __name__ == "__main__":
    deploy()
