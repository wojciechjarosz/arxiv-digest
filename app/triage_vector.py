from typing import List, Tuple
import numpy as np
from .storage_sqlite import Storage, assert_vss_ready
from .embeddings import Embedder

def normalize_1(v: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(v, axis=-1, keepdims=True) + 1e-9
    return (v / n).astype(np.float32)

def rank_query_vss(store: Storage, paper_ids: List[str], query: str, top_k: int = 20) -> List[Tuple[str, float]]:
    embedder = Embedder()
    q = embedder.embed([query])[0].astype(np.float32)
    q = normalize_1(q)
    #### dokonczyc wyszukiwanie tylko po nowych id
    rows = store.c.execute(f"""
        WITH knn AS (
            SELECT rowid, distance
            FROM vss_embeddings
            WHERE vss_search(embedding, ?)
            ORDER BY distance ASC
            LIMIT {top_k}
        )
        SELECT m.arxiv_id, knn.distance
        FROM knn
        JOIN vss_map AS m ON m.rowid = knn.rowid
        ORDER BY knn.distance ASC
    """, (memoryview(q.tobytes()),)).fetchall()

    # Convert distance -> similarity (optional): for normalized vecs, cosine ~ 1 - 0.5*L2
    # but you can just return -distance for a monotonic score
    result = [(pid, float(-dist)) for pid, dist in rows if pid in paper_ids]
    return result
