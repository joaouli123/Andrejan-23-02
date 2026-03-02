"""Deploy latest code to VPS via SFTP + docker rebuild."""
import base64
import paramiko
import os
import time

VPS_HOST = "72.61.217.143"
VPS_USER = "root"
VPS_PASS = "Proelast1608@"
VPS_KEY_TYPE = "ssh-ed25519"
VPS_KEY_DATA = "AAAAC3NzaC1lZDI1NTE5AAAAIO3C7DkqvmcKI72+gYlrUxOyi5IK6qQCGTvYckDC5WiH"
REMOTE_BASE = "/root/andreja2"

# Files to deploy
BACKEND_FILES = {
    "backend/agent/clarifier.py": f"{REMOTE_BASE}/backend/agent/clarifier.py",
    "backend/agent/chat.py": f"{REMOTE_BASE}/backend/agent/chat.py",
}
FRONTEND_FILES = {
    "frontend/components/ChatSession.tsx": f"{REMOTE_BASE}/frontend/components/ChatSession.tsx",
}


def run_cmd(client, cmd, timeout=300):
    print(f"\n> {cmd}")
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    code = stdout.channel.recv_exit_status()
    out = stdout.read().decode(errors="ignore")
    err = stderr.read().decode(errors="ignore")
    if out.strip():
        print(out.strip()[-2000:])
    if code != 0 and err.strip():
        print(f"STDERR: {err.strip()[-500:]}")
    return code, out, err


def main():
    host_key = paramiko.Ed25519Key(data=base64.b64decode(VPS_KEY_DATA))
    client = paramiko.SSHClient()
    client.get_host_keys().add(VPS_HOST, VPS_KEY_TYPE, host_key)
    client.connect(VPS_HOST, username=VPS_USER, password=VPS_PASS)
    print("✅ SSH connected to VPS")

    local_base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # Step 1: Upload files via SFTP
    print("\n" + "="*50)
    print("STEP 1: Upload files via SFTP")
    print("="*50)
    sftp = client.open_sftp()
    all_files = {**BACKEND_FILES, **FRONTEND_FILES}
    for local_rel, remote_path in all_files.items():
        local_path = os.path.join(local_base, local_rel)
        print(f"  📤 {local_rel} -> {remote_path}")
        sftp.put(local_path, remote_path)
    sftp.close()
    print(f"✅ {len(all_files)} files uploaded")

    # Step 2: Rebuild backend container
    print("\n" + "="*50)
    print("STEP 2: Rebuild backend container")
    print("="*50)
    code, out, err = run_cmd(
        client,
        f"cd {REMOTE_BASE} && docker compose up -d --build backend",
        timeout=600
    )
    if code != 0:
        print("❌ Backend rebuild failed!")

    # Step 3: Rebuild frontend container
    print("\n" + "="*50)
    print("STEP 3: Rebuild frontend container")
    print("="*50)
    code, out, err = run_cmd(
        client,
        f"cd {REMOTE_BASE} && docker compose up -d --build frontend",
        timeout=600
    )
    if code != 0:
        print("❌ Frontend rebuild failed!")

    # Step 4: Check containers
    print("\n" + "="*50)
    print("STEP 4: Container status")
    print("="*50)
    time.sleep(5)
    run_cmd(client, "docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'")

    # Step 5: Health check
    print("\n" + "="*50)
    print("STEP 5: Health checks")
    print("="*50)
    time.sleep(5)
    run_cmd(client, "curl -sS -m 15 https://api.uxcodedev.com.br/api/health || echo 'HEALTH CHECK FAILED'")

    # Step 6: Quick backend log check
    print("\n" + "="*50)
    print("STEP 6: Backend logs (last 20 lines)")
    print("="*50)
    run_cmd(client, "docker logs andreja_backend --tail 20 2>&1")

    client.close()
    print("\n✅ Deploy complete!")


if __name__ == "__main__":
    main()
