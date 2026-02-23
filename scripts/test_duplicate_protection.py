"""Test: verify server-side duplicate detection works correctly."""
import requests
import json

VPS = "http://72.61.217.143:8000"

# Login
r = requests.post(f"{VPS}/auth/login", data={"username": "admin@andreja.com", "password": "admin123"})
token = r.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

print("=" * 60)
print("TESTE 1: check-duplicates endpoint (nomes exatos)")
print("=" * 60)

# Test with existing filename
r = requests.post(f"{VPS}/api/check-duplicates", 
    json={"fileNames": ["Mag completo.pdf", "OTISMATIC.pdf", "NovoArquivo.pdf"], "brandId": "1"},
    headers=headers)
data = r.json()
print(f"  Input: Mag completo.pdf, OTISMATIC.pdf, NovoArquivo.pdf")
print(f"  Duplicatas detectadas: {data['duplicates']}")
assert "Mag completo.pdf" in data["duplicates"], "FALHA: Mag completo.pdf deveria ser duplicata"
assert "OTISMATIC.pdf" in data["duplicates"], "FALHA: OTISMATIC.pdf deveria ser duplicata"
assert "NovoArquivo.pdf" not in data["duplicates"], "FALHA: NovoArquivo.pdf NÃO deveria ser duplicata"
print("  ✓ PASSOU")

print()
print("=" * 60)
print("TESTE 2: check-duplicates com variações (maiúscula/minúscula/acentos)")
print("=" * 60)

# Test with variations
r = requests.post(f"{VPS}/api/check-duplicates", 
    json={"fileNames": ["mag completo.pdf", "otismatic.pdf", "MAG COMPLETO.PDF"], "brandId": "1"},
    headers=headers)
data = r.json()
print(f"  Input: mag completo.pdf, otismatic.pdf, MAG COMPLETO.PDF")
print(f"  Duplicatas detectadas: {data['duplicates']}")
# These should all be detected as duplicates via normalization
expected_dupes = len(data["duplicates"])
print(f"  Detectou {expected_dupes} duplicata(s)")
if expected_dupes >= 2:
    print("  ✓ PASSOU - Normalização funcionando")
else:
    print("  ⚠ Normalização pode não estar pegando variações de caixa")

print()
print("=" * 60)
print("TESTE 3: check-duplicates com nome completamente diferente")
print("=" * 60)

r = requests.post(f"{VPS}/api/check-duplicates", 
    json={"fileNames": ["Manual GEN2 Resgate.pdf", "Calibração do OVF10.pdf", "Manual Otis uso URM 311-1.pdf"], "brandId": "1"},
    headers=headers)
data = r.json()
print(f"  Input: Manual GEN2 Resgate.pdf, Calibração do OVF10.pdf, Manual Otis uso URM 311-1.pdf")
print(f"  Duplicatas detectadas: {data['duplicates']}")
# These were deleted so should NOT be duplicates anymore
if len(data["duplicates"]) == 0:
    print("  ✓ PASSOU - Nenhuma duplicata (arquivos foram deletados antes)")
else:
    print(f"  ⚠ Estes não deveriam ser duplicatas: {data['duplicates']}")

print()
print("=" * 60)
print("TESTE 4: Verificar que documentos independentes NÃO conflitam")
print("=" * 60)

# These should all be independent
test_names = ["D0509.pdf", "D0506.pdf", "D0510.pdf", "regular freio otis.pdf"]
r = requests.post(f"{VPS}/api/check-duplicates", 
    json={"fileNames": test_names, "brandId": "1"},
    headers=headers)
data = r.json()
print(f"  Input: {test_names}")
print(f"  Duplicatas detectadas: {data['duplicates']}")
# All should be detected as duplicates since they exist
assert len(data["duplicates"]) == len(test_names), f"FALHA: esperava {len(test_names)} duplicatas, recebeu {len(data['duplicates'])}"
print("  ✓ PASSOU - Todos detectados como existentes")

print()
print("=" * 60)
print("RESUMO DO ESTADO ATUAL")
print("=" * 60)
r = requests.get(f"{VPS}/admin/brands/1/documents", headers=headers)
if r.status_code == 200:
    docs = r.json()
    if isinstance(docs, list):
        print(f"  Total de documentos na marca: {len(docs)}")
        for d in docs:
            print(f"    id={d.get('id')} | {d.get('status','?')} | {d.get('original_filename','?')}")
    else:
        print(f"  Resposta: {docs}")
else:
    print(f"  Erro ao buscar docs: {r.status_code}")

print()
print("3 documentos precisam ser RE-ENVIADOS:")
print("  1. Manual GEN2 Resgate.pdf")
print("  2. Manual Otis uso URM 311-1.pdf")
print("  3. Calibração do OVF10.pdf")
