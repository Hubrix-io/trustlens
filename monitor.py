"""Watch a lender: save each audit as a snapshot and report what changed.

Streamlit has no background scheduler, so re-checks run when you press the button
in the app, or on a schedule if you run this file from cron / GitHub Actions:

    python monitor.py            # re-check every lender on the watchlist
"""
import json
import os
import time

from audit import run_audit

PATH = "data/watchlist.json"


def load():
    try:
        with open(PATH, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save(d):
    os.makedirs(os.path.dirname(PATH), exist_ok=True)
    with open(PATH, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)


def add(app_name, website=""):
    d = load()
    key = app_name.strip().lower()
    d.setdefault(key, {"app": app_name.strip(), "website": website.strip(), "history": []})
    _save(d)
    return key


def remove(key):
    d = load()
    d.pop(key, None)
    _save(d)


def recheck(key):
    """Run a fresh audit, compare with the last snapshot, save, return the changes."""
    d = load()
    item = d[key]
    result = run_audit(item["app"], item["website"], use_research=False)
    snap = {"time": time.strftime("%Y-%m-%d %H:%M"),
            "score": result["score"],
            "statuses": {c["name"]: c["status"] for c in result["checks"]}}
    changes = []
    if item["history"]:
        prev = item["history"][-1]
        if prev["score"] != snap["score"]:
            changes.append(f"Score {prev['score']} → {snap['score']}")
        for name, status in snap["statuses"].items():
            old = prev["statuses"].get(name)
            if old and old != status:
                changes.append(f"{name}: {old} → {status}")
    item["history"].append(snap)
    item["history"] = item["history"][-20:]
    _save(d)
    return {"snapshot": snap, "changes": changes, "first": len(item["history"]) == 1}


if __name__ == "__main__":
    for k in load():
        r = recheck(k)
        print(k, r["snapshot"]["score"], r["changes"] or "no change")
