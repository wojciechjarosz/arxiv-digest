#!/usr/bin/env bash
set -euo pipefail

: "${BUCKET:?}"                          # e.g., gs://arxiv-digest-data
DB="${DB_PATH:-/tmp/arxiv.db}"
STAMP="$(date +%Y%m%d-%H%M%S)"

# -------------------- Morning: pull DB or init --------------------
python - "$BUCKET" "$DB" <<'PY'
import os, sys, sqlite3
from google.cloud import storage

bucket_uri, db_path = sys.argv[1], sys.argv[2]
bucket_name = bucket_uri.replace("gs://", "", 1).strip("/")

os.makedirs(os.path.dirname(db_path), exist_ok=True)

client = storage.Client()
bucket = client.bucket(bucket_name)
blob = bucket.blob("arxiv.db")

if blob.exists():
    print(f"[bootstrap] downloading arxiv.db from gs://{bucket_name}/arxiv.db -> {db_path}")
    blob.download_to_filename(db_path)
else:
    print(f"[bootstrap] no existing DB found; initializing new SQLite at {db_path}")
    conn = sqlite3.connect(db_path)
    # WAL for better reliability; NORMAL is a good balance on Cloud Run
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.commit()
    conn.close()
PY

# -------------------- Play: run the pipeline ----------------------
python main.py --db "$DB"

# -------------------- Night: push snapshot + latest ---------------
python - "$BUCKET" "$DB" "$STAMP" <<'PY'
import sys
from google.cloud import storage

bucket_uri, db_path, stamp = sys.argv[1], sys.argv[2], sys.argv[3]
bucket_name = bucket_uri.replace("gs://", "", 1).strip("/")

client = storage.Client()
bucket = client.bucket(bucket_name)

snap_name = f"snapshots/arxiv-{stamp}.db"
print(f"[persist] uploading snapshot -> gs://{bucket_name}/{snap_name}")
bucket.blob(snap_name).upload_from_filename(db_path)

print(f"[persist] uploading latest   -> gs://{bucket_name}/arxiv.db")
bucket.blob("arxiv.db").upload_from_filename(db_path)
PY

echo "[done] entrypoint completed successfully."
