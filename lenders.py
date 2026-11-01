import re
from concurrent.futures import ThreadPoolExecutor

from tinyfish_client import safe_fetch_text
from rbi_list import search_rbi_list, load_list

# Add the exact "personal loan" and "privacy policy" page URLs to each list.
# More relevant pages = better results. Verify these domains yourself.
LENDERS = [
    {"name": "SBI", "kind": "Bank", "urls": ["https://www.sbi.co.in"]},
    {"name": "HDFC Bank", "kind": "Bank", "urls": ["https://www.hdfcbank.com"]},
    {"name": "Kissht", "kind": "App/NBFC", "urls": ["https://www.kissht.com"]},
    {"name": "CASHe", "kind": "App/NBFC", "urls": ["https://www.cashe.co.in"]},
    {"name": "JioFinance", "kind": "App/NBFC", "urls": ["https://www.jiofinance.in"]},
    {"name": "IDFC FIRST Bank", "kind": "Bank", "urls": ["https://www.idfcfirst.bank.in"]},
    {"name": "Stashfin", "kind": "App/NBFC", "urls": ["https://www.stashfin.com"]},
    {"name": "CapitalNow", "kind": "App/NBFC", "urls": ["https://www.capitalnow.in"]},
    {"name": "Bank of Baroda", "kind": "Bank", "urls": ["https://www.bankofbaroda.in"]},
]

PAN_RE = re.compile(r"\bPAN\b|[Pp]ermanent [Aa]ccount [Nn]umber")
NEED_RE = re.compile(r"requir|mandator|necessar|must|submit|documents?|KYC|eligib", re.I)
RATE_RE = re.compile(r"(\d{1,2}(?:\.\d{1,2})?)\s*%")

PRIVACY_PATTERNS = {
    "Accesses your contacts": r"access.{0,25}contacts?|contact list|phone ?book",
    "Reads your SMS": r"read.{0,15}SMS|access.{0,20}SMS|SMS (permission|access)",
    "Accesses gallery / camera": r"(access|permission).{0,30}(gallery|photos|camera)",
    "Collects location": r"(access|collect|track).{0,25}location|location (data|permission|access)",
    "Shares data with third parties": r"(share|disclose|transfer).{0,40}third[- ]part",
    "Uses data for marketing": r"(marketing|promotional) (purposes|communications|offers)",
}


def _sentences(text):
    return re.split(r"(?<=[.!?])\s+|\n+", text)


def _pan(text):
    hits = [s for s in _sentences(text) if PAN_RE.search(s)]
    if not hits:
        return "Not mentioned on fetched pages", ""
    need = [s for s in hits if NEED_RE.search(s)]
    if need:
        return "Yes, listed as needed", need[0].strip()[:200]
    return "PAN mentioned", hits[0].strip()[:200]


def _rates(text):
    rates, fees = [], []
    for m in RATE_RE.finditer(text):
        v = float(m.group(1))
        ctx = text[max(0, m.start() - 80): m.end() + 60].lower()
        if "processing" in ctx and "interest" not in ctx:
            if v <= 10:
                fees.append(v)
        elif any(k in ctx for k in ("interest", "p.a", "per annum", "roi", "apr")) and 5 <= v <= 60:
            rates.append(v)
    return rates, fees


def _privacy(text):
    return [label for label, pat in PRIVACY_PATTERNS.items()
            if re.search(pat, text, re.I | re.S)]


def _rbi_status(L):
    r = search_rbi_list(L["name"])
    if L["kind"] == "Bank":
        base = "✅ Scheduled bank (RBI-regulated)"
        return base + (" · app in DLA list" if r["status"] == "found" else "")
    return {"found": "✅ In RBI DLA list",
            "possible": "⚠️ Similar name only",
            "not_found": "🔴 Not in DLA list",
            "too_short": "❔ Name too short"}.get(r["status"], "❔")


def fetch_one(L):
    texts, errors = [], []
    for u in L["urls"]:
        r = safe_fetch_text(u)          # TinyFish Fetch, every time
        if r["ok"]:
            texts.append(r["text"])
        else:
            errors.append(r["error"])
    text = "\n".join(texts)
    rates, fees = _rates(text)
    pan_label, pan_evidence = _pan(text)
    return {
        "name": L["name"], "kind": L["kind"], "urls": L["urls"],
        "fetched": bool(texts), "error": "; ".join(e for e in errors if e),
        "rate_min": min(rates) if rates else None,
        "rate_max": max(rates) if rates else None,
         "rate_avg": round(sum(rates) / len(rates), 1) if rates else None,
        "fee_pct": fees[0] if fees else None,
        "pan": pan_label, "pan_evidence": pan_evidence,
        "privacy_flags": _privacy(text),
        "privacy_scanned": bool(re.search(r"privacy", text, re.I)),
        "rbi": _rbi_status(L),
    }


def fetch_all_lenders():
    load_list()
    with ThreadPoolExecutor(max_workers=len(LENDERS)) as pool:
        futures = [pool.submit(fetch_one, L) for L in LENDERS]
        out = []
        for L, f in zip(LENDERS, futures):
            try:
                out.append(f.result(timeout=120))
            except Exception as e:
                out.append({"name": L["name"], "kind": L["kind"], "urls": L["urls"],
                            "fetched": False, "error": str(e)[:150], "rate_min": None,
                            "rate_max": None, "rate_avg": None , "fee_pct": None, "pan": "Fetch failed",
                            "pan_evidence": "", "privacy_flags": [],
                            "privacy_scanned": False, "rbi": _rbi_status(L)})
        return out
def recommend(d, rate, market_avg):
    """Returns (label, reason) from the evidence gathered for one lender."""
    score, reasons = 0, []

    # --- regulation ---
    rbi = d["rbi"]
    if rbi.startswith("✅"):
        score += 2
        reasons.append("RBI-regulated" if d["kind"] == "Bank" else "in RBI DLA list")
    elif rbi.startswith("🔴"):
        score -= 2
        reasons.append("not in RBI DLA list")
    elif rbi.startswith("⚠️"):
        reasons.append("only a similar name in RBI list")

    # --- privacy ---
    if d["privacy_scanned"]:
        n = len(d["privacy_flags"])
        if n >= 3:
            score -= 2
            reasons.append(f"{n} privacy flags")
        elif n >= 1:
            score -= 1
            reasons.append(f"{n} privacy flag" + ("s" if n > 1 else ""))
        else:
            score += 1
            reasons.append("no privacy flags found")
    else:
        reasons.append("privacy not checked")

    # --- cost ---
    if rate and market_avg:
        if rate <= market_avg:
            score += 1
            reasons.append("rate at or below average")
        elif rate > market_avg + 3:
            score -= 1
            reasons.append("rate above average")

    # --- could we verify anything? ---
    if not d["fetched"]:
        score -= 1
        reasons.append("pages could not be fetched")

    if score >= 3:
        label = "✅ Recommended"
    elif score >= 1:
        label = "🟡 Okay, check details"
    else:
        label = "🔴 Verify before applying"
    return label, ", ".join(reasons)