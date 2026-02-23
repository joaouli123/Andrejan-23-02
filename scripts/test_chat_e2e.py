"""
End-to-end chat test: ask the exact question that failed before
about the Beneton LED issue from D0510.pdf.
"""
import requests

BASE = "http://72.61.217.143:3001/api"

# Login
r = requests.post(f"{BASE}/auth/login", json={
    "username": "admin@andreja.com",
    "password": "admin123"
})
token = r.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}
print(f"Logged in: {token[:20]}...")

# Create chat session for brand Otis
r = requests.post(f"{BASE}/chat/sessions", json={
    "brand_slug": "otis"
}, headers=headers)
print(f"Session response: {r.status_code} - {r.json()}")
session = r.json()
session_id = session.get("session_id", session.get("id"))
print(f"Session ID: {session_id}")

# Ask the failing question
question = "O led vermelho de emergência não acende na caixa de inspeção Beneton. Qual o procedimento para corrigir?"
print(f"\nQuestion: {question}")

r = requests.post(f"{BASE}/chat/message", json={
    "session_id": session_id,
    "message": question,
    "brand_slug": "otis"
}, headers=headers, timeout=60)

print(f"\nResponse status: {r.status_code}")
resp = r.json()
print(f"\nAnswer:\n{resp.get('answer', resp.get('response', resp))}")

sources = resp.get("sources", [])
if sources:
    print(f"\nSources cited:")
    for s in sources:
        print(f"  - {s}")
