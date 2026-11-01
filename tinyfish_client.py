from dotenv import load_dotenv
load_dotenv()

from tinyfish import TinyFish

client = TinyFish()

# counts tool use, shown later in the UI
USAGE = {"search": 0, "fetch": 0, "agent": 0, "research": 0, "monitor": 0}


def safe_search(query, n=5):
    USAGE["search"] += 1
    try:
        r = client.search.query(query)
        items = [{"title": x.title, "url": x.url,
                  "snippet": getattr(x, "snippet", "")} for x in r.results[:n]]
        return {"ok": True, "results": items}
    except Exception as e:
        return {"ok": False, "error": str(e)}


LIVE_VIEW = False   # the app switches this on from a checkbox
LIVE = {}           # label -> live browser URL, read by the UI


def _stream_agent(url, goal, label):
    """EXPERIMENTAL: uses the SDK's streaming call to capture the live-browser URL.
    Raises if the SDK does not support it, and the caller falls back to .run()."""
    result, status, error = None, "", None
    for ev in client.agent.stream(url=url, goal=goal):
        surl = getattr(ev, "streaming_url", None)
        if surl and label:
            LIVE[label] = surl
        if getattr(ev, "result", None) is not None:
            result = ev.result
        if getattr(ev, "status", None):
            status = str(ev.status)
        if getattr(ev, "error", None):
            error = str(ev.error)
    if result is None:
        raise RuntimeError("stream gave no result")
    return {"ok": status.upper().endswith("COMPLETED") or not status,
            "result": result, "error": error}


def safe_agent(url, goal, label=None):
    USAGE["agent"] += 1
    if LIVE_VIEW and label:
        try:
            return _stream_agent(url, goal, label)
        except Exception:
            pass  # fall back to the normal blocking call below
    try:
        r = client.agent.run(url=url, goal=goal)
        done = str(r.status).upper().endswith("COMPLETED")
        return {"ok": done, "result": r.result,
                "error": str(r.error) if r.error else None}
    except Exception as e:
        return {"ok": False, "result": None, "error": str(e)}


def safe_fetch(url):
    USAGE["fetch"] += 1
    try:
        r = client.fetch.get_contents([url])
        if r.errors and not r.results:
            return {"ok": False, "error": str(r.errors)[:300]}
        return {"ok": True, "raw": str(r.results)[:4000]}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def safe_research(query, mode="standard"):
    USAGE["research"] += 1
    try:
        try:
            r = client.research.run(query=query, mode=mode)
        except TypeError:
            r = client.research.run(query=query)
        text = None
        for attr in ("report", "result", "final_result", "summary"):
            v = getattr(r, attr, None)
            if v:
                text = v if isinstance(v, str) else str(v)
                break
        if text is None:
            text = str(r)
        return {"ok": True, "report": text[:3000]}
    except Exception as e:
        return {"ok": False, "error": str(e)[:300]}
def safe_fetch_text(url, limit=30000):
    USAGE["fetch"] += 1
    try:
        r = client.fetch.get_contents([url])
        if r.errors and not r.results:
            return {"ok": False, "text": "", "error": str(r.errors)[:300]}
        parts = []
        for item in r.results:
            got = None
            for attr in ("text", "content", "markdown", "html", "body"):
                v = getattr(item, attr, None)
                if isinstance(v, str) and v.strip():
                    got = v
                    break
            parts.append(got if got else str(item))
        return {"ok": True, "text": "\n".join(parts)[:limit], "error": None}
    except Exception as e:
        return {"ok": False, "text": "", "error": str(e)[:300]}