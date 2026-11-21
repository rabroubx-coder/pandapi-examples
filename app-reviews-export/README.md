# Export App Store and Google Play reviews to CSV

One script, one app, both stores. It runs two Pandapi actors on Apify and writes:

- `appstore_reviews.csv`: up to 1,000 reviews per country (Apple's most recent and most helpful lists, merged without duplicates)
- `play_reviews.csv`: as many Google Play reviews as you ask for, per language
- `summary.json`: star split, average rating per app version, top complaint and praise phrases, worst recent reviews

```bash
pip install apify-client
export APIFY_TOKEN=...   # free Apify account, Settings > API & Integrations
python export_reviews.py --ios "Notion" --android notion.id --countries us gb --max 1000
```

Options: `--languages en de` (Google Play), `--since 2026-10-01` (only newer reviews).

Real run on 2026-11-19 (Notion, US + GB App Store, 2,000 newest English Google Play reviews): 1,502 App Store reviews in 6.5 s and 2,000 Google Play reviews in 7.4 s. Cost $0.23 + $0.20, inside the free $5 monthly Apify credit.

Price: App Store $0.15 per 1,000 reviews, Google Play $0.10 per 1,000 reviews, plus $0.001 per app details row.

Article: How to export App Store and Google Play reviews to CSV for free (Pandapi Blog).

Tests: `pytest test_export_reviews.py` (no network).
