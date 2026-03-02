import json

with open("scripts/otis_300_results.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# Show C test results (IDs 161-180)
for r in data["results"]:
    if 161 <= r["id"] <= 180:
        d = " | ".join(str(x)[:60] for x in r.get("details", []))
        status = "PASS" if r["passed"] else "FAIL"
        print(f"ID {r['id']}: {status} | {d}")
