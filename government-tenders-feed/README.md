# Government tenders feed in one script

Open tenders from SAM.gov (US), TED (EU), Find a Tender and Contracts Finder (UK), CanadaBuys and the World Bank, in one list with the same fields, saved to `tenders.csv`.

```bash
pip install "apify-client>=3"
export APIFY_TOKEN=...   # free Apify account, Settings > API & Integrations
python tenders_feed.py
```

Change `keywords`, or add `cpvCodes` (EU/UK), `naicsCodes` (US) or `countries` in the input. Each notice costs $0.002, and filtered-out notices are free. More options: [Government Tenders & Public Procurement API](https://apify.com/blueberry_rainstorm/public-tenders-feed).

Disclosure: made by Pandapi.
