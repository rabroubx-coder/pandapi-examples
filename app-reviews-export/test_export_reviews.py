import csv
import export_reviews as er


def test_write_csv_keeps_columns_and_store(tmp_path):
    rows = [
        {"type": "review", "country": "us", "date": "2026-11-16", "rating": 2, "title": "Nav",
         "text": "Hard to find pages", "appVersion": "1.7.353", "reviewId": "1", "extra": "ignored"},
        {"type": "review", "language": "en", "date": "2026-11-18", "rating": 1,
         "text": "Login problems", "thumbsUp": 0, "developerReply": None, "reviewId": "2"},
    ]
    out = tmp_path / "r.csv"
    assert er.write_csv(out, "appstore", rows) == 2
    got = list(csv.DictReader(open(out, encoding="utf-8")))
    assert list(got[0].keys()) == er.REVIEW_COLUMNS
    assert got[0]["store"] == "appstore" and got[1]["text"] == "Login problems"


def test_run_splits_reviews(monkeypatch):
    class DS:
        def iterate_items(self):
            return iter([{"type": "review", "reviewId": "1"}, {"type": "app"}, {"type": "summary"}])

    class Run:
        default_dataset_id = "ds"

    class Actor:
        def call(self, run_input):
            return Run()

    class Client:
        def actor(self, name):
            return Actor()

        def dataset(self, ds_id):
            return DS()

    reviews, other = er.run(Client(), "x", {})
    assert len(reviews) == 1 and [o["type"] for o in other] == ["app", "summary"]
