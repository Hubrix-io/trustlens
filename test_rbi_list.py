from rbi_list import load_list, search_rbi_list

df = load_list()
print("Rows loaded:", len(df))
print(df[["app", "entity", "entity_type"]].head(5).to_string())

for name in ["GeM Sahay", "121 finance", "FastCashNow99"]:
    r = search_rbi_list(name)
    print("\n", name, "->", r["status"])
    for m in r["matches"][:2]:
        print("   ", m["app"], "|", m["entity"], "|", m["available_on"])