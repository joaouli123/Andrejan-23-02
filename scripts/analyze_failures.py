"""Analyze failures from test_otis_300 results to find patterns."""
import json

with open("scripts/otis_300_results.json", "r", encoding="utf-8") as f:
    data = json.load(f)

results = data["results"]

# Separate connection errors
actual = [r for r in results if "error" not in r]
conn_err = [r for r in results if "error" in r]

failed = [r for r in actual if not r.get("passed")]
partial = [r for r in actual if r.get("passed") and any("⚠" in str(d) for d in r.get("details", []))]

print(f"=== TOTAL: {len(actual)} actual, {len(conn_err)} conn errors ===")
print(f"Pass: {sum(1 for r in actual if r['passed'])}/{len(actual)}")
print(f"Fail: {len(failed)}")
print()

# Categorize failures
over_clarify = []  # Agent asked when should have answered
under_clarify = []  # Agent answered when should have asked
wrong_sources = []  # Right action but wrong docs

for r in failed:
    details = r.get("details", [])
    details_str = " ".join(str(d) for d in details)
    
    if "Asked for clarification when should have answered" in details_str:
        over_clarify.append(r)
    elif "Should have asked for clarification but answered" in details_str:
        under_clarify.append(r)
    else:
        wrong_sources.append(r)

print(f"=== FAILURE BREAKDOWN ===")
print(f"Over-clarify (asked when shouldn't): {len(over_clarify)}")
print(f"Under-clarify (answered when shouldn't): {len(under_clarify)}")
print(f"Other/wrong sources: {len(wrong_sources)}")
print()

print("=== OVER-CLARIFY (Agent asks but should answer) ===")
for r in over_clarify:
    print(f"  ID {r['id']}")

print()
print("=== UNDER-CLARIFY (Agent answers but should ask) ===")
for r in under_clarify:
    print(f"  ID {r['id']}")

print()
print("=== OTHER FAILURES ===")
for r in wrong_sources:
    print(f"  ID {r['id']}: {' | '.join(str(d)[:60] for d in r.get('details', []))}")
