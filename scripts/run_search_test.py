"""Upload search_test.py and run inside container."""
import paramiko, os

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("72.61.217.143", username="root", password="Proelast1608@")

# Upload script
local = os.path.join(os.path.dirname(os.path.abspath(__file__)), "search_test.py")
sftp = ssh.open_sftp()
sftp.put(local, "/root/andreja2/scripts/search_test.py")
sftp.close()

# Copy into container and run
cmds = [
    "docker cp /root/andreja2/scripts/search_test.py andreja_backend:/app/scripts/search_test.py",
    "docker exec andreja_backend python /app/scripts/search_test.py",
]
for cmd in cmds:
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=60)
    out = stdout.read().decode()
    err = stderr.read().decode()
    if out: print(out)
    if err and "Error" in err: print("ERR:", err)

ssh.close()
