"""Debug reranking to find why scores are all 0"""
import paramiko
import base64

VPS_HOST = "72.61.217.143"
VPS_USER = "root"
VPS_PASS = "Proelast1608@"
HOST_KEY_B64 = "AAAAC3NzaC1lZDI1NTE5AAAAIO3C7DkqvmcKI72+gYlrUxOyi5IK6qQCGTvYckDC5WiH"

host_key = paramiko.Ed25519Key(data=base64.b64decode(HOST_KEY_B64))
ssh = paramiko.SSHClient()
ssh.get_host_keys().add(VPS_HOST, "ssh-ed25519", host_key)
ssh.connect(VPS_HOST, username=VPS_USER, password=VPS_PASS)

test_script = r'''
import asyncio, sys, os, json, re
sys.path.insert(0, "/app")
os.environ.setdefault("DATABASE_URL", "sqlite:////app/data/andreja.db")

from google import genai
from google.genai import types
from config import get_settings

settings = get_settings()
client = genai.Client(api_key=settings.gemini_api_key)

async def test():
    from ingestion.embedder import search_brand
    
    query = "alteracoes ligacao eletrica Controles CVF OVF10"
    chunks = search_brand("otis", query, top_k=10)
    
    # Build rerank prompt manually
    chunks_text = "\n\n".join(
        f"[{i}] Fonte: {c['source']} | Pagina: {c['page']}\n{c['text'][:500]}"
        for i, c in enumerate(chunks[:7])
    )
    
    RERANK_PROMPT = """Voce e um especialista tecnico em elevadores.
Dada a consulta do tecnico e os trechos de documentacao recuperados, avalie cada trecho de 0 a 10
quanto a sua relevancia e utilidade para a consulta.

Consulta: {query}

Trechos:
{chunks}

Responda no formato JSON:
[{{"index": 0, "score": 9, "reason": "..."}}]
"""
    
    prompt = RERANK_PROMPT.format(query=query, chunks=chunks_text)
    print("=== PROMPT (first 300 chars) ===")
    print(prompt[:300])
    
    response = await client.aio.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(temperature=0.0, max_output_tokens=1024),
    )
    
    raw = response.text or ""
    print(f"\n=== RAW RESPONSE ({len(raw)} chars) ===")
    print(raw[:1000])
    
    # Try to parse
    json_match = re.search(r'\[.*\]', raw, re.DOTALL)
    if json_match:
        try:
            scores = json.loads(json_match.group())
            print(f"\n=== PARSED SCORES ({len(scores)} items) ===")
            for item in scores:
                print(f"  index={item.get('index')}, score={item.get('score')}, reason={item.get('reason','')[:60]}")
        except json.JSONDecodeError as e:
            print(f"JSON parse error: {e}")
            print(f"Matched text: {json_match.group()[:300]}")
    else:
        print("NO JSON ARRAY FOUND in response!")

asyncio.run(test())
'''

stdin, stdout, stderr = ssh.exec_command(f"cat > /tmp/test_rerank.py << 'PYEOF'\n{test_script}\nPYEOF")
stdout.channel.recv_exit_status()

stdin2, stdout2, stderr2 = ssh.exec_command(
    "docker cp /tmp/test_rerank.py andreja_backend:/tmp/test_rerank.py && "
    "docker exec andreja_backend python /tmp/test_rerank.py 2>&1",
    timeout=60
)
output = stdout2.read().decode()
print(output[-2000:])
ssh.close()
