import sys
sys.path.insert(0, "scripts")
from test_otis_300 import TESTS

c_tests = [t for t in TESTS if t.get("category") == "C"]
clarify = [t for t in c_tests if t.get("expected") == "CLARIFY"]
answer = [t for t in c_tests if t.get("expected") == "ANSWER"]
print(f"C tests: {len(c_tests)} total, {len(clarify)} expect CLARIFY, {len(answer)} expect ANSWER")
for t in c_tests:
    tid = t["id"]
    q = t.get("question", "?")[:55]
    exp = t.get("expected")
    hist = "history" in t
    print(f"  {tid}: Q={q} | expect={exp} | history={hist}")
