from typing import List, Tuple
import numpy as np
from .storage_sqlite import Storage
from .embeddings import Embedder
import logging

def normalize_1(v: np.ndarray) -> np.ndarray:
    logging.info("method=%s", 'normalize_1')
    n = np.linalg.norm(v, axis=-1, keepdims=True) + 1e-9
    return (v / n).astype(np.float32)

def rank_query_vss(store: Storage, query: str, top_k: int = 20,  already_seen: int = 0) -> List[Tuple[str, float]]:
    logging.info("method=%s", 'rank_query_vss')
    embedder = Embedder()
    q = embedder.embed([query])[0].astype(np.float32)
    q = normalize_1(q)
    limit_k = top_k + already_seen
    if limit_k <= 0:
        raise ValueError(f"Invalid limit for vss search: {limit_k}")
    query = f"""
        WITH knn AS (
            SELECT rowid, distance
            FROM vss_embeddings
            WHERE vss_search(embedding, (memoryview(q.tobytes()),))
            ORDER BY distance ASC
            LIMIT {limit_k}
        )
        SELECT m.arxiv_id, knn.distance
        FROM knn
        JOIN vss_map AS m ON m.rowid = knn.rowid
        LEFT JOIN summaries s ON s.arxiv_id = m.arxiv_id
        WHERE s.arxiv_id IS NULL
        ORDER BY knn.distance ASC
    """
    logging.info("query=%s", query)
    rows = store.c.execute(query).fetchall()

    # Convert distance -> similarity (optional): for normalized vecs, cosine ~ 1 - 0.5*L2
    # but you can just return -distance for a monotonic score
    result = [(pid, float(-dist)) for pid, dist in rows]
    return result[:top_k]
