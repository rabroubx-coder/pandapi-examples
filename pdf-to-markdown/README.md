# PDF to Markdown: free locally, OCR only for scans

Converts a folder of PDFs to Markdown.

- **Digital PDFs** are converted on your machine with [pymupdf4llm](https://pypi.org/project/pymupdf4llm/) (free, keeps headings and tables).
- **Scanned PDFs** (fewer than 20 words a page) are sent to the [Pandapi PDF API](https://apify.com/blueberry_rainstorm/pdf-to-text-markdown?utm_source=github&utm_medium=post&utm_campaign=pdf-to-text-markdown) on Apify, which runs OCR. You only pay for those: $3 per 1,000 PDFs plus $5 per 1,000 OCR pages. Apify's free plan includes $5 of credit a month.

```bash
pip install pymupdf4llm apify-client
export APIFY_TOKEN=...            # only needed when a scan is found
python pdf_to_markdown.py ./pdfs --out ./markdown
```

```
attention.pdf: local, 15 pages, 6218 words, 4 tables
fw9.pdf: local, 6 pages, 6132 words, 10 tables
```

Output: one `.md` per PDF and `summary.csv` (file, route, pages, words, tables, ocr_pages).

Options:

- `--api-all`: send every PDF to the API (no local install of PyMuPDF needed for conversion; useful on small servers).
- `--lang eng deu fra`: OCR languages.

## Fully free alternative for scans

`pymupdf4llm` 2.x runs OCR itself when an OCR engine is installed: `pip install rapidocr onnxruntime` (about 95 MB). In our test a 3-page scan took 11.4 s on 4 CPU cores. If that's fine for you, you don't need the API at all.

Licences: PyMuPDF / pymupdf4llm are AGPL-3.0 (or a commercial licence from Artifex). This script is MIT.

## Tests

```bash
pip install pytest
pytest -q
```

The tests use a fake Apify client, so they run offline and cost nothing.

Disclosure: we make the PDF API at Pandapi.
