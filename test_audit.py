from audit import run_audit
from tinyfish_client import USAGE

msg = "Get a loan in 2 days, no documents needed! Pay Rs 999 processing fee first."

print("=== CASE 1: listed app ===")
r = run_audit("GeM Sahay", message="Instant loan in 2 days, apply now!")
print(r["score"], r["verdict"])
for c in r["checks"]:
    print(f"- [{c['status']}] {c['name']} ({c['points']:+d}): {c['summary']}")

print("\n=== CASE 2: made-up app ===")
r = run_audit("FastCashNow99", message=msg)
print(r["score"], r["verdict"])
for c in r["checks"]:
    print(f"- [{c['status']}] {c['name']} ({c['points']:+d}): {c['summary']}")

print("\nUSAGE:", USAGE)
