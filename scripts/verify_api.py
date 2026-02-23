"""Verify the /api/brands/{id}/documents endpoint returns file_size."""
import paramiko
import json

HOST = "72.61.217.143"
USER = "root"
PASS = "Proelast1608@"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASS)

# Check API response
cmd = 'curl -s http://localhost:8000/api/brands/1/documents'
stdin, stdout, stderr = ssh.exec_command(cmd)
data = json.loads(stdout.read().decode())
print("API response for brand 1 documents:")
for doc in data:
    print(f"  id={doc['id']}, title={doc['title']}, file_size={doc['file_size']}, status={doc['status']}")
    size_mb = (doc['file_size'] or 0) / 1024 / 1024
    print(f"  -> {size_mb:.1f} MB")

ssh.close()
