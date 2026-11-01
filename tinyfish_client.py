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


def safe_agent(url, goal):
    USAGE["agent"] += 1
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