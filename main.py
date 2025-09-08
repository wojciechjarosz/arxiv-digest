from app.fetch import fetch_arxiv_feed
from app.db import init_db, upsert_papers, fetch_unprocessed, update_scores, mark_processed
from app.triage import rank
from app.summarize import summarize_papers
from app.deliver import build_digest_text, build_digest_html, send_email
from datetime import datetime
from dotenv import load_dotenv
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import logging, os

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)

# ---- Dev knobs via env vars ----
INCLUDE_PROCESSED = os.getenv("INCLUDE_PROCESSED", "0").lower() in ("1","true","yes")
FORCE_TOP_N       = os.getenv("FORCE_TOP_N", "0").lower() in ("1","true","yes")
MIN_SCORE         = float(os.getenv("MIN_SCORE", "1.0"))
DELIVER           = os.getenv("DELIVER", "1").lower() in ("1","true","yes")
# -------------------------------

def step_fetch_store(categories, max_results=25):
    logging.info("Fetching latest papers...")
    papers = fetch_arxiv_feed(categories, max_results=max_results)
    upsert_papers(papers)
    logging.info("Stored (new) papers. Total fetched: %d", len(papers))

def step_triage(top_n=5):
    logging.info("Loading unprocessed papers for triage...")
    candidates = fetch_unprocessed(limit=200)
    logging.info("Triage candidates: %d", len(candidates))
    top, scores = rank(candidates, top_n=top_n, min_score=1.0)
    update_scores(scores)
    return top

def step_summarize(top_papers):
    if not top_papers:
        logging.info("No top papers to summarize.")
        return {}
    logging.info("Summarizing %d papers...", len(top_papers))
    summaries = summarize_papers(top_papers, max_input_tokens=3000, max_output_tokens=220)
    # mark as processed now; delivery step will read summaries in-memory today
    mark_processed([p["id"] for p in top_papers])
    return summaries

def step_deliver(top_papers, summaries):
    if not top_papers:
        logging.info("Nothing to deliver.")
        return
    try:
        tz = ZoneInfo("Europe/Warsaw")
    except ZoneInfoNotFoundError:
        tz = ZoneInfo("UTC")
    today = datetime.now(tz).strftime("%Y-%m-%d")
    subject = f"arXiv AI digest — {today}"
    text_body = build_digest_text(top_papers, summaries)
    html_body = build_digest_html(top_papers, summaries)
    if DELIVER:
        send_email(subject, text_body, html_body)
        # Only mark processed after successful delivery
        mark_processed([p["id"] for p in top_papers])
    else:
        logging.info("DELIVER=0 set — skipping email send (dev mode).")

if __name__ == "__main__":
    init_db()
    # Adjust your default categories here
    categories = ["cs.AI", "cs.LG", "stat.ML"]
    step_fetch_store(categories, max_results=40)
    top = step_triage(top_n=5)

    print("\nTop picks to summarize:")
    for i, p in enumerate(top, 1):
        s = p.get("title", "").strip().replace("\n", " ")
        print(f"{i}. {s}  ({p.get('published')})")
        print(f"   {p.get('link')}")
    
    summaries = step_summarize(top)

    if summaries:
        print("\n=== Daily Digest (draft) ===")
        for i, p in enumerate(top, 1):
            sid = p["id"]
            print(f"\n{i}) {p['title'].strip()}")
            print(f"Link: {p.get('link')}")
            print(summaries.get(sid, "[No summary]"))

    step_deliver(top, summaries)