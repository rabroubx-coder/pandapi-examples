"""Convert a folder of PDFs to Markdown: free locally, OCR only for scanned files.

Digital PDFs are converted on your machine with pymupdf4llm (free). PDFs with no
text layer (scans, photos of pages) are sent to the Pandapi PDF API on Apify, which
runs OCR and returns Markdown. You only pay for the scanned ones.

Usage:
    pip install pymupdf4llm apify-client
    export APIFY_TOKEN=...      # only needed if a scanned PDF is found
    python pdf_to_markdown.py ./pdfs --out ./markdown
    python pdf_to_markdown.py ./pdfs --out ./markdown --api-all   # send every PDF to the API

Writes one .md per PDF and summary.csv (file, route, pages, words, tables).
"""
import argparse
import base64
import csv
import os
import pathlib
import re

ACTOR = "blueberry_rainstorm/pdf-to-text-markdown"
MIN_WORDS_PER_PAGE = 20  # below this a PDF is treated as scanned


def count_words(md):
    return len(md.split())


def count_tables(md):
    return sum(1 for line in md.splitlines() if re.match(r"^\|\s*:?-{3,}", line))


def looks_scanned(words, pages):
    return pages > 0 and words / pages < MIN_WORDS_PER_PAGE


def convert_local(path):
    """Free route. Returns (markdown, pages)."""
    import pymupdf
    import pymupdf4llm

    with pymupdf.open(path) as doc:
        pages = doc.page_count
    return pymupdf4llm.to_markdown(str(path)), pages


def convert_api(client, paths, languages=("eng",)):
    """Paid route: one actor run for all files. Returns {file name: (markdown, pages, ocr pages)}."""
    run_input = {
        "base64Pdfs": [{"name": p.name, "data": base64.b64encode(p.read_bytes()).decode()} for p in paths],
        "ocr": "auto",
        "ocrLanguages": list(languages),
        "includeText": False,
        "includeTables": False,
        "spreadsheetOutput": "none",
    }
    finished = client.actor(ACTOR).call(run_input=run_input)
    dataset_id = finished["defaultDatasetId"] if isinstance(finished, dict) else finished.default_dataset_id
    out = {}
    for item in client.dataset(dataset_id).iterate_items():
        if item.get("status") == "ok":
            out[item["fileName"]] = (item.get("markdown", ""), item.get("pagesProcessed", 0), len(item.get("ocrPages") or []))
    return out


def main(argv=None, client=None, local=convert_local):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("folder")
    ap.add_argument("--out", default="markdown")
    ap.add_argument("--api-all", action="store_true", help="send every PDF to the API, not only scans")
    ap.add_argument("--lang", nargs="+", default=["eng"], help="OCR languages, e.g. eng deu fra")
    args = ap.parse_args(argv)

    out_dir = pathlib.Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    rows, to_api = [], []
    for pdf in sorted(pathlib.Path(args.folder).glob("*.pdf")):
        if args.api_all:
            to_api.append(pdf)
            continue
        md, pages = local(pdf)
        words = count_words(md)
        if looks_scanned(words, pages):
            to_api.append(pdf)
            continue
        (out_dir / f"{pdf.stem}.md").write_text(md, encoding="utf-8")
        rows.append({"file": pdf.name, "route": "local", "pages": pages, "words": words,
                     "tables": count_tables(md), "ocr_pages": 0})

    if to_api:
        if client is None:
            from apify_client import ApifyClient
            client = ApifyClient(os.environ["APIFY_TOKEN"])
        for name, (md, pages, ocr_pages) in convert_api(client, to_api, args.lang).items():
            (out_dir / f"{pathlib.Path(name).stem}.md").write_text(md, encoding="utf-8")
            rows.append({"file": name, "route": "api", "pages": pages, "words": count_words(md),
                         "tables": count_tables(md), "ocr_pages": ocr_pages})

    with open(out_dir / "summary.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["file", "route", "pages", "words", "tables", "ocr_pages"])
        w.writeheader()
        w.writerows(rows)
    for r in rows:
        print(f"{r['file']}: {r['route']}, {r['pages']} pages, {r['words']} words, {r['tables']} tables")
    return rows


if __name__ == "__main__":
    main()
