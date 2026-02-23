"""Deploy speed optimizations to VPS and rebuild backend."""
import paramiko
import os

HOST = "72.61.217.143"
USER = "root"
PASS = "Proelast1608@"
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASS)
sftp = ssh.open_sftp()

# Upload modified files
files = [
    ("backend/ingestion/open_source_vision.py", "/root/andreja2/backend/ingestion/open_source_vision.py"),
    ("backend/ingestion/embedder.py", "/root/andreja2/backend/ingestion/embedder.py"),
]

for local_rel, remote in files:
    local = os.path.join(BASE, local_rel)
    print(f"Uploading {local_rel}...")
    sftp.put(local, remote)

# Update .env on VPS: change INGESTION_PAGE_DELAY_SECONDS from 4 to 0
print("Updating .env on VPS...")
stdin, stdout, stderr = ssh.exec_command(
    "sed -i 's/INGESTION_PAGE_DELAY_SECONDS=4/INGESTION_PAGE_DELAY_SECONDS=0/' /root/andreja2/.env"
)
stdout.read()
# Verify
stdin, stdout, stderr = ssh.exec_command("grep INGESTION_PAGE_DELAY /root/andreja2/.env")
print(f"  .env: {stdout.read().decode().strip()}")

sftp.close()

# Rebuild backend
print("Rebuilding backend container...")
stdin, stdout, stderr = ssh.exec_command(
    "cd /root/andreja2 && docker compose up -d --build backend",
    timeout=300,
)
out = stdout.read().decode()
err = stderr.read().decode()
if "Started" in err or "Running" in err:
    print("Backend rebuilt and started!")
else:
    print("STDOUT:", out[-200:] if len(out) > 200 else out)
    print("STDERR:", err[-500:] if len(err) > 500 else err)

# Verify container
stdin, stdout, stderr = ssh.exec_command("docker ps --filter name=andreja_backend --format '{{.Status}}'")
status = stdout.read().decode().strip()
print(f"Backend status: {status}")

ssh.close()
print("\nDone! Speed optimizations deployed.")
print("\nResume of changes:")
print("  1. GEMINI_MIN_INTERVAL: 4.5s → 2.0s (with retry on 429)")
print("  2. INGESTION_PAGE_DELAY: 4s → 0s (unnecessary for non-Gemini pages)")
print("  3. Thinking disabled for OCR (thinking_budget=0)")
print("  4. Gemini DPI: 300 → 200 (reuse Tesseract image)")
print("  5. Batch embeddings (1 API call per page instead of per chunk)")
