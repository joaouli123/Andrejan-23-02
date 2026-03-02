"""Show failing test details with queries and expected behavior."""
import json, sys
sys.path.insert(0, "scripts")
from test_otis_300 import TESTS as ALL_TESTS

with open("scripts/otis_300_results.json", "r", encoding="utf-8") as f:
    data = json.load(f)

results = data["results"]
actual = [r for r in results if "error" not in r]
failed = [r for r in actual if not r.get("passed")]

# Build test lookup
test_by_id = {t["id"]: t for t in ALL_TESTS}

# Get the failed IDs from previous batch 1 (1-101) too
# Merge: batch1 had IDs 37,51,93 as failures
batch1_fail_ids = {37, 51, 93}

over_clarify = []
under_clarify = []

# Process batch 2 failures  
for r in failed:
    details_str = " ".join(str(d) for d in r.get("details", []))
    tid = r["id"]
    t = test_by_id.get(tid, {})
    entry = {
        "id": tid,
        "category": t.get("category", "?"),
        "description": t.get("desc", "?"),
        "query": t.get("question", "?"),
        "expected": t.get("expected", "?"),
        "expected_docs": t.get("expected_docs", []),
    }
    if "Asked for clarification when should have answered" in details_str:
        over_clarify.append(entry)
    else:
        under_clarify.append(entry)

# Add batch1 failures
for tid in sorted(batch1_fail_ids):
    t = test_by_id.get(tid, {})
    details_str = ""  # We know these from prior analysis
    entry = {
        "id": tid,
        "category": t.get("category", "?"),
        "description": t.get("desc", "?"),
        "query": t.get("question", "?"),
        "expected": t.get("expected", "?"),
        "expected_docs": t.get("expected_docs", []),
    }
    over_clarify.insert(0, entry)  # All 3 were over-clarify

print("=" * 70)
print(f"OVER-CLARIFY: {len(over_clarify)} tests (agent asks but should answer)")
print("=" * 70)
for e in over_clarify:
    print(f"\n  ID {e['id']} ({e['category']}) - {e['description']}")
    print(f"  Query: {e['query']}")
    print(f"  Expected: {e['expected']} | Docs: {e['expected_docs']}")

print()
print("=" * 70)
print(f"UNDER-CLARIFY: {len(under_clarify)} tests (agent answers but should ask)")
print("=" * 70)
for e in under_clarify:
    print(f"\n  ID {e['id']} ({e['category']}) - {e['description']}")
    print(f"  Query: {e['query']}")
    print(f"  Expected: {e['expected']} | Docs: {e['expected_docs']}")
