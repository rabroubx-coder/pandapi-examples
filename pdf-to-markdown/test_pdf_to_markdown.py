import csv

import pdf_to_markdown as p2m


def test_counts():
    md = "# Title\n\n| a | b |\n|---|---|\n| 1 | 2 |\n\ntext here"
    assert p2m.count_tables(md) == 1
    assert p2m.count_words("one two  three\nfour") == 4


def test_looks_scanned():
    assert p2m.looks_scanned(0, 3)
    assert p2m.looks_scanned(30, 3)          # 10 words a page
    assert not p2m.looks_scanned(6000, 15)
    assert not p2m.looks_scanned(0, 0)


class FakeClient:
    """Stands in for ApifyClient: records the input, returns one OCR result per file."""

    def __init__(self):
        self.run_input = None

    def actor(self, name):
        assert name == p2m.ACTOR
        return self

    def call(self, run_input):
        self.run_input = run_input
        return {"defaultDatasetId": "ds1"}

    def dataset(self, dataset_id):
        assert dataset_id == "ds1"
        return self

    def iterate_items(self):
        for f in self.run_input["base64Pdfs"]:
            yield {"fileName": f["name"], "status": "ok", "markdown": "# Scan\n\nRead by OCR",
                   "pagesProcessed": 3, "ocrPages": [1, 2, 3]}


def test_only_scans_go_to_the_api(tmp_path):
    src = tmp_path / "pdfs"
    src.mkdir()
    (src / "paper.pdf").write_bytes(b"%PDF-1.4 digital")
    (src / "scan.pdf").write_bytes(b"%PDF-1.4 scanned")

    def fake_local(path):
        if path.name == "paper.pdf":
            return "# Paper\n\n" + "word " * 500, 2
        return "", 3

    client = FakeClient()
    rows = p2m.main([str(src), "--out", str(tmp_path / "md")], client=client, local=fake_local)
    assert [f["name"] for f in client.run_input["base64Pdfs"]] == ["scan.pdf"]
    assert client.run_input["ocr"] == "auto"
    by_file = {r["file"]: r for r in rows}
    assert by_file["paper.pdf"]["route"] == "local"
    assert by_file["scan.pdf"]["route"] == "api" and by_file["scan.pdf"]["ocr_pages"] == 3
    assert (tmp_path / "md" / "scan.md").read_text() == "# Scan\n\nRead by OCR"
    summary = list(csv.DictReader(open(tmp_path / "md" / "summary.csv")))
    assert len(summary) == 2


def test_no_scans_means_no_client_needed(tmp_path):
    src = tmp_path / "pdfs"
    src.mkdir()
    (src / "a.pdf").write_bytes(b"%PDF")
    rows = p2m.main([str(src), "--out", str(tmp_path / "md")], client=None,
                    local=lambda p: ("text " * 100, 1))
    assert rows[0]["route"] == "local"


def test_api_all_sends_everything(tmp_path):
    src = tmp_path / "pdfs"
    src.mkdir()
    for n in ("a.pdf", "b.pdf"):
        (src / n).write_bytes(b"%PDF")
    client = FakeClient()
    p2m.main([str(src), "--out", str(tmp_path / "md"), "--api-all", "--lang", "eng", "deu"], client=client,
             local=lambda p: (_ for _ in ()).throw(AssertionError("local should not run")))
    assert len(client.run_input["base64Pdfs"]) == 2
    assert client.run_input["ocrLanguages"] == ["eng", "deu"]
