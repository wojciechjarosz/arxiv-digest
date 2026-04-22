CREATE TABLE IF NOT EXISTS papers (
  arxiv_id     TEXT PRIMARY KEY,
  title        TEXT NOT NULL,
  authors      TEXT NOT NULL,        -- "A; B; C"
  abstract     TEXT NOT NULL,
  categories   TEXT NOT NULL,        -- "cs.CL,cs.LG"
  published_at TEXT NOT NULL,        -- ISO8601
  updated_at   TEXT,
  pdf_url      TEXT,
  arxiv_url    TEXT,
  source_json  TEXT,
  abs_fp       TEXT,                 -- fingerprint of abstract (SHA-256, etc.)
  created_at   TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_papers_absfp ON papers(abs_fp)
  WHERE abs_fp IS NOT NULL;

-- Virtual table with FAISS index. Use your embedding dim (3072 for text-embedding-3-large)
CREATE VIRTUAL TABLE IF NOT EXISTS vss_embeddings USING vss0(embedding(3072));

-- Map arxiv_id to vss rowid (rowid is the primary key of vss_embeddings)
CREATE TABLE IF NOT EXISTS vss_map (
  rowid     INTEGER PRIMARY KEY,  -- must match vss_embeddings.rowid
  arxiv_id  TEXT NOT NULL UNIQUE REFERENCES papers(arxiv_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS embeddings (
  arxiv_id TEXT PRIMARY KEY REFERENCES papers(arxiv_id) ON DELETE CASCADE,
  model    TEXT NOT NULL,
  dim      INTEGER NOT NULL,
  vec      BLOB NOT NULL,            -- float32 bytes
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS tags (
  name TEXT PRIMARY KEY,
  kind TEXT NOT NULL DEFAULT 'topic'  -- topic|model|domain|custom
);

CREATE TABLE IF NOT EXISTS paper_tags (
  arxiv_id TEXT REFERENCES papers(arxiv_id) ON DELETE CASCADE,
  tag_name TEXT REFERENCES tags(name) ON DELETE CASCADE,
  score    REAL,
  source   TEXT,
  PRIMARY KEY (arxiv_id, tag_name)
);

CREATE TABLE IF NOT EXISTS summaries (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  arxiv_id      TEXT REFERENCES papers(arxiv_id) ON DELETE CASCADE,
  style         TEXT NOT NULL,        -- "exec"|"pl"|"eli5"
  model         TEXT NOT NULL,
  text  TEXT NOT NULL,
  tokens_in     INTEGER,
  tokens_out    INTEGER,
  created_at    TEXT NOT NULL DEFAULT (datetime('now')),
  UNIQUE (arxiv_id, style)
);

