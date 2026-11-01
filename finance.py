import re


def calc_emi(amount, annual_rate, months):
    r = annual_rate / 12 / 100
    if r == 0:
        return amount / months
    return amount * r * (1 + r) ** months / ((1 + r) ** months - 1)


def _annual_rate_from_emi(received, emi, months):
    """Find the yearly rate (%) that makes these EMIs worth 'received' today."""
    if emi * months <= received:
        return 0.0
    lo, hi = 0.0, 1.0
    for _ in range(100):
        mid = (lo + hi) / 2
        pv = emi * (1 - (1 + mid) ** -months) / mid
        if pv > received:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2 * 12 * 100


RATE_TYPES = ["Per year (reducing balance)", "Per month (reducing balance)", "Flat per year"]


def cost_for(amount, months, rate, rate_type, fee_pct):
    if rate_type.startswith("Flat"):
        interest = amount * rate / 100 * months / 12
        emi = (amount + interest) / months
    elif "month" in rate_type:
        emi = calc_emi(amount, rate * 12, months)
    else:
        emi = calc_emi(amount, rate, months)
    fee = amount * fee_pct / 100
    received = amount - fee
    total = emi * months
    return {
        "emi": emi,
        "total": total,
        "fee": fee,
        "received": received,
        "extra_cost": total - received,
        "apr": _annual_rate_from_emi(received, emi, months),
    }


def timing_view(claimed, lender_stated, snippets):
    bad = ("", "none", "null", "n/a", "unknown", "not found", "not available")
    lender = str(lender_stated or "").strip()
    if lender.lower() in bad:
        lender = "not found on the lender's pages"
    when = re.compile(r"\b\d+\s*(minutes?|hours?|days?|weeks?)\b", re.I)
    ctx = re.compile(r"(disburs|credited|received|delay|waited|took)", re.I)
    hints = []
    for s in snippets or []:
        if ctx.search(s) and when.search(s):
            hints.append(s[:220])
        if len(hints) >= 2:
            break
    return {"claimed": claimed or "not stated in the message",
            "lender": lender, "reviews": hints}