"""Quick API check via external HTTP."""
import paramiko, json

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("72.61.217.143", username="root", password="Proelast1608@")

# Use wget instead of curl
cmd = 'docker exec andreja_backend python -c "import urllib.request, json; data=json.loads(urllib.request.urlopen(\'http://localhost:8000/api/brands\').read()); print(json.dumps(data, indent=2))"'
stdin, stdout, stderr = ssh.exec_command(cmd)
out = stdout.read().decode()
print("=== BRANDS ===")
print(out)

brands = json.loads(out)
for b in brands:
    cmd2 = f'docker exec andreja_backend python -c "import urllib.request, json; data=json.loads(urllib.request.urlopen(\'http://localhost:8000/api/brands/{b["id"]}/documents\').read()); print(json.dumps(data, indent=2))"'
    stdin2, stdout2, stderr2 = ssh.exec_command(cmd2)
    docs_out = stdout2.read().decode()
    docs = json.loads(docs_out)
    print(f"\n=== Docs for {b['name']} (id={b['id']}) ===")
    for d in docs:
        size_mb = (d.get('file_size') or 0) / 1024 / 1024
        print(f"  {d['title']} - {size_mb:.1f} MB - {d['status']}")

ssh.close()
