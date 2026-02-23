"""Check current state of brands, documents, and files on VPS."""
import paramiko
import json

HOST = "72.61.217.143"
USER = "root"
PASS = "Proelast1608@"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASS)

# 1. Check all brands in DB
print("=== BRANDS ===")
cmd = """docker exec andreja_backend python -c "
import sqlite3
c = sqlite3.connect('/app/data/andreja.db')
cur = c.cursor()
cur.execute('SELECT id, name, slug, is_active FROM brands ORDER BY id')
for r in cur.fetchall():
    print(r)
" """
stdin, stdout, stderr = ssh.exec_command(cmd)
print(stdout.read().decode())
print(stderr.read().decode())

# 2. Check all documents in DB
print("=== DOCUMENTS ===")
cmd = """docker exec andreja_backend python -c "
import sqlite3
c = sqlite3.connect('/app/data/andreja.db')
cur = c.cursor()
cur.execute('SELECT id, brand_id, original_filename, filename, status, file_size, total_pages, processed_pages FROM documents ORDER BY id')
for r in cur.fetchall():
    print(r)
" """
stdin, stdout, stderr = ssh.exec_command(cmd)
print(stdout.read().decode())
print(stderr.read().decode())

# 3. Check physical files
print("=== PHYSICAL FILES ===")
cmd = "docker exec andreja_backend find /app/data/uploads -type f -name '*.pdf' 2>/dev/null"
stdin, stdout, stderr = ssh.exec_command(cmd)
print(stdout.read().decode())

# 4. Check API responses
print("=== API /api/brands ===")
cmd = "docker exec andreja_backend curl -s http://localhost:8000/api/brands"
stdin, stdout, stderr = ssh.exec_command(cmd)
brands = json.loads(stdout.read().decode())
for b in brands:
    print(f"  Brand: id={b['id']}, name={b['name']}, slug={b['slug']}")
    
    # Get docs for each brand
    cmd2 = f"docker exec andreja_backend curl -s http://localhost:8000/api/brands/{b['id']}/documents"
    stdin2, stdout2, stderr2 = ssh.exec_command(cmd2)
    docs = json.loads(stdout2.read().decode())
    for d in docs:
        print(f"    Doc: id={d['id']}, title={d['title']}, file_size={d['file_size']}, status={d['status']}")

# 5. Check Qdrant collections
print("\n=== QDRANT ===")
cmd = "docker exec andreja_backend curl -s http://qdrant:6333/collections"
stdin, stdout, stderr = ssh.exec_command(cmd)
data = json.loads(stdout.read().decode())
for col in data.get('result', {}).get('collections', []):
    name = col['name']
    cmd2 = f"docker exec andreja_backend curl -s http://qdrant:6333/collections/{name}"
    stdin2, stdout2, stderr2 = ssh.exec_command(cmd2)
    info = json.loads(stdout2.read().decode())
    count = info.get('result', {}).get('points_count', 0)
    print(f"  Collection: {name} -> {count} points")

ssh.close()
