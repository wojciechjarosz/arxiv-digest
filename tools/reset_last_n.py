from app.db import get_conn
import sys
n = int(sys.argv[1]) if len(sys.argv) > 1 else 5
with get_conn() as conn:
    ids = [r[0] for r in conn.execute(
        "SELECT id FROM papers ORDER BY COALESCE(published, added_at) DESC LIMIT ?", (n,)
    ).fetchall()]
    conn.executemany("UPDATE papers SET processed = 0, score = NULL WHERE id = ?", [(i[0] if isinstance(i, tuple) else i,) for i in ids])
print(f"Reset processed on {len(ids)} most recent papers.")