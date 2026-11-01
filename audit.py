from concurrent.futures import ThreadPoolExecutor, wait
from rbi_list import search_rbi_list
from message_check import analyze_message
from tinyfish_client import safe_search, safe_agent, safe_research

NEG_WORDS = ["fraud", "scam", "harass", "complaint", "fake", "cheat",
             "illegal", "warning", "blocked", "threat"]

NBFC_LIST_URL = "https://www.rbi.org.in/Scripts/BS_NBFCList.aspx"


def _check(name, tool, status, points, summary, sources=None, data=None):
    return {"name": name, "tool": tool, "status": status, "points": points,
            "summary": summary, "sources": sources or [], "data": data or {}}


def _url(u):
    u = (u or "").strip()
    if not u:
        return ""
    return u if u.startswith("http") else "https://" + u


def _truthy(v):
    return str(v).strip().lower() in ("true", "yes", "1")


def _has_value(v):
    return bool(v) and str(v).strip().lower() not in (
        "none", "null", "n/a", "not found", "not available", "unknown")


def unknown(name, tool, why):
    return _check(name, tool, "unknown", 0, why)


# ---------- instant checks ----------
def check_rbi(app_name):
    r = search_rbi_list(app_name)
    if r["status"] == "found":
        m = r["matches"][0]
        stores = sorted({x["available_on"] for x in r["matches"] if x["available_on"]})
        return _check(
            "RBI DLA directory", "Local RBI list", "good", 30,
            f"Listed. Lender: {m['entity']} ({m['entity_type']}). Stores: {', '.join(stores) or 'n/a'}.",
            data={"entity": m["entity"], "entity_site": m["entity_site"],
                  "app": m["app"], "grievance_email": m["grievance_email"]})
    if r["status"] == "possible":
        m = r["matches"][0]
        return _check("RBI DLA directory", "Local RBI list", "warn", 5,
                      f"No exact match. Similar name: '{m['app']}'. Check the spelling.",
                      data={"entity": m["entity"], "entity_site": m["entity_site"]})
    if r["status"] == "too_short":
        return unknown("RBI DLA directory", "Local RBI list", "Name too short to search.")
    return _check("RBI DLA directory", "Local RBI list", "bad", -25,
                  "No match found in the downloaded RBI list. This is not proof of fraud: "
                  "the app may use a different legal name. Ask the lender for its regulated entity's name.")


