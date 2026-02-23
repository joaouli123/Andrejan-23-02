import base64
import os
import time

import paramiko

VPS_HOST = "72.61.217.143"
VPS_USER = "root"
VPS_PASS = "Proelast1608@"
VPS_KEY_TYPE = "ssh-ed25519"
VPS_KEY_DATA = "AAAAC3NzaC1lZDI1NTE5AAAAIO3C7DkqvmcKI72+gYlrUxOyi5IK6qQCGTvYckDC5WiH"
REMOTE_BASE = "/root/andreja2/backend"

FILES = {
    "backend/models.py": f"{REMOTE_BASE}/models.py",
    "backend/routes/rag_compat_routes.py": f"{REMOTE_BASE}/routes/rag_compat_routes.py",
}


def deploy():
    host_key = paramiko.Ed25519Key(data=base64.b64decode(VPS_KEY_DATA))
    client = paramiko.SSHClient()
    client.get_host_keys().add(VPS_HOST, VPS_KEY_TYPE, host_key)
    client.connect(VPS_HOST, username=VPS_USER, password=VPS_PASS)
    print("SSH connected")

    sftp = client.open_sftp()
    local_base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    for local_rel, remote_path in FILES.items():
        local_path = os.path.join(local_base, local_rel)
        print(f"  {local_rel} -> {remote_path}")
        sftp.put(local_path, remote_path)

    sftp.close()
    print("Files uploaded")

    print("Rebuilding backend...")
    _, stdout, stderr = client.exec_command(
        "cd /root/andreja2 && docker compose up -d --build backend",
        timeout=240,
    )
    exit_code = stdout.channel.recv_exit_status()
    err = stderr.read().decode()
    if exit_code != 0:
        print(f"BACKEND BUILD FAILED: {err[-1200:]}")
        client.close()
        return False

    print("Backend rebuilt")

    time.sleep(6)
    _, stdout, _ = client.exec_command(
        "docker ps --filter name=andreja_backend --format '{{.Status}}'"
    )
    print("Backend status:", stdout.read().decode().strip())

    _, stdout, _ = client.exec_command(
        "docker logs --tail 80 andreja_backend"
    )
    logs = stdout.read().decode()
    print("--- backend tail logs ---")
    print(logs)

    client.close()
    return True


if __name__ == "__main__":
    deploy()
