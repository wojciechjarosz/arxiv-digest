import sqlite3
from contextlib import contextmanager
from typing import Iterable, Dict, List
import datetime
import os

DB_PATH = os.getenv("DB_PATH", "/tmp/arxiv_digest.db")

@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

def init_db():
    with get_conn() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS papers (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            summary TEXT NOT NULL,
            link TEXT,
            published TEXT,
            authors TEXT,
            added_at TEXT NOT NULL,
            processed INTEGER NOT NULL DEFAULT 0,  -- set to 1 after summarization
            score REAL                              -- triage score (nullable)
        )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_processed ON papers(processed)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_published ON papers(published)")

def upsert_papers(papers: Iterable[Dict]):
    """
    Insert new papers; ignore if id already exists.
    """
    now = datetime.datetime.utcnow().isoformat() + "Z"
    rows = [
        (
            p["id"],
            p.get("title", ""),
            p.get("summary", ""),
            p.get("link"),
            p.get("published"),
            "; ".join(p.get("authors", [])) if p.get("authors") else None,
            now,
        )
        for p in papers
    ]
    with get_conn() as conn:
        conn.executemany("""
            INSERT OR IGNORE INTO papers (id, title, summary, link, published, authors, added_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, rows)

def fetch_unprocessed(limit: int = 100) -> List[Dict]:
    with get_conn() as conn:
        cur = conn.execute("""
            SELECT id, title, summary, link, published, authors, score
            FROM papers
            WHERE processed = 0
            ORDER BY published DESC
            LIMIT ?
        """, (limit,))
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]

def update_scores(scores: Dict[str, float]):
    """
    scores: dict of {paper_id: score}
    """
    with get_conn() as conn:
        conn.executemany(
            "UPDATE papers SET score = ? WHERE id = ?",
            [(score, pid) for pid, score in scores.items()]
        )

def mark_processed(paper_ids: Iterable[str]):
    with get_conn() as conn:
        conn.executemany(
            "UPDATE papers SET processed = 1 WHERE id = ?",
            [(pid,) for pid in paper_ids]
        )

def fetch_candidates(limit: int = 100, include_processed: bool = False) -> List[Dict]:
    with get_conn() as conn:
        where = "" if include_processed else "WHERE processed = 0"
        cur = conn.execute(f"""
            SELECT id, title, summary, link, published, authors, score, processed
            FROM papers
            {where}
            ORDER BY COALESCE(published, added_at) DESC
            LIMIT ?
        """, (limit,))
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]