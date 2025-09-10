#!/usr/bin/env bash
set -euo pipefail
BUCKET="${BUCKET:?}"
DB="${DB_PATH:-/tmp/arxiv.db}"
STAMP=$(date +%Y%m%d-%H%M%S)

# morning
if gsutil -q stat "$BUCKET/arxiv.db"; then
  gsutil cp "$BUCKET/arxiv.db" "$DB"
else
  sqlite3 "$DB" 'PRAGMA journal_mode=WAL; VACUUM;'
fi

# play
python -m arxiv_digest.main --db "$DB"

# night
gsutil cp "$DB" "$BUCKET/snapshots/arxiv-$STAMP.db"
gsutil cp "$DB" "$BUCKET/arxiv.db"