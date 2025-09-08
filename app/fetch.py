from tenacity import retry, wait_exponential, stop_after_attempt
from typing import List, Dict
from urllib.parse import urlencode, quote_plus

import feedparser
import time

ARXIV_BASE = "http://export.arxiv.org/api/query"

def _build_query(categories, max_results: int = 25) -> str:
    if not categories:
        raise ValueError("categories must be a non-empty list")
    # Join as "cat:cs.AI OR cat:cs.LG ..." then encode safely
    search = " OR ".join(f"cat:{c}" for c in categories)
    params = {
        "search_query": search,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
        "max_results": str(max_results),
    }
    # urlencode ensures spaces become '+' and everything is safe
    return f"{ARXIV_BASE}?{urlencode(params, quote_via=quote_plus)}"

@retry(wait=wait_exponential(multiplier=1, min=2, max=10), stop=stop_after_attempt(3))
def fetch_arxiv_feed(categories: List[str], max_results: int = 25) -> List[Dict]:
    """
    Fetches recent papers from arXiv Atom feed.
    Returns a list of dicts with id, title, authors, summary, link, published.
    Retries on transient network issues.
    """
    url = _build_query(categories, max_results)
    # Respect arXiv's guidance: set a custom user-agent and avoid hammering
    feedparser.USER_AGENT = "arxiv-digest/0.1 (contact: youremail@example.com)"
    parsed = feedparser.parse(url)

    entries = []
    for e in parsed.entries:
        entry = {
            "id": e.get("id"),
            "title": e.get("title", "").strip().replace("\n", " "),
            "summary": e.get("summary", "").strip(),
            "link": e.get("link"),
            "published": e.get("published"),
            "authors": [a.get("name") for a in e.get("authors", [])],
        }
        entries.append(entry)
    # A tiny courtesy sleep; we’ll be even nicer later when paging.
    time.sleep(0.5)
    return entries
