import json

with open("scripts/otis_300_results.json", "r", encoding="utf-8") as f:
    data = json.load(f)

results = data["results"]

# Count by actual ID ranges for categories
# Check if results are indexed by position or by ID
print(f"Total results: {len(results)}")
print(f"First 3 IDs: {[r['id'] for r in results[:3]]}")
print(f"IDs 160-182: {[r['id'] for r in results if 160 <= r['id'] <= 182]}")

# Check C test IDs from TESTS
import sys; sys.path.insert(0, "scripts")
from test_otis_300 import TESTS
c_ids = {t["id"] for t in TESTS if t["category"] == "C"}
print(f"\nC test IDs: {sorted(c_ids)}")

# Now count C results by ID matching
c_results = [r for r in results if r["id"] in c_ids]
c_passed = [r for r in c_results if r.get("passed")]
print(f"C results found: {len(c_results)}")
print(f"C passed: {len(c_passed)}")
for r in c_results:
    print(f"  ID {r['id']}: passed={r.get('passed')}")
