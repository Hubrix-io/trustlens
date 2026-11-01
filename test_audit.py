from audit import run_audit
from tinyfish_client import USAGE

msg = "Get a loan in 2 days, no documents needed! Pay Rs 999 processing fee first."

for label, name, m in (("listed app", "GeM Sahay", "Instant loan in 2 days, apply now!"),
                       ("made-up app", "FastCashNow99", msg)):
    print(f"=== {label} ===")
    r = run_audit(name, message=m)
    print(r["score"], r["verdict"])
    for c in r["checks"]:
        print(f"- [{c['status']}] {c['name']} ({c['points']:+d}): {c['summary']}")
print("\nUSAGE:", USAGE)
