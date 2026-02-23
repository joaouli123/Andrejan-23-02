"""Check if D0510.pdf exists in the system."""
import paramiko, json

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("72.61.217.143", username="root", password="Proelast1608@")

# Check all documents in DB
print("=== ALL DOCUMENTS IN DB ===")
cmd = """docker exec andreja_backend python -c "
import sqlite3
c = sqlite3.connect('/app/data/andreja.db')
cur = c.cursor()
cur.execute('SELECT id, brand_id, original_filename, status, total_pages, processed_pages FROM documents ORDER BY id')
for r in cur.fetchall():
    print(r)
" """
stdin, stdout, stderr = ssh.exec_command(cmd)
print(stdout.read().decode())
print(stderr.read().decode())

# Check physical files
print("=== ALL PDF FILES ON DISK ===")
cmd = "docker exec andreja_backend find /app/data/uploads -type f -name '*.pdf' 2>/dev/null"
stdin, stdout, stderr = ssh.exec_command(cmd)
print(stdout.read().decode())

# Check Qdrant collections
print("=== QDRANT COLLECTIONS ===")
cmd = """docker exec andreja_backend python -c "
import urllib.request, json
data = json.loads(urllib.request.urlopen('http://qdrant:6333/collections').read())
for col in data.get('result', {}).get('collections', []):
    name = col['name']
    info = json.loads(urllib.request.urlopen(f'http://qdrant:6333/collections/{name}').read())
    count = info.get('result', {}).get('points_count', 0)
    print(f'  {name}: {count} points')
" """
stdin, stdout, stderr = ssh.exec_command(cmd)
print(stdout.read().decode())
print(stderr.read().decode())

# Search for D0510 in filenames
print("=== SEARCH FOR D0510 ===")
cmd = "docker exec andreja_backend find /app/data/uploads -name '*D0510*' -o -name '*d0510*' 2>/dev/null"
stdin, stdout, stderr = ssh.exec_command(cmd)
result = stdout.read().decode().strip()
print(result if result else "  NOT FOUND on disk")

ssh.close()
