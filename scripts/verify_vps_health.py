import base64
import paramiko

host = "72.61.217.143"
user = "root"
pwd = "Proelast1608@"
key_type = "ssh-ed25519"
key_data = "AAAAC3NzaC1lZDI1NTE5AAAAIO3C7DkqvmcKI72+gYlrUxOyi5IK6qQCGTvYckDC5WiH"

host_key = paramiko.Ed25519Key(data=base64.b64decode(key_data))
client = paramiko.SSHClient()
client.get_host_keys().add(host, key_type, host_key)
client.connect(host, username=user, password=pwd)

commands = [
    "curl -sS -m 10 http://127.0.0.1:8000/api/health",
    "curl -sS -m 10 http://127.0.0.1:3000 | head -c 120",
]

for cmd in commands:
    stdin, stdout, stderr = client.exec_command(cmd, timeout=30)
    code = stdout.channel.recv_exit_status()
    out = stdout.read().decode(errors="ignore").strip()
    err = stderr.read().decode(errors="ignore").strip()
    print(f"CMD: {cmd}\nCODE: {code}\nOUT: {out}\nERR: {err}\n---")

client.close()
