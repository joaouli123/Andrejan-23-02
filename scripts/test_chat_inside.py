"""
E2E chat test - run from inside VPS since port 3001 isn't exposed externally.
"""
import paramiko
import base64

VPS_HOST = "72.61.217.143"
VPS_USER = "root"
VPS_PASS = "Proelast1608@"
VPS_KEY_TYPE = "ssh-ed25519"
VPS_KEY_DATA = "AAAAC3NzaC1lZDI1NTE5AAAAIO3C7DkqvmcKI72+gYlrUxOyi5IK6qQCGTvYckDC5WiH"

CHAT_TEST = r'''
import sys, os, json
sys.path.insert(0, "/app")
os.environ.setdefault("DATABASE_URL", "sqlite:////app/data/andreja.db")

import asyncio
from agent.chat import handle_chat_message

async def test():
    question = "O led vermelho de emergência não acende na caixa de inspeção Beneton. Qual o procedimento para corrigir?"
    print(f"Question: {question}\n")
    
    result = await handle_chat_message(
        brand_slug="otis",
        brand_name="Otis",
        query=question,
        history=[],
    )
    
    print(f"Answer:\n{result.get('answer', 'NO ANSWER')}\n")
    print(f"Sources: {json.dumps(result.get('sources', []), indent=2, ensure_ascii=False)}")
    
    # Check if D0510 mentioned
    answer = result.get('answer', '')
    if 'D0510' in answer or 'Beneton' in answer or 'INS' in answer or 'bloco' in answer:
        print("\n✓ SUCCESS: Answer references D0510.pdf content!")
    else:
        print("\n? Answer may not be from D0510.pdf - check manually")

asyncio.run(test())
'''

def run():
    host_key = paramiko.Ed25519Key(data=base64.b64decode(VPS_KEY_DATA))
    ssh = paramiko.SSHClient()
    ssh.get_host_keys().add(VPS_HOST, VPS_KEY_TYPE, host_key)
    ssh.connect(VPS_HOST, username=VPS_USER, password=VPS_PASS)

    sftp = ssh.open_sftp()
    with sftp.file("/root/andreja2/chat_test.py", "w") as f:
        f.write(CHAT_TEST)
    sftp.close()

    cmds = [
        "docker cp /root/andreja2/chat_test.py andreja_backend:/app/chat_test.py",
        "docker exec andreja_backend python /app/chat_test.py 2>&1",
    ]
    for cmd in cmds:
        stdin, stdout, stderr = ssh.exec_command(cmd, timeout=120)
        exit_code = stdout.channel.recv_exit_status()
        output = stdout.read().decode()
        if output.strip():
            print(output)
        err = stderr.read().decode()
        if err.strip() and exit_code != 0:
            print(f"ERR: {err[-500:]}")

    ssh.close()

if __name__ == "__main__":
    run()
