"""Upload fixed rag_compat_routes.py to VPS and rebuild backend."""
import paramiko
import os

HOST = "72.61.217.143"
USER = "root"
PASS = "Proelast1608@"

LOCAL_FILE = os.path.join(os.path.dirname(__file__), "..", "backend", "routes", "rag_compat_routes.py")
REMOTE_FILE = "/root/andreja2/backend/routes/rag_compat_routes.py"

print("Connecting to VPS...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASS)

print("Uploading rag_compat_routes.py...")
sftp = ssh.open_sftp()
sftp.put(os.path.abspath(LOCAL_FILE), REMOTE_FILE)
sftp.close()
print("File uploaded successfully.")

print("Rebuilding backend container...")
stdin, stdout, stderr = ssh.exec_command("cd /root/andreja2 && docker compose up -d --build backend", timeout=300)
out = stdout.read().decode()
err = stderr.read().decode()
print("STDOUT:", out)
print("STDERR:", err)

print("Checking container status...")
stdin, stdout, stderr = ssh.exec_command("docker ps --filter name=andreja_backend --format '{{.Status}}'")
print("Backend status:", stdout.read().decode().strip())

ssh.close()
print("Done!")
