import json, sys

with open("scripts/otis_300_results.json", "r", encoding="utf-8") as f:
    data = json.load(f)

results = data["results"]

# Check structure
print("Sample keys:", results[0].keys())
print("Sample:", json.dumps(results[0], ensure_ascii=False)[:300])
print("Sample 200:", json.dumps(results[200], ensure_ascii=False)[:300])
print()

# Classify  
def is_conn_error(r):
    return "error" in r

conn_errors = [r for r in results if is_conn_error(r)]
actual = [r for r in results if not is_conn_error(r)]
passed = [r for r in actual if r.get("passed")]
failed = [r for r in actual if not r.get("passed")]

print(f"Total: {len(results)}")
print(f"Connection errors: {len(conn_errors)}")
print(f"Actual: {len(actual)}")
print(f"Passed: {len(passed)}/{len(actual)} ({100*len(passed)/max(len(actual),1):.1f}%)")
print(f"Failed: {len(failed)}")
print()

# Show failures
print("=== FAILURES ===")
for r in failed:
    d = r.get("details", [])
    if isinstance(d, list):
        d = " | ".join(str(x)[:80] for x in d)
    else:
        d = str(d)[:160]
    print(f"  ID {r['id']}: {d}")

if conn_errors:
    print(f"\nFirst connection error at ID: {conn_errors[0]['id']}")
    print(f"Total connection errors: {len(conn_errors)}")
