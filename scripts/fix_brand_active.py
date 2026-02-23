"""Fix: activate Otis brand (id=1) and deactivate duplicate LG Otis (id=16)."""
import paramiko

HOST = "72.61.217.143"
USER = "root"
PASS = "Proelast1608@"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASS)

# Fix brand states
cmd = """docker exec andreja_backend python -c "
import sqlite3
c = sqlite3.connect('/app/data/andreja.db')
cur = c.cursor()

# Activate Otis (id=1) - has the document
cur.execute('UPDATE brands SET is_active=1 WHERE id=1')
print(f'Activated brand Otis (id=1): {cur.rowcount} rows')

# Deactivate LG Otis (id=16) - duplicate, no docs
cur.execute('UPDATE brands SET is_active=0 WHERE id=16')
print(f'Deactivated brand LG Otis (id=16): {cur.rowcount} rows')

c.commit()

# Verify
cur.execute('SELECT id, name, slug, is_active FROM brands WHERE id IN (1,16)')
for r in cur.fetchall():
    print(f'  Brand {r[0]}: name={r[1]}, slug={r[2]}, active={r[3]}')

# Verify doc is under brand 1
cur.execute('SELECT id, brand_id, original_filename, status, file_size FROM documents WHERE brand_id=1')
for r in cur.fetchall():
    print(f'  Doc {r[0]}: brand_id={r[1]}, file={r[2]}, status={r[3]}, size={r[4]}')
" """
stdin, stdout, stderr = ssh.exec_command(cmd)
print(stdout.read().decode())
err = stderr.read().decode()
if err:
    print("STDERR:", err)

# Check API now works
import json
cmd2 = "docker exec andreja_backend curl -s http://localhost:8000/api/brands"
stdin, stdout, stderr = ssh.exec_command(cmd2)
brands = json.loads(stdout.read().decode())
for b in brands:
    print(f"API Brand: id={b['id']}, name={b['name']}")

cmd3 = "docker exec andreja_backend curl -s http://localhost:8000/api/brands/1/documents"
stdin, stdout, stderr = ssh.exec_command(cmd3)
docs = json.loads(stdout.read().decode())
for d in docs:
    size_mb = (d['file_size'] or 0) / 1024 / 1024
    print(f"API Doc: id={d['id']}, title={d['title']}, size={size_mb:.1f} MB, status={d['status']}")

ssh.close()
print("\nDone! Refresh the admin page.")
