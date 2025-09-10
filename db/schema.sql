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
  source_json  TEXT NOT NULL,
  created_at   TEXT NOT NULL DEFAULT (datetime('now'))
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
