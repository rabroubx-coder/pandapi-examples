"""Keep a RAG index in sync with a docs site.

Each run re-embeds only the pages that changed, adds new pages and deletes
chunks of pages that disappeared from the sitemap.

    pip install apify-client chromadb requests
    export APIFY_TOKEN=...            # free Apify account
    python rag_docs_sync.py https://docs.docker.com/sitemap.xml --include /compose/

How a page is judged "changed":
  1. Sitemap <lastmod> differs from last run  -> re-convert the page.
  2. No <lastmod> on the site                 -> re-convert it every --recheck-days
                                                 (default 7), because ETag and
                                                 Last-Modified headers change on every
                                                 deploy, not when the page changes.
  3. After converting, each chunk's text hash is compared with the stored one,
     so only chunks whose text really changed are re-embedded.
"""
import argparse, gzip, hashlib, json, os, re, sys, time
from datetime import datetime, timezone

import requests
import chromadb
from apify_client import ApifyClient

ACTOR = "blueberry_rainstorm/web-page-to-markdown"


def read_sitemap(url, seen=None):
    """Return {page_url: lastmod or None}; follows sitemap indexes and .gz files."""
    seen = seen if seen is not None else set()
    if url in seen:
        return {}
    seen.add(url)
    body = requests.get(url, timeout=30, headers={"User-Agent": "rag-docs-sync/1.0"}).content
    if body[:2] == b"\x1f\x8b":
        body = gzip.decompress(body)
    xml = body.decode("utf-8", "replace")
    pages = {}
    if "<sitemapindex" in xml:
        for child in re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", xml):
            pages.update(read_sitemap(child, seen))
        return pages
    for block in re.findall(r"<url>(.*?)</url>", xml, re.S):
        loc = re.search(r"<loc>\s*([^<\s]+)\s*</loc>", block)
        mod = re.search(r"<lastmod>\s*([^<\s]*)\s*</lastmod>", block)
        if loc:
            pages[loc.group(1)] = (mod.group(1) or None) if mod else None
    return pages


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def chunk_ids(url, chunks):
    """Stable ids: url + heading path + position under that heading.
    Adding a section only shifts ids inside that section, not the whole page."""
    out, seen = [], {}
    for c in chunks:
        path = c.get("headingPath") or ""
        n = seen.get(path, 0)
        seen[path] = n + 1
        out.append(f"{url}#{sha(path)}-{n}")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sitemap")
    ap.add_argument("--include", default="", help="only URLs containing this text")
    ap.add_argument("--max-pages", type=int, default=500)
    ap.add_argument("--db", default="./docs-index")
    ap.add_argument("--collection", default="docs")
    ap.add_argument("--state", default="./sync-state.json")
    ap.add_argument("--recheck-days", type=float, default=7)
    ap.add_argument("--chunk-size", type=int, default=400)
    args = ap.parse_args()

    state = json.load(open(args.state)) if os.path.exists(args.state) else {"pages": {}}
    known = state["pages"]  # url -> {lastmod, checked, chunks: {id: hash}}

    sitemap = {u: m for u, m in read_sitemap(args.sitemap).items() if args.include in u}
    urls = list(sitemap)[: args.max_pages]
    now = time.time()

    todo, reasons = [], {"new": 0, "lastmod changed": 0, "no lastmod, recheck due": 0}
    for u in urls:
        old = known.get(u)
        if old is None:
            todo.append(u); reasons["new"] += 1
        elif sitemap[u] and sitemap[u] != old.get("lastmod"):
            todo.append(u); reasons["lastmod changed"] += 1
        elif not sitemap[u] and now - old.get("checked", 0) > args.recheck_days * 86400:
            todo.append(u); reasons["no lastmod, recheck due"] += 1
    gone = [u for u in known if u not in sitemap]

    print(f"sitemap: {len(urls)} pages ({sum(1 for u in urls if sitemap[u])} with lastmod)")
    print(f"to convert: {len(todo)} {reasons}; removed from sitemap: {len(gone)}")

    col = chromadb.PersistentClient(path=args.db).get_or_create_collection(args.collection)
    stats = {"chunks upserted": 0, "chunks unchanged": 0, "chunks deleted": 0, "pages failed": 0}

    if todo:
        client = ApifyClient(os.environ["APIFY_TOKEN"])
        run = client.actor(ACTOR).call(run_input={
            "urls": [{"url": u} for u in todo],
            "maxPages": len(todo),
            "contentMode": "main",
            "chunkSize": args.chunk_size,
            "chunkOverlap": 50,
        })
        # apify-client 1.x returns a dict, 2.x+ a typed object
        dataset_id = run["defaultDatasetId"] if isinstance(run, dict) else run.default_dataset_id
        for page in client.dataset(dataset_id).iterate_items():
            url = page.get("url")
            if url not in sitemap:
                continue
            if page.get("status") != "ok":
                stats["pages failed"] += 1  # keep the old chunks, try again next run
                continue
            chunks = page.get("chunks") or []
            ids = chunk_ids(url, chunks)
            was_known = url in known
            old = known.get(url, {}).get("chunks", {})
            new = {}
            up_ids, up_docs, up_meta = [], [], []
            for cid, c in zip(ids, chunks):
                text = f'{c.get("headingPath") or ""}\n\n{c["text"]}'
                h = sha(text)
                new[cid] = h
                if old.get(cid) == h:
                    stats["chunks unchanged"] += 1
                    continue
                up_ids.append(cid); up_docs.append(text)
                up_meta.append({"url": url, "title": page.get("title") or "",
                                "section": c.get("headingPath") or ""})
            if up_ids:
                col.upsert(ids=up_ids, documents=up_docs, metadatas=up_meta)
                stats["chunks upserted"] += len(up_ids)
            stale = [cid for cid in old if cid not in new]
            if stale:
                col.delete(ids=stale)
                stats["chunks deleted"] += len(stale)
            if was_known and (up_ids or stale):
                print(f"  changed: {url} (+{len(up_ids)} / -{len(stale)} chunks)")
            known[url] = {"lastmod": sitemap[url], "checked": now, "chunks": new}

    for url in gone:
        ids = list(known[url].get("chunks", {}))
        if ids:
            col.delete(ids=ids)
            stats["chunks deleted"] += len(ids)
        del known[url]

    state["lastRun"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    json.dump(state, open(args.state, "w"), indent=1)
    print(stats, f"index size: {col.count()} chunks")


if __name__ == "__main__":
    sys.exit(main())
