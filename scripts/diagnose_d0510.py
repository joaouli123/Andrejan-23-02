"""Diagnose why D0510.pdf content wasn't found by the chatbot."""
import paramiko, json

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("72.61.217.143", username="root", password="Proelast1608@")

# 1. Check what text was extracted from D0510.pdf (doc_id=17)
print("=== TEXT EXTRACTED FROM D0510.pdf (doc_id=17) ===")
cmd = """docker exec andreja_backend python -c "
import sqlite3
c = sqlite3.connect('/app/data/andreja.db')
cur = c.cursor()
cur.execute('SELECT page_number, length(gemini_text), quality_score, gemini_text FROM pages WHERE document_id=17')
for r in cur.fetchall():
    print(f'Page {r[0]}: {r[1]} chars, quality={r[2]}')
    print(f'TEXT: {r[3][:2000]}')
    print('---')
" """
stdin, stdout, stderr = ssh.exec_command(cmd)
print(stdout.read().decode())
err = stderr.read().decode()
if err: print("ERR:", err)

# 2. Check Qdrant chunks for doc_id=17
print("\n=== QDRANT CHUNKS FOR doc_id=17 ===")
cmd = """docker exec andreja_backend python -c "
import urllib.request, json

# Search by scrolling with filter
payload = json.dumps({
    'filter': {'must': [{'key': 'doc_id', 'match': {'value': 17}}]},
    'limit': 20,
    'with_payload': True
}).encode()

req = urllib.request.Request('http://qdrant:6333/collections/brand_otis/points/scroll', data=payload, headers={'Content-Type': 'application/json'}, method='POST')
data = json.loads(urllib.request.urlopen(req).read())
points = data.get('result', {}).get('points', [])
print(f'Found {len(points)} chunks for doc_id=17')
for p in points:
    payload = p.get('payload', {})
    text = payload.get('text', '')
    print(f'  chunk_index={payload.get(\"chunk_index\")}, len={len(text)}')
    print(f'  TEXT: {text[:500]}')
    print()
" """
stdin, stdout, stderr = ssh.exec_command(cmd)
print(stdout.read().decode())
err = stderr.read().decode()
if err: print("ERR:", err)

# 3. Test search for the user's query
print("\n=== SEARCH TEST: 'led vermelho emergência caixa inspeção Beneton' ===")
cmd = """docker exec andreja_backend python -c "
import sys
sys.path.insert(0, '/app')
from ingestion.embedder import search_brand
results = search_brand('otis', 'led vermelho emergência caixa inspeção Beneton não acende', top_k=5)
for r in results:
    print(f'score={r[\"score\"]:.4f} page={r[\"page\"]} doc_id={r[\"doc_id\"]} source={r[\"source\"]}')
    print(f'  text={r[\"text\"][:300]}')
    print()
" """
stdin, stdout, stderr = ssh.exec_command(cmd)
print(stdout.read().decode())
err = stderr.read().decode()
if err: print("ERR:", err)

# 4. Test search for 'D0510' or 'Beneton'
print("\n=== SEARCH TEST: 'Beneton' ===")
cmd = """docker exec andreja_backend python -c "
import sys
sys.path.insert(0, '/app')
from ingestion.embedder import search_brand
results = search_brand('otis', 'Beneton caixa inspeção emergência', top_k=5)
for r in results:
    print(f'score={r[\"score\"]:.4f} page={r[\"page\"]} doc_id={r[\"doc_id\"]} source={r[\"source\"]}')
    print(f'  text={r[\"text\"][:300]}')
    print()
" """
stdin, stdout, stderr = ssh.exec_command(cmd)
print(stdout.read().decode())
err = stderr.read().decode()
if err: print("ERR:", err)

ssh.close()
