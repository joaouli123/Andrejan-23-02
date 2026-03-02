import json
import test_otis_300 as t

with open("otis_300_results.json", "r", encoding="utf-8") as f:
    data = json.load(f)

by_id = {x["id"]: x for x in t.TESTS}

print(
    f"total={data['total']} pass={data['passed']} partial={data['partial']} fail={data['failed']} errors={data['errors']}"
)

for result in data["results"]:
    if result.get("passed") is False:
        test = by_id.get(result["id"], {})
        print(f"\nID {result['id']} [{test.get('category','?')}] exp={test.get('expected','?')}")
        print(f"Desc: {test.get('desc','?')}")
        print(f"Q: {test.get('question','?')}")
        print(f"Details: {result.get('details')}")
