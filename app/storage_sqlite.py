import sqlite3, json, numpy as np

class Storage:
    def __init__(self, db_path: str):
        self.c = sqlite3.connect(db_path)
        self.c.execute("PRAGMA foreign_keys = ON")
        self.c.execute("PRAGMA journal_mode = WAL")

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
        if not papers: return
        rows = [(p["arxiv_id"], p["title"], "; ".join(p["authors"]), p["abstract"],
                 ",".join(p["categories"]), p["published_at"], p.get("updated_at"),
                 p.get("pdf_url"), p.get("arxiv_url"), json.dumps(p["source"]))
                for p in papers]
        self.c.executemany("""
          INSERT INTO papers(arxiv_id,title,authors,abstract,categories,published_at,updated_at,pdf_url,arxiv_url,source_json)
          VALUES(?,?,?,?,?,?,?,?,?,?)
          ON CONFLICT(arxiv_id) DO UPDATE SET
            title=excluded.title, authors=excluded.authors, abstract=excluded.abstract,
            categories=excluded.categories, updated_at=excluded.updated_at,
            pdf_url=excluded.pdf_url, arxiv_url=excluded.arxiv_url, source_json=excluded.source_json
        """, rows)
        self.c.commit()

    # ----- embeddings / tags -----
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
