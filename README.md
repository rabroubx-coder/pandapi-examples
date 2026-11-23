# Pandapi examples 🐼

Small, working scripts for [Pandapi](https://apify.com/blueberry_rainstorm) data APIs: clean input, clean output, pay per result.

| Folder | What it does |
|---|---|
| [pdf-tables-to-excel](pdf-tables-to-excel/) | Pull every table out of a list of PDFs into one Excel file (Python) |
| [government-tenders-feed](government-tenders-feed/) | Open tenders from SAM.gov, TED, the UK, Canada and the World Bank in one CSV (Python) |
| [app-reviews-export](app-reviews-export/) | App Store and Google Play reviews for any app into CSV, with a per-app summary (Python) |
| [rag-docs-sync](rag-docs-sync/) | Keep a RAG index in sync with a docs site: re-embed only changed pages, delete removed ones (Python, Chroma) |
| [pdf-to-markdown](pdf-to-markdown/) | Convert a folder of PDFs to Markdown: free locally with pymupdf4llm, OCR via the API only for scanned files (Python) |

Each folder has a README and a script you can run with a free Apify account (`APIFY_TOKEN`).

Disclosure: these examples use tools we make at Pandapi. The free/DIY alternatives are mentioned in each README.
