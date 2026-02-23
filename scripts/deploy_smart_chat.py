"""
Deploy smart clarification + scale improvements + duplicate protection + frontend fixes:
1. clarifier.py - Smart clarification, progressive search, confidence analysis
2. chat.py - Search-first-then-clarify flow
3. embedder.py - MAX_PER_DOC=2, filename match bonus
4. gemini_vision.py - Reranking with include_thoughts=False
5. open_source_vision.py - Same fix
6. admin_routes.py - Server-side duplicate detection
7. rag_compat_routes.py - Server-side duplicate detection + improved check-duplicates
8. AdminDashboard.tsx - Brand creation error handling fix
"""
import paramiko
import base64
import os
import time

VPS_HOST = "72.61.217.143"
VPS_USER = "root"
VPS_PASS = "Proelast1608@"
VPS_KEY_TYPE = "ssh-ed25519"
VPS_KEY_DATA = "AAAAC3NzaC1lZDI1NTE5AAAAIO3C7DkqvmcKI72+gYlrUxOyi5IK6qQCGTvYckDC5WiH"
REMOTE_BASE = "/root/andreja2/backend"
REMOTE_FRONTEND = "/root/andreja2/frontend"

BACKEND_FILES = {
    "backend/agent/clarifier.py": f"{REMOTE_BASE}/agent/clarifier.py",
    "backend/agent/chat.py": f"{REMOTE_BASE}/agent/chat.py",
    "backend/ingestion/embedder.py": f"{REMOTE_BASE}/ingestion/embedder.py",
    "backend/ingestion/gemini_vision.py": f"{REMOTE_BASE}/ingestion/gemini_vision.py",
    "backend/ingestion/open_source_vision.py": f"{REMOTE_BASE}/ingestion/open_source_vision.py",
    "backend/routes/admin_routes.py": f"{REMOTE_BASE}/routes/admin_routes.py",
    "backend/routes/rag_compat_routes.py": f"{REMOTE_BASE}/routes/rag_compat_routes.py",
}

FRONTEND_FILES = {
    "frontend/components/admin/AdminDashboard.tsx": f"{REMOTE_FRONTEND}/components/admin/AdminDashboard.tsx",
}

def deploy():
    host_key = paramiko.Ed25519Key(data=base64.b64decode(VPS_KEY_DATA))
    client = paramiko.SSHClient()
    client.get_host_keys().add(VPS_HOST, VPS_KEY_TYPE, host_key)
    client.connect(VPS_HOST, username=VPS_USER, password=VPS_PASS)
    print("SSH connected")

    sftp = client.open_sftp()
    local_base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # Upload backend files
    for local_rel, remote_path in BACKEND_FILES.items():
        local_path = os.path.join(local_base, local_rel)
        print(f"  {local_rel} -> {remote_path}")
        sftp.put(local_path, remote_path)

    # Upload frontend files
    for local_rel, remote_path in FRONTEND_FILES.items():
        local_path = os.path.join(local_base, local_rel)
        print(f"  {local_rel} -> {remote_path}")
        sftp.put(local_path, remote_path)
    sftp.close()
    print("Files uploaded")

    print("Rebuilding backend...")
    stdin, stdout, stderr = client.exec_command(
        "cd /root/andreja2 && docker compose up -d --build backend",
        timeout=180,
    )
    exit_code = stdout.channel.recv_exit_status()
    err = stderr.read().decode()
    if exit_code != 0:
        print(f"BACKEND BUILD FAILED: {err[-500:]}")
        client.close()
        return False
    print("Backend rebuilt")

    print("Rebuilding frontend...")
    stdin, stdout, stderr = client.exec_command(
        "cd /root/andreja2 && docker compose up -d --build frontend",
        timeout=300,
    )
    exit_code = stdout.channel.recv_exit_status()
    err = stderr.read().decode()
    if exit_code != 0:
        print(f"FRONTEND BUILD FAILED: {err[-500:]}")
        client.close()
        return False
    print("Frontend rebuilt")

    time.sleep(8)
    stdin, stdout, stderr = client.exec_command(
        "docker ps --filter name=andreja_backend --format '{{.Status}}' && "
        "echo '---' && "
        "docker ps --filter name=andreja_frontend --format '{{.Status}}'",
    )
    status = stdout.read().decode().strip()
    lines = status.split("---")
    print(f"Backend:  {lines[0].strip() if lines else 'unknown'}")
    print(f"Frontend: {lines[1].strip() if len(lines) > 1 else 'unknown'}")

    client.close()
    return True

if __name__ == "__main__":
    deploy()
