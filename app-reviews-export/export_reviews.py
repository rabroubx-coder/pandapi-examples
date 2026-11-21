"""Export App Store and Google Play reviews for one app to CSV.

Usage:
    pip install apify-client
    export APIFY_TOKEN=...            # free account: https://console.apify.com/settings/integrations
    python export_reviews.py --ios "Notion" --android notion.id --countries us gb

Writes appstore_reviews.csv, play_reviews.csv and summary.json (star split,
average per app version, top complaint phrases) in the current folder.
"""
import argparse
import csv
import json
import os

from apify_client import ApifyClient

APP_STORE_ACTOR = "blueberry_rainstorm/app-store-reviews-scraper"
GOOGLE_PLAY_ACTOR = "blueberry_rainstorm/google-play-reviews-scraper"

REVIEW_COLUMNS = ["store", "country", "language", "date", "rating", "appVersion",
                  "title", "text", "helpfulVotes", "thumbsUp", "developerReply", "reviewId"]


def run(client, actor, run_input):
    """Run an actor and return its dataset items, split into reviews and other rows."""
    finished = client.actor(actor).call(run_input=run_input)
    items = list(client.dataset(finished.default_dataset_id).iterate_items())
    reviews = [i for i in items if i.get("type") == "review"]
    other = [i for i in items if i.get("type") != "review"]
    return reviews, other


def write_csv(path, store, reviews):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=REVIEW_COLUMNS, extrasaction="ignore")
        w.writeheader()
        for r in reviews:
            w.writerow({**r, "store": store})
    return len(reviews)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--ios", help="App Store link, numeric ID, bundle ID or app name")
    p.add_argument("--android", help="Google Play link or package name, e.g. notion.id")
    p.add_argument("--countries", nargs="+", default=["us"])
    p.add_argument("--languages", nargs="+", default=["en"], help="Google Play review languages")
    p.add_argument("--max", type=int, default=1000, help="max reviews per app per country/language")
    p.add_argument("--since", help="only reviews on or after YYYY-MM-DD")
    args = p.parse_args()
    if not (args.ios or args.android):
        p.error("give --ios, --android or both")

    client = ApifyClient(os.environ["APIFY_TOKEN"])
    summary = {}

    if args.ios:
        inp = {"apps": [args.ios], "countries": args.countries,
               "maxReviewsPerApp": args.max, "reviewSort": "both"}
        if args.since:
            inp["reviewsSince"] = args.since
        reviews, other = run(client, APP_STORE_ACTOR, inp)
        print("App Store:", write_csv("appstore_reviews.csv", "appstore", reviews), "reviews")
        summary["appstore"] = other

    if args.android:
        inp = {"apps": [args.android], "languages": args.languages,
               "countries": args.countries[:1], "maxReviewsPerApp": args.max}
        if args.since:
            inp["reviewsSince"] = args.since
        reviews, other = run(client, GOOGLE_PLAY_ACTOR, inp)
        print("Google Play:", write_csv("play_reviews.csv", "googleplay", reviews), "reviews")
        summary["googleplay"] = other

    with open("summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, default=str)


if __name__ == "__main__":
    main()
