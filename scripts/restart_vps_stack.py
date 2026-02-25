import base64
import paramiko

VPS_HOST = "72.61.217.143"
VPS_USER = "root"
VPS_PASS = "Proelast1608@"
VPS_KEY_TYPE = "ssh-ed25519"
VPS_KEY_DATA = "AAAAC3NzaC1lZDI1NTE5AAAAIO3C7DkqvmcKI72+gYlrUxOyi5IK6qQCGTvYckDC5WiH"


def run_cmd(client: paramiko.SSHClient, cmd: str, timeout: int = 120):
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    code = stdout.channel.recv_exit_status()
    out = stdout.read().decode(errors="ignore")
    err = stderr.read().decode(errors="ignore")
    return code, out, err


def main():
    host_key = paramiko.Ed25519Key(data=base64.b64decode(VPS_KEY_DATA))
    client = paramiko.SSHClient()
    client.get_host_keys().add(VPS_HOST, VPS_KEY_TYPE, host_key)
    client.connect(VPS_HOST, username=VPS_USER, password=VPS_PASS)
    print("SSH connected")

    print("Restarting backend/frontend containers...")
    code, out, err = run_cmd(
        client,
        "cd /root/andreja2 && docker compose restart backend frontend",
        timeout=180,
    )
    print(out.strip())
    if code != 0:
        print("RESTART ERROR:", err.strip())

    print("\nContainer status:")
    code, out, err = run_cmd(
        client,
        "docker ps --filter name=andreja_backend --filter name=andreja_frontend --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'",
        timeout=60,
    )
    print(out.strip())

    print("\nHealth checks:")
    checks = [
        "curl -sS -m 10 https://api.uxcodedev.com.br/api/health || true",
        "curl -sS -m 10 https://elevex.uxcodedev.com.br || true",
    ]
    for c in checks:
        _, o, _ = run_cmd(client, c, timeout=30)
        snippet = (o or "").strip().replace("\n", " ")
        if len(snippet) > 220:
            snippet = snippet[:220] + "..."
        print(snippet)

    print("\nRecent backend logs:")
    _, out, _ = run_cmd(client, "docker logs --tail 40 andreja_backend", timeout=60)
    print(out)

    client.close()


if __name__ == "__main__":
    main()
