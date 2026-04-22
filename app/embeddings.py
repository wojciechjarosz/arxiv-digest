from dotenv import load_dotenv
from typing import List
import numpy as np, openai, os
import logging

load_dotenv()

class Embedder:
    def __init__(self):
        self.model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-large")
        self._client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def embed(self, texts: List[str]) -> np.ndarray:
        logging.info("method=%s", 'embed')
        resp = self._client.embeddings.create(model=self.model, input=texts)
        arr = np.array([d.embedding for d in resp.data], dtype=np.float32)
        return arr
