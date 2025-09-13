import sqlite3, sqlite_vss, json, numpy as np
from typing import List, Tuple

def load_vss(conn: sqlite3.Connection):
    conn.enable_load_extension(True)
    sqlite_vss.load(conn)

class Storage:
    def __init__(self, db_path: str):
        self.c = sqlite3.connect(db_path)
        self.c.execute("PRAGMA foreign_keys = ON")
        self.c.execute("PRAGMA journal_mode = WAL")
        self.c.execute("PRAGMA synchronous = NORMAL")
        load_vss(self.c)

    # ----- schema -----
    def ensure_schema(self, schema_sql_path: str):
        with open(schema_sql_path, "r") as f:
            self.c.executescript(f.read())

    # ----- fetch / dedupe -----
    def get_seen_ids(self, arxiv_ids: list[str]) -> set[str]:
        q = "SELECT arxiv_id FROM papers WHERE arxiv_id IN (%s)" % ",".join("?"*len(arxiv_ids))
        rows = self.c.execute(q, arxiv_ids).fetchall() if arxiv_ids else []
        return {r[0] for r in rows}

    def upsert_papers(self, papers: list[dict]):
        if not papers:
            return

        # Prepare rows
        insert_rows = []
        update_rows = []
        for p in papers:
            authors_s = "; ".join(p.get("authors", []))
            cats_s = ",".join(p.get("categories", []))
            insert_rows.append((
                p["arxiv_id"], p["title"], authors_s, p["abstract"], cats_s,
                p["published_at"], p.get("updated_at"),
                p.get("pdf_url"), p.get("arxiv_url"),
                json.dumps(p.get("source", {})),
                p.get("abs_fp")
            ))
            update_rows.append((
                p["title"], authors_s, p["abstract"], cats_s,
                p.get("updated_at"), p.get("pdf_url"), p.get("arxiv_url"),
                json.dumps(p.get("source", {})), p.get("abs_fp"),
                p["arxiv_id"]
            ))

        # One transaction
        with self.c:
            # 1) Update existing rows (by arxiv_id)
            self.c.executemany("""
                UPDATE papers
                SET title=?,
                    authors=?,
                    abstract=?,
                    categories=?,
                    updated_at=?,
                    pdf_url=?,
                    arxiv_url=?,
                    source_json=?,
                    abs_fp=?
                WHERE arxiv_id=?
            """, update_rows)

            # 2) Insert new rows; ignore if abs_fp collides (UNIQUE on abs_fp) or arxiv_id collides
            self.c.executemany("""
                INSERT OR IGNORE INTO papers(
                    arxiv_id, title, authors, abstract, categories,
                    published_at, updated_at, pdf_url, arxiv_url, source_json, abs_fp
                )
                VALUES(?,?,?,?,?,?,?,?,?,?,?)
            """, insert_rows)

    # ----- embeddings / tags -----
    def vss_upsert_many(self, arxiv_ids: list[str], vecs: np.ndarray):
        """
        Insert/replace normalized float32 vectors into sqlite-vss.
        Keeps vss_map in sync so we can translate rowid<->arxiv_id.
        """
        assert vecs.dtype == np.float32
        cur = self.c.cursor()
        with self.c:  # single transaction
            for pid, v in zip(arxiv_ids, vecs):
                # ensure a rowid exists for this arxiv_id
                cur.execute("INSERT OR IGNORE INTO vss_map(arxiv_id) VALUES (?)", (pid,))
                cur.execute("SELECT rowid FROM vss_map WHERE arxiv_id=?", (pid,))
                (rid,) = cur.fetchone()
                # insert/replace into vss (rowid must match)
                cur.execute("INSERT OR REPLACE INTO vss_embeddings(rowid, embedding) VALUES (?, ?)",
                            (rid, memoryview(v.tobytes())))
            
    def fetch_papers_without_embedding(self, limit: int = 500) -> List[Tuple[str, str]]:
        """
        Returns [(arxiv_id, text_for_embedding), ...] for papers that
        do NOT have an embedding row yet.
        """
        rows = self.c.execute("""
        SELECT p.arxiv_id, p.title || CHAR(10) || p.abstract AS txt
        FROM papers p
        LEFT JOIN embeddings e ON e.arxiv_id = p.arxiv_id
        WHERE e.arxiv_id IS NULL
        ORDER BY p.created_at ASC
        LIMIT ?
        """, (limit,)).fetchall()
        return [(r[0], r[1] or "") for r in rows]

    def put_embeddings(self, items: list[tuple[str,str,np.ndarray]]):
        # items: [(arxiv_id, model, vec_np), ...]
        rows = []
        for arxiv_id, model, vec in items:
            vec = np.asarray(vec, dtype=np.float32)
            rows.append((arxiv_id, model, int(vec.size), vec.tobytes()))
        self.c.executemany("""
          INSERT INTO embeddings(arxiv_id,model,dim,vec)
          VALUES(?,?,?,?)
          ON CONFLICT(arxiv_id) DO UPDATE SET model=excluded.model, dim=excluded.dim, vec=excluded.vec
        """, rows)
        self.c.commit()

    def tag_papers(self, tags: list[tuple[str,str,float,str]]):
        # tags: [(arxiv_id, tag_name, score, source), ...]
        if not tags: return
        # ensure tag exists
        unique_tags = {(t[1],t[-1]) for t in tags}
        self.c.executemany("INSERT OR IGNORE INTO tags(name,kind) VALUES(?,?)", list(unique_tags))
        self.c.executemany("""
          INSERT INTO paper_tags(arxiv_id, tag_name, score, source)
          VALUES(?,?,?,?)
          ON CONFLICT(arxiv_id, tag_name) DO UPDATE SET score=excluded.score, source=excluded.source
        """, tags)
        self.c.commit()

    # ----- summaries -----
    def put_summary(self, arxiv_id: str, text: str, tokens_in: int, tokens_out: int, style: str, model: str):
        self.c.execute("""
          INSERT INTO summaries(arxiv_id,style,model,text,tokens_in,tokens_out)
          VALUES(?,?,?,?,?,?)
          ON CONFLICT(arxiv_id,style)
          DO UPDATE SET text=excluded.text, model=excluded.model,
                        tokens_in=excluded.tokens_in, tokens_out=excluded.tokens_out
        """, (arxiv_id, style, model, text, tokens_in, tokens_out))
        self.c.commit()

    # ----- reads for triage / digest -----
    def recent_papers(self, days: int=7) -> list[tuple]:
        return self.c.execute("""
          SELECT arxiv_id,title,abstract FROM papers
          WHERE datetime(published_at) >= datetime('now', ?)
        """, (f'-{days} days',)).fetchall()

    def fetch_embedding(self, arxiv_id: str):
        row = self.c.execute("SELECT dim, vec FROM embeddings WHERE arxiv_id=?", (arxiv_id,)).fetchone()
        if not row: return None
        dim, blob = row
        return np.frombuffer(blob, dtype=np.float32, count=dim)
