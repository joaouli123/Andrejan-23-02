"""Test filename matching with various user input formats"""
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
import sys
sys.path.insert(0, "/app")
from ingestion.embedder import _filename_match_bonus, _normalize_for_matching

# All real filenames in the system
filenames = [
    "958a96af-14bf-468c-95cb-621ec84052a5_Calibracao do OVF10.pdf",
    "cd400fed-e0e3-49ba-951c-a9cf4f4ce9ab_Mag completo.pdf",
    "c689c686-a082-43b9-9d48-e4d97a50efb7_LFV OVF20 MNUAL DE AJUSTE.pdf",
    "41e87005-7249-4950-a617-174c7ddd10b7_OTISMATIC.pdf",
    "e5e0338a-6429-400a-93f1-a7993a3df413_ATC 043 ELIMINAR ACP.pdf",
    "D0510.pdf",
    "899b5c82-f222-4b9c-9822-5d11f0e90a6e_Manual GEN2 Resgate.pdf",
    "a34814cf-c4f1-4efc-b8aa-9e945996e282_DIAGRAMA DE LCB1 PARA LCB2.pdf",
    "1c52cad6-5b71-45fc-922a-4c53c42f3dab_Lista de IO RCB2 JAA30171AAA.pdf",
    "13f84ad5-7245-438c-8f74-032d9babb9f9_Manual Otis uso URM 311-1.pdf",
    "72836e53-4bb3-4561-aed9-16c92e22a261_D0506.pdf",
    "9955eb74-8658-4441-8563-9845231b7354_D0510.pdf",
]

# Test queries as user might type them
queries = [
    "ovf10",              # → should match Calibracao do OVF10
    "OVF10",              # → same, different case
    "calibracao ovf10",   # → strong match
    "atc c0710",          # → should match? (its ATC - C.07.10 doc)
    "gen2",               # → Manual GEN2 Resgate
    "GEN2 resgate",       # → Manual GEN2 Resgate (strong)
    "lcb2",               # → DIAGRAMA DE LCB1 PARA LCB2
    "ovf20",              # → LFV OVF20 MNUAL DE AJUSTE
    "d0510",              # → D0510.pdf
    "mag completo",       # → Mag completo.pdf
    "otismatic",          # → OTISMATIC.pdf
    "rcb2",               # → Lista de IO RCB2
    "urm 311",            # → Manual Otis uso URM 311-1
    "ATC 043",            # → ATC 043 ELIMINAR ACP
    "eliminar acp",       # → ATC 043 ELIMINAR ACP
    "diagrama lcb1 lcb2", # → DIAGRAMA DE LCB1 PARA LCB2
]

print("=== Normalization Tests ===")
for fn in filenames[:5]:
    print(f"  '{fn}' -> '{_normalize_for_matching(fn)}'")

print(f"\n=== Filename Match Bonus Tests ===")
for q in queries:
    print(f"\nQuery: '{q}'")
    matches = []
    for fn in filenames:
        bonus = _filename_match_bonus(fn, q)
        if bonus > 0:
            display = fn.split("_", 1)[-1] if "_" in fn else fn
            matches.append((display, bonus))
    matches.sort(key=lambda x: -x[1])
    if matches:
        for name, b in matches:
            print(f"  +{b:.2f} {name}")
    else:
        print("  NO MATCH!")
'''

stdin, stdout, stderr = ssh.exec_command(f"cat > /tmp/test_matching.py << 'PYEOF'\n{test_script}\nPYEOF")
stdout.channel.recv_exit_status()
stdin2, stdout2, stderr2 = ssh.exec_command(
    "docker cp /tmp/test_matching.py andreja_backend:/tmp/test_matching.py && "
    "docker exec andreja_backend python /tmp/test_matching.py 2>&1",
    timeout=30
)
output = stdout2.read().decode()
print(output)
ssh.close()
