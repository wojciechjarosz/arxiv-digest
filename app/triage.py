from typing import Dict, List

import re

DEFAULT_KEYWORDS = {
    # keyword: weight
    r"\b(llm|language model|transformer|gpt)\b": 3.0,
    r"\b(rag|retrieval[- ]augmented|retrieval)\b": 2.5,
    r"\b(multimodal|vision[- ]language|audio|video)\b": 2.0,
    r"\b(agent|tool[- ]use|planning)\b": 2.0,
    r"\b(distillation|compression|quantization)\b": 1.8,
    r"\b(inference|latency|throughput)\b": 1.5,
    r"\b(benchmark|leaderboard|dataset)\b": 1.5,
    r"\b(alignment|safety|robustness)\b": 1.5,
    r"\b(reinforcement learning|rl)\b": 1.4,
    r"\b(diffusion|generative)\b": 1.2,
}

DEFAULT_EXCLUDES = [
    r"\b(quantum|biology|astronomy|chemistry)\b",
    r"\b(category theory|algebraic topology)\b",
]

_title_boost = 1.5  # titles count a bit more

def _compile_patterns(d: Dict[str, float]):
    return [(re.compile(pat, re.I), w) for pat, w in d.items()]

def _compile_list(lst: List[str]):
    return [re.compile(pat, re.I) for pat in lst]

def score_paper(paper: Dict, inc=None, exc=None) -> float:
    """
    Simple keyword scoring on title + abstract.
    """
    inc = _compile_patterns(inc or DEFAULT_KEYWORDS)
    exc = _compile_list(exc or DEFAULT_EXCLUDES)
    title = paper.get("title", "") or ""
    text = f"{title}\n{paper.get('summary', '') or ''}"

    # exclude early
    for pat in exc:
        if pat.search(text):
            return 0.0

    score = 0.0
    for pat, w in inc:
        # more weight if keyword is in title
        if pat.search(title):
            score += w * _title_boost
        # also count in abstract
        if pat.search(text):
            score += w

    # small length penalty to prefer concise abstracts
    length = len(paper.get("summary", ""))
    score -= 0.0005 * max(0, length - 2000)

    return max(0.0, score)

def rank(papers: List[Dict], top_n: int = 5, min_score: float = 1.0) -> tuple[List[Dict], Dict[str, float]]:
    """
    Returns (top, scores_map) where top is a list of selected papers.
    """
    scores = {}
    for p in papers:
        s = score_paper(p)
        scores[p["arxiv_id"]] = s
    ranked = sorted(papers, key=lambda x: scores[x["arxiv_id"]], reverse=True)
    top = [p for p in ranked if scores[p["arxiv_id"]] >= min_score][:top_n]
    return top, scores
