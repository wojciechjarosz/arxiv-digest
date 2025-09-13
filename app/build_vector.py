from dotenv import load_dotenv
from .storage_sqlite import Storage
from .embeddings import Embedder
import numpy as np, os

load_dotenv()

def l2_normalize(v: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(v, axis=1, keepdims=True) + 1e-9
    return (v / n).astype(np.float32)

def build_vector_base(store: Storage, batch: int = 128):
    store.ensure_schema(os.getenv("SCHEMA_SQL_PATH", "db/schema.sql"))
    embedder = Embedder()

    total = 0
    while True:
        todo = store.fetch_papers_without_embedding(limit=batch)
        if not todo:
            break
        ids, texts = zip(*todo)
        vecs = embedder.embed(list(texts))      # [n, d] float32
        vecs = l2_normalize(vecs)               # normalize!
        # write canonical copy
        store.put_embeddings([(pid, embedder.model, v) for pid, v in zip(ids, vecs)])
        # also insert into vss
        store.vss_upsert_many(list(ids), vecs)
        total += len(ids)
        print(f"[vectors] embedded+indexed {len(ids)} (total={total})")

    print("[vectors] up to date." if total == 0 else f"[vectors] added {total}.")