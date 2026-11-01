from dotenv import load_dotenv
load_dotenv()

from tinyfish import TinyFish

client = TinyFish()

resp = client.search.query("RBI digital lending apps directory")
print("Total results:", resp.total_results)
for r in resp.results[:5]:
    print(r.title, "|", r.url)
    