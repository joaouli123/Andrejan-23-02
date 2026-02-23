"""Test the full chat flow for OVF10 scenario"""
import paramiko
import base64
import json

VPS_HOST = "72.61.217.143"
VPS_USER = "root"
VPS_PASS = "Proelast1608@"
HOST_KEY_B64 = "AAAAC3NzaC1lZDI1NTE5AAAAIO3C7DkqvmcKI72+gYlrUxOyi5IK6qQCGTvYckDC5WiH"

host_key = paramiko.Ed25519Key(data=base64.b64decode(HOST_KEY_B64))
ssh = paramiko.SSHClient()
ssh.get_host_keys().add(VPS_HOST, "ssh-ed25519", host_key)
ssh.connect(VPS_HOST, username=VPS_USER, password=VPS_PASS)

test_script = r'''
import asyncio, sys, json, os
sys.path.insert(0, "/app")
os.environ.setdefault("DATABASE_URL", "sqlite:////app/data/andreja.db")

async def test():
    from database import AsyncSessionLocal, engine
    from agent.chat import chat
    
    async with AsyncSessionLocal() as db:
        # Step 1: Initial question (generic)
        print("=" * 60)
        print("USER: Quais alteracoes especificas devem ser feitas na ligacao eletrica para garantir a operacao segura do equipamento?")
        result = await chat(
            db=db, user_id=1, brand_id=1,
            brand_slug="otis", brand_name="Otis",
            query="Quais alteracoes especificas devem ser feitas na ligacao eletrica para garantir a operacao segura do equipamento?",
            session_id=None,
        )
        sid = result["session_id"]
        print(f"AGENT: {result['answer'][:200]}")
        print(f"  needs_clarification: {result['needs_clarification']}")
        print(f"  sources: {len(result['sources'])}")
        
        # Step 2: User answers with model info
        print("\n" + "=" * 60)
        print("USER: Controles CVF (OVF10)")
        result2 = await chat(
            db=db, user_id=1, brand_id=1,
            brand_slug="otis", brand_name="Otis",
            query="Controles CVF (OVF10)",
            session_id=sid,
        )
        print(f"AGENT: {result2['answer'][:300]}")
        print(f"  needs_clarification: {result2['needs_clarification']}")
        print(f"  sources: {[s['filename'] for s in result2['sources']]}")

        # Step 3: Even more specific
        print("\n" + "=" * 60)
        print("USER: ATC - C.07.10 da Otis")
        result3 = await chat(
            db=db, user_id=1, brand_id=1,
            brand_slug="otis", brand_name="Otis",
            query="ATC - C.07.10 da Otis",
            session_id=sid,
        )
        print(f"AGENT: {result3['answer'][:300]}")
        print(f"  needs_clarification: {result3['needs_clarification']}")
        print(f"  sources: {[s['filename'] for s in result3['sources']]}")

asyncio.run(test())
'''

stdin, stdout, stderr = ssh.exec_command(f"cat > /tmp/test_chat_flow.py << 'PYEOF'\n{test_script}\nPYEOF")
stdout.channel.recv_exit_status()

stdin2, stdout2, stderr2 = ssh.exec_command(
    "docker cp /tmp/test_chat_flow.py andreja_backend:/tmp/test_chat_flow.py && "
    "docker exec andreja_backend python /tmp/test_chat_flow.py 2>&1",
    timeout=120
)
output = stdout2.read().decode()
print(output[-3000:])  # last 3000 chars

ssh.close()
