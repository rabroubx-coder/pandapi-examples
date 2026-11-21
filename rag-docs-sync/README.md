# Keep a RAG index in sync with a docs site

Re-embed only the documentation pages that changed, add new pages, and delete the chunks of pages that disappeared. One file, a local [Chroma](https://www.trychroma.com/) index, and a state file.

```bash
pip install apify-client chromadb requests
export APIFY_TOKEN=...   # free Apify account, Settings > API & Integrations
python rag_docs_sync.py https://docs.docker.com/sitemap.xml --include /compose/
```

Run it again whenever you like (cron, GitHub Actions, an Apify schedule). Each run prints what it did:

```
sitemap: 87 pages (43 with lastmod)
to convert: 45 {'new': 1, 'lastmod changed': 0, 'no lastmod, recheck due': 44}; removed from sitemap: 0
{'chunks upserted': 0, 'chunks unchanged': 156, 'chunks deleted': 0, 'pages failed': 1} index size: 525 chunks
```

## How it decides what changed

1. **Sitemap `<lastmod>`.** If it differs from the last run, the page is converted again. Pages with an unchanged `lastmod` cost nothing.
2. **No `<lastmod>`** (FastAPI, Playwright, Pydantic and Supabase docs have none): the page is re-checked every `--recheck-days` (default 7). ETag and Last-Modified headers are no help here, because docs sites rebuild every page on each deploy.
3. **Chunk hashes.** After converting, every chunk's text is hashed. Only chunks whose text changed are re-embedded; chunks that vanished from a page are deleted.

Chunk ids are `url#hash(heading path)-n`, so adding a section to a page only touches the ids under that heading.

## Options

| Flag | Default | |
|---|---|---|
| `--include` | (all) | only sitemap URLs containing this text, e.g. `/docs/` |
| `--max-pages` | 500 | cap per run |
| `--recheck-days` | 7 | re-convert pages without `<lastmod>` after this many days |
| `--chunk-size` | 400 | approximate tokens per chunk |
| `--db`, `--collection`, `--state` | `./docs-index`, `docs`, `./sync-state.json` | where things are stored |

## Cost

Conversion uses [Website to Markdown for RAG & LLMs](https://apify.com/blueberry_rainstorm/web-page-to-markdown) at $1 per 1,000 pages converted (failed pages are free). The Docker Compose docs (87 pages) cost $0.086 to index (86 pages converted, 1 empty page free) and $0.044 per weekly re-check. Chroma embeds locally for free. Swap in any other vector store by changing the `upsert` and `delete` calls.

The free alternative for the conversion step: fetch each page with `requests` and convert it with `trafilatura` or `markdownify`. You'll need your own handling for JavaScript-only pages and heading-aware chunking.

Disclosure: made by Pandapi.
