"""Upload reprocess_errors.py to VPS and run it inside the backend container"""
import paramiko
import base64
import os

VPS_HOST = "72.61.217.143"
VPS_USER = "root"
VPS_PASS = "Proelast1608@"
VPS_KEY_DATA = "AAAAC3NzaC1lZDI1NTE5AAAAIO3C7DkqvmcKI72+gYlrUxOyi5IK6qQCGTvYckDC5WiH"

host_key = paramiko.Ed25519Key(data=base64.b64decode(VPS_KEY_DATA))
client = paramiko.SSHClient()
client.get_host_keys().add(VPS_HOST, "ssh-ed25519", host_key)
client.connect(VPS_HOST, username=VPS_USER, password=VPS_PASS)

# Upload script
sftp = client.open_sftp()
local = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reprocess_errors.py")
sftp.put(local, "/root/andreja2/scripts/reprocess_errors.py")
sftp.close()
print("Script uploaded")

# Copy into container and run
stdin, stdout, stderr = client.exec_command(
    "docker cp /root/andreja2/scripts/reprocess_errors.py andreja_backend:/app/scripts/reprocess_errors.py && "
    "docker exec andreja_backend python /app/scripts/reprocess_errors.py",
    timeout=30
)
print(stdout.read().decode())
err = stderr.read().decode()
if err:
    print("STDERR:", err)

client.close()
