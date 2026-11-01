from concurrent.futures import ThreadPoolExecutor

from rbi_list import search_rbi_list
from message_check import analyze_message
from tinyfish_client import safe_search, safe_agent

NEG_WORDS = ["fraud", "scam", "harass", "complaint", "fake", "cheat",
             "illegal", "warning", "blocked", "threat"]


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
    return bool(v) and str(v).strip().lower() not in ("none", "null", "n/a", "not found", "not available")


# ---------- CHECK 1: RBI list (instant, local file) ----------
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
        return _check("RBI DLA directory", "Local RBI list", "unknown", 0,
                      "Name too short to search.")
    return _check("RBI DLA directory", "Local RBI list", "bad", -25,
                  "No match found in the downloaded RBI list. This is not proof of fraud: "
                  "the app may use a different legal name. Ask the lender for its regulated entity's name.")


# ---------- CHECK 2: the lender's own website (TinyFish Agent) ----------
def check_lender_site(app_name, site):
    site = _url(site)
    if not site:
        return _check("Lender website", "TinyFish Agent", "unknown", 0,
                      "No website to check. Add the lender's website for a stronger audit.")
    goal = (f"Check whether this website mentions or lists the app '{app_name}' "
            "(digital lending apps, partner apps, product pages). Also find the "
            "grievance redressal officer contact if shown. Return JSON with keys: "
            "mentions_app (true/false), grievance_contact, evidence_url.")
    res = safe_agent(site, goal)
    if not res["ok"] or not isinstance(res.get("result"), dict):
        return _check("Lender website", "TinyFish Agent", "unknown", 0,
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
    return _check("Lender website", "TinyFish Agent",
                  "good" if mentions else "warn", points, " ".join(parts),
                  sources=[{"title": "Evidence page", "url": ev}], data=d)


# ---------- CHECK 3: reputation (TinyFish Search) ----------
def check_reputation(name):
    res = safe_search(f"{name} complaints reviews", n=8)
    if not res["ok"]:
        return _check("Reputation", "TinyFish Search", "unknown", 0,
                      "Could not search right now.")
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
    return _check("Reputation", "TinyFish Search", status, pts, summary,
                  sources=[{"title": x["title"], "url": x["url"]} for x in items[:6]])


# ---------- CHECK 4: the message itself (instant) ----------
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
                        "amount": m["amount_mentioned"],
                        "flags": m["red_flags"]})


# ---------- SCORE ----------
def verdict(score):
    if score >= 70:
        return "🟢 Looks legitimate (based on the sources we checked)"
    if score >= 40:
        return "🟡 Be careful: verify before sharing documents"
    return "🔴 High risk: do not share documents or pay fees"


def run_audit(app_name, website="", message=""):
    checks = []

    msg_check = check_message(message)
    rbi = check_rbi(app_name)
    site = (rbi["data"].get("entity_site") or website) if rbi["status"] != "bad" else website
    rep_name = rbi["data"].get("entity") or f"{app_name} loan app"

    # the two slow TinyFish checks run in parallel
    with ThreadPoolExecutor(max_workers=2) as pool:
        f_site = pool.submit(check_lender_site, app_name, site)
        f_rep = pool.submit(check_reputation, rep_name)
        site_check, rep_check = f_site.result(), f_rep.result()

    checks = [c for c in (rbi, site_check, rep_check, msg_check) if c]
    score = max(0, min(100, 50 + sum(c["points"] for c in checks)))
    return {"score": score, "verdict": verdict(score), "checks": checks}
