import re
import difflib
import pandas as pd

FILE = "data/rbi_dla_list.xlsx"
_df = None


def _norm(s):
    """lowercase, remove symbols, collapse spaces"""
    return " ".join(re.sub(r"[^a-z0-9]+", " ", str(s).lower()).split())


def _find_col(columns, *keywords):
    for c in columns:
        low = c.lower()
        if all(k in low for k in keywords):
            return c
    return None


def load_list():
    global _df
    if _df is not None:
        return _df

    raw = pd.read_excel(FILE, header=None, dtype=str)

    # find the real header row (the one that contains "Name of the DLA")
    header_row = None
    for i in range(min(20, len(raw))):
        row_text = " ".join(str(v) for v in raw.iloc[i].tolist()).lower()
        if "name of the dla" in row_text:
            header_row = i
            break
    if header_row is None:
        raise ValueError("Could not find the header row. Send me the first 6 rows.")

    cols = [" ".join(str(c).split()) for c in raw.iloc[header_row]]
    df = raw.iloc[header_row + 1:].copy()
    df.columns = cols

    c_entity = _find_col(cols, "entity name")
    c_site   = _find_col(cols, "website of re")
    c_type   = _find_col(cols, "entity type")
    c_app    = _find_col(cols, "name of the dla")
    c_owner  = _find_col(cols, "owner of dla")
    c_avail  = _find_col(cols, "available on")
    c_link   = _find_col(cols, "link to dla")
    c_email  = _find_col(cols, "email")

    # fill blanks caused by merged cells in Excel
    for c in (c_entity, c_site, c_type):
        if c:
            df[c] = df[c].ffill()

    out = pd.DataFrame({
        "entity":    df[c_entity],
        "entity_site": df[c_site],
        "entity_type": df[c_type],
        "app":       df[c_app],
        "owner":     df[c_owner] if c_owner else "",
        "available_on": df[c_avail] if c_avail else "",
        "link":      df[c_link] if c_link else "",
        "grievance_email": df[c_email] if c_email else "",
    })
    out = out.dropna(subset=["app"]).reset_index(drop=True)
    out["app_norm"] = out["app"].map(_norm)
    out["entity_norm"] = out["entity"].map(_norm)
    out["owner_norm"] = out["owner"].map(_norm)

    _df = out
    return _df


def _rows_to_dicts(rows, limit):
    keep = ["app", "entity", "entity_type", "owner", "available_on",
            "link", "entity_site", "grievance_email"]
    return rows[keep].head(limit).fillna("").to_dict("records")


def search_rbi_list(query, limit=5):
    """
    Returns {"status": "found" | "possible" | "not_found" | "too_short",
             "matches": [...]}
    """
    df = load_list()
    q = _norm(query)
    if len(q) < 3:
        return {"status": "too_short", "matches": []}

    # 1. exact app name
    exact = df[df["app_norm"] == q]
    if len(exact):
        return {"status": "found", "matches": _rows_to_dicts(exact, limit)}

    # 2. query appears inside an app, lender or owner name
    mask = (df["app_norm"].str.contains(q, regex=False)
            | df["entity_norm"].str.contains(q, regex=False)
            | df["owner_norm"].str.contains(q, regex=False))
    part = df[mask]
    if len(part):
        return {"status": "found", "matches": _rows_to_dicts(part, limit)}

    # 3. similar spelling
       # 3. similar spelling
    names = df["app_norm"].unique().tolist()
    close = difflib.get_close_matches(q, names, n=3, cutoff=0.8)
    if close:
        rows = df[df["app_norm"].isin(close)]
        return {"status": "possible", "matches": _rows_to_dicts(rows, limit)}

    return {"status": "not_found", "matches": []}