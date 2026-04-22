import os, logging, gc
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
TRIAGE_QUERY = (
    "practical data engineering; production data platforms; distributed data systems; "
    "ETL and ELT pipelines; orchestration; stream processing; batch processing; "
    "data quality; observability; metadata; lineage; governance; storage formats; "
    "query optimization; warehouse and lakehouse architecture; reliability; scalability; "
    "latency; throughput; fault tolerance; cost optimization; production ML and AI infrastructure"
)

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
        "source": None,
        "abs_fp": p.get("abs_fp"),
    }

def _chunks(seq, size):
    for i in range(0, len(seq), size):
        yield seq[i:i+size]

def run():
    store = Storage(DB_PATH)
    if os.path.exists(SCHEMA_SQL):
        store.ensure_schema(SCHEMA_SQL)

    logging.info("Fetching arXiv for categories=%s max=%d", CATEGORIES, MAX_RESULTS)
    fetched = fetch_arxiv_feed(categories=CATEGORIES, max_results=MAX_RESULTS)
    if not fetched:
        logging.info("No papers fetched, exiting.")
        return

    ids = [p["id"] for p in fetched]
    seen = store.get_seen_ids(ids)
    raw_new = [p for p in fetched if p["id"] not in seen]
    del fetched
    gc.collect()
    
    logging.info("New papers=%d", len(raw_new))
    if not raw_new:
        return

    stored_new = []
    for batch in _chunks(raw_new, 20):
        batch_rows = [_paper_to_storage(p) for p in batch]
        store.upsert_papers(batch_rows)
        logging.info(f"papers = {store.c.execute('SELECT COUNT(*) FROM papers').fetchone()[0]}")
        stored_new.extend(batch_rows)
    
    del batch_rows
    gc.collect()
    
    build_vector_base(store, batch=16)

    selected = rank_query_vss(
        store,
        TRIAGE_QUERY,
        top_k=TOP_N,
        already_seen=len(seen),
    )
    if not selected:
        logging.info("No papers selected after triage, exiting.")
        return

    selected_ids = {p[0] for p in selected}
    selected_papers = [paper for paper in stored_new if paper["arxiv_id"] in selected_ids]

    all_summaries = []
    for batch in _chunks(selected_papers, 5):
        batch_summaries = summarize_papers(
            batch,
            max_output_tokens=int(os.getenv("SUMMARY_TOKENS", "500"))
        )
        if not batch_summaries:
            continue
        for summary in batch_summaries:
            if summary.text:
                store.put_summary(**summary.__dict__)
        all_summaries.extend(batch_summaries)

    if not all_summaries:
        logging.info("No summaries generated, exiting.")
        return
    del batch_summaries
    gc.collect()
    
    subject = f"{SUBJECT_PREFIX} — {datetime.now(UTC).strftime('%Y-%m-%d')}"
    body_html = build_digest_html(selected_papers, all_summaries)
    body_text = build_digest_text(selected_papers, all_summaries)
    send_email(subject, body_text, body_html)
    
if __name__ == "__main__":
    run()