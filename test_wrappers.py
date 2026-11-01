from tinyfish_client import safe_search, safe_agent, USAGE

print("--- SEARCH ---")
s = safe_search("121 Finance Private Limited complaints reviews")
print(s["ok"])
for x in s.get("results", []):
    print(x["title"], "|", x["url"])

print("\n--- AGENT ---")
a = safe_agent(
    "https://121finance.com",
    "Check whether this website mentions the app 'GeM Sahay' or lists its "
    "digital lending apps. Also find a grievance officer contact if shown. "
    "Return JSON with keys: mentions_app (true/false), grievance_contact, "
    "evidence_url."
)
print(a)

print("\nUSAGE:", USAGE)