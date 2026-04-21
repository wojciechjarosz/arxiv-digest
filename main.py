import os, logging
from datetime import datetime, UTC
from typing import Dict

from app.storage_sqlite import Storage
from app.fetch import fetch_arxiv_feed
from app.triage_vector import rank_query_vss
from app.summarize import summarize_papers
from app.deliver import build_digest_html, build_digest_text, send_email
from app.build_vector import build_vector_base

DB_PATH = os.getenv("DB_PATH", "/tmp/arxiv.db")
SCHEMA_SQL = os.getenv("SCHEMA_SQL_PATH", "db/schema.sql")
CATEGORIES = [c.strip() for c in os.getenv("ARXIV_CATEGORIES", "cs.DS,cs.DB,cs.IR,cs.DC,cs.NI,cs.OS").split(",") if c.strip()]
MAX_RESULTS = int(os.getenv("ARXIV_MAX_RESULTS", "100"))
TOP_N = int(os.getenv("TRIAGE_TOP_N", "20"))
MIN_SCORE = float(os.getenv("TRIAGE_MIN_SCORE", "1.0"))
SUBJECT_PREFIX = os.getenv("SUBJECT_PREFIX", "arXiv Digest")

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))

def _paper_to_storage(p: Dict) -> Dict:
    # fetch.py returns keys: id, title, summary, link, published, authors
    return {
        "arxiv_id": p["id"],
        "title": p["title"],
        "authors": p.get("authors", []),
        "abstract": p.get("summary", ""),
        "categories": p.get("categories", CATEGORIES),  # we queried by these; arXiv feed entry may also include cats but feedparser mapping varies
        "published_at": p.get("published") or datetime.now(UTC).isoformat(),
        "updated_at": None,
        "pdf_url": f"https://arxiv.org/pdf/{p["id"]}.pdf",
        "arxiv_url": p.get("link"),
        "source": p,
        "abs_fp": p.get("abs_fp"),
    }

def run():
    store = Storage(DB_PATH)
    # ensure schema present
    if os.path.exists(SCHEMA_SQL):
        store.ensure_schema(SCHEMA_SQL)

    logging.info("Fetching arXiv for categories=%s max=%d", CATEGORIES, MAX_RESULTS)
    papers = fetch_arxiv_feed(categories=CATEGORIES, max_results=MAX_RESULTS)
    if not papers:
        logging.info("No papers fetched, exiting.")
        return

    # de-dup
    ids = [p["id"] for p in papers]
    seen = store.get_seen_ids(ids)
    new_ids = [p["id"] for p in papers if p["id"] not in seen]
    logging.info("Fetched=%d, new=%d (seen=%d)", len(papers), len(new_ids), len(seen))
    
    papers = [_paper_to_storage(p) for p in papers if p['id'] in new_ids]
    # upsert new
    store.upsert_papers(papers)

    build_vector_base(store)

    # triage
    selected = rank_query_vss(store, "large language models; multimodal; safety", top_k=TOP_N, already_seen=len(seen))
    if not selected:
        logging.info("No papers selected after triage, exiting.")
        return
    logging.info("Selected %d papers after triage", len(selected))

    # tag by queried categories (score=1.0)
    tag_rows = []
    for p in selected:
        for cat in CATEGORIES:
            tag_rows.append((p[0], cat, p[1], "category"))
    if tag_rows:
        store.tag_papers(tag_rows)

    selected_ids = {p[0] for p in selected}
    
    selected_papers = [paper for paper in papers if paper["arxiv_id"] in selected_ids]
    if not selected_papers:
        logging.info("No papers found in DB for selected IDs, exiting.")
        return
    # summarize (exec style)
    summaries = summarize_papers(selected_papers, max_output_tokens=int(os.getenv("SUMMARY_TOKENS","500")))
    if not summaries:
        logging.info("No summaries generated, exiting.")
        return
    # persist summaries
    for summary in summaries:
        if summary.text:
            store.put_summary(**summary.__dict__)

    # build and send
    subject = f"{SUBJECT_PREFIX} — {datetime.now(UTC).strftime('%Y-%m-%d')}"
    body_html = build_digest_html(selected_papers, summaries)
    body_text = build_digest_text(selected_papers, summaries)
    send_email(subject, body_text, body_html)

if __name__ == "__main__":
    run()
