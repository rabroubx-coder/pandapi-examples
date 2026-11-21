"""Open government tenders from SAM.gov, TED (EU), UK, Canada and the World Bank in one list.

pip install "apify-client>=3"
APIFY_TOKEN=... python tenders_feed.py
"""
import csv
import os

from apify_client import ApifyClient

client = ApifyClient(os.environ["APIFY_TOKEN"])
run = client.actor("blueberry_rainstorm/public-tenders-feed").call(run_input={
    "keywords": ["cybersecurity", "penetration testing"],
    "postedWithinDays": 14,
    "minDaysLeft": 7,
})

tenders = list(client.dataset(run.default_dataset_id).iterate_items())
tenders.sort(key=lambda t: (not t.get("matchedInTitle"), t.get("daysLeft") or 999))

for t in tenders:
    print(f'{t["countryName"] or "":<15} {str(t["daysLeft"] or "-"):>3}d  {t["valueEur"] or "":>10}  {t["title"][:70]}')

fields = ["source", "countryName", "buyerName", "title", "deadline", "daysLeft", "valueEur", "valueUsd", "matchedInTitle", "url"]
with open("tenders.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
    w.writeheader()
    w.writerows(tenders)
print(f"{len(tenders)} tenders saved to tenders.csv")