def check_message(text):
    if not text or not text.strip():
        return None
    m = analyze_message(text)
    pts = -min(30, m["risk_points"] // 2)
    if m["red_flags"]:
        summary = "Red flags: " + "; ".join(f["flag"] for f in m["red_flags"])
        status = "bad" if m["risk_points"] >= 30 else "warn"
    else:
        summary, status = "No common scam phrases found.", "good"
    return _check("Message red flags", "Rule-based", status, pts, summary,
                  data={"claimed_speed": m["claimed_speed"],
                        "amount": m["amount_mentioned"], "flags": m["red_flags"]})


# ---------- TinyFish checks (run in parallel) ----------
def check_lender_site(app_name, site):
    name, tool = "Lender website", "TinyFish Agent"
    site = _url(site)
    if not site:
        return unknown(name, tool, "No website to check. Add the lender's website for a stronger audit.")
    goal = (f"Check whether this website mentions or lists the app '{app_name}' "
            "(digital lending apps, partner apps, product pages). Also find the "
            "grievance redressal officer contact if shown. Return JSON with keys: "
            "mentions_app (true/false), grievance_contact, evidence_url.")
    res = safe_agent(site, goal, label="Lender website")
    if not res["ok"] or not isinstance(res.get("result"), dict):
        return _check(name, tool, "unknown", 0,
                      "Could not verify this site (blocked, slow or unreadable).",
                      sources=[{"title": site, "url": site}])
    d = res["result"]
    mentions = _truthy(d.get("mentions_app"))
    grievance = d.get("grievance_contact")
    ev = d.get("evidence_url") or site
    points = (15 if mentions else -5) + (5 if _has_value(grievance) else 0)
    parts = ["The lender's site mentions this app." if mentions
             else "The lender's site did not mention this app."]
    if _has_value(grievance):
        parts.append(f"Grievance contact found: {grievance}")
    return _check(name, tool, "good" if mentions else "warn", points, " ".join(parts),
                  sources=[{"title": "Evidence page", "url": str(ev)}], data=d)


def check_fees_privacy(app_name, site):
    name, tool = "Fees & privacy", "TinyFish Agent"
    site = _url(site)
    if not site:
        return unknown(name, tool, "No website to check.")
    goal = ("Find this lender's published charges and its privacy policy. Return JSON "
            "with keys: charges_published (true/false), interest_rate_range, "
            "processing_fee, prepayment_charges, privacy_policy_url, "
            "shares_data_with_third_parties (true/false/unknown), "
                        "data_collected (short text), disbursal_time_stated (how fast the lender says money is paid out).")
    res = safe_agent(site, goal, label="Fees & privacy")
    if not res["ok"] or not isinstance(res.get("result"), dict):
        return unknown(name, tool, "Could not read fee or privacy pages from this site.")
    d = res["result"]
    published = _truthy(d.get("charges_published"))
    shares = _truthy(d.get("shares_data_with_third_parties"))
    pts = (5 if published else -5) + (-5 if shares else 0)
    bits = []
    for label, key in (("Interest", "interest_rate_range"), ("Processing fee", "processing_fee"),
                       ("Prepayment", "prepayment_charges")):
        if _has_value(d.get(key)):
            bits.append(f"{label}: {d.get(key)}")
    bits.append("Charges are published." if published else "Charges were not clearly published.")
    if shares:
        bits.append("Privacy policy mentions sharing data with third parties.")
    if _has_value(d.get("data_collected")):
        bits.append(f"Data collected: {d.get('data_collected')}")
    src = []
    if _has_value(d.get("privacy_policy_url")):
        src.append({"title": "Privacy policy", "url": str(d.get("privacy_policy_url"))})
    return _check(name, tool, "good" if published and not shares else "warn",
                  pts, " ".join(bits), sources=src, data=d)


def check_nbfc(entity):
    name, tool = "RBI NBFC list", "TinyFish Agent"
    if not entity:
        return unknown(name, tool, "No lender name to look up.")
    goal = (f"Search this list for the company '{entity}'. Return JSON with keys: "
            "found (true/false), registration_number, status (for example active or cancelled).")
    res = safe_agent(NBFC_LIST_URL, goal, label="RBI NBFC list")
    if not res["ok"] or not isinstance(res.get("result"), dict):
        return unknown(name, tool, "Could not read RBI's NBFC list right now.")
    d = res["result"]
    src = [{"title": "RBI NBFC list", "url": NBFC_LIST_URL}]
    if _truthy(d.get("found")):
        st = str(d.get("status", "")).lower()
        if "cancel" in st:
            return _check(name, tool, "bad", -15,
                          f"Lender found on RBI's NBFC list but status looks cancelled ({d.get('status')}).",
                          sources=src, data=d)
        reg = d.get("registration_number")
        return _check(name, tool, "good", 10,
                      "Lender found on RBI's NBFC list." + (f" Registration: {reg}." if _has_value(reg) else ""),
                      sources=src, data=d)
    return _check(name, tool, "warn", -5,
                  "Lender not found on RBI's NBFC list in this check. It may be a bank, or listed under another name.",
                  sources=src, data=d)


def check_reputation(name_q):
    name, tool = "Reputation (Search)", "TinyFish Search"
    res = safe_search(f"{name_q} complaints reviews", n=8)
    if not res["ok"]:
        return unknown(name, tool, "Could not search right now.")
    items = res["results"]
    hits = [x for x in items
            if any(w in (x["title"] + " " + x.get("snippet", "")).lower() for w in NEG_WORDS)]
    pts = -min(15, 5 * len(hits))
    if hits:
        summary = (f"{len(hits)} of {len(items)} results use complaint-type words. "
                   "Read them: a word match is a hint, not proof.")
        status = "warn"
    else:
        summary = "No complaint-type words in the top results. Absence is not proof of safety."
        status = "good"
    return _check(name, tool, status, pts, summary,
                  sources=[{"title": x["title"], "url": x["url"]} for x in items[:6]],
                  data={"snippets": [(x["title"] + " " + x.get("snippet", "")) for x in items]})


def check_research(name_q):
    name, tool = "Reputation report (Research)", "TinyFish Research"
    q = (f"What is the reputation and regulatory standing of {name_q} as a lender in India? "
         "Cover complaints, regulator actions, and customer experience. Cite sources.")
    res = safe_research(q)
    if not res["ok"]:
        return unknown(name, tool, "Research report was not available: " + res.get("error", "")[:120])
    text = res["report"]
    short = text if len(text) <= 700 else text[:700] + "..."
    return _check(name, tool, "good", 0, short, data={"report": text})


# ---------- orchestration ----------
def prepare(app_name, website="", message="", use_research=True):
    rbi = check_rbi(app_name)
    msg = check_message(message)
    entity = rbi["data"].get("entity") if rbi["status"] != "bad" else None
    site = (rbi["data"].get("entity_site") or website) if rbi["status"] != "bad" else website
    rep_name = entity or f"{app_name} loan app"

    jobs = {
        "Lender website": lambda: check_lender_site(app_name, site),
        "Fees & privacy": lambda: check_fees_privacy(app_name, site),
        "Reputation (Search)": lambda: check_reputation(rep_name),
    }
    if entity:
        jobs["RBI NBFC list"] = lambda: check_nbfc(entity)
    if use_research:
        jobs["Reputation report (Research)"] = lambda: check_research(rep_name)

    instant = [c for c in (rbi, msg) if c]
    return {"instant": instant, "jobs": jobs}


def verdict(score):
    if score >= 70:
        return "🟢 Looks legitimate (based on the sources we checked)"
    if score >= 40:
        return "🟡 Be careful: verify before sharing documents"
    return "🔴 High risk: do not share documents or pay fees"


def finalize(checks):
    score = max(0, min(100, 50 + sum(c["points"] for c in checks)))
    return {"score": score, "verdict": verdict(score), "checks": checks}


def verdict_band(score):
    return "good" if score >= 70 else "mid" if score >= 40 else "bad"


def run_audit(app_name, website="", message="", use_research=False, timeout=150):
    """Run a whole audit without a UI. Used by Compare, Monitor and tests."""
    plan = prepare(app_name, website, message, use_research)
    checks = list(plan["instant"])
    jobs = plan["jobs"]
    pool = ThreadPoolExecutor(max_workers=max(1, len(jobs)))
    futures = {pool.submit(fn): name for name, fn in jobs.items()}
    done, pending = wait(futures, timeout=timeout)
    for f in done:
        try:
            checks.append(f.result())
        except Exception as e:
            checks.append(unknown(futures[f], "TinyFish", f"Check failed: {str(e)[:100]}"))
    for f in pending:
        checks.append(unknown(futures[f], "TinyFish", "Timed out."))
    pool.shutdown(wait=False, cancel_futures=True)
    return finalize(checks)
