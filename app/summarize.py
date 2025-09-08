from dotenv import load_dotenv
from tenacity import retry, wait_exponential, stop_after_attempt
from typing import Dict, List

import logging, os, requests, textwrap

load_dotenv
# --- Config ---
DEFAULT_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")  # change as you wish
API_BASE = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
API_KEY = os.getenv("OPENAI_API_KEY") 

# --- Prompt Design ---
SYSTEM_PROMPT = (
    "You are an expert research analyst. Write concise executive summaries for AI papers. "
    "Audience: busy engineers and product leaders. Be accurate, neutral, and specific."
)

def build_user_prompt(title: str, authors: str, abstract: str) -> str:
    """
    Short, structured, executive-style prompt (aim ≤200 tokens output).
    """
    template = f"""
    Summarize the following paper in ~120–180 words. Use 5 short sections, each a single line:
    1) What it claims (plain language)
    2) How it works (key method/idea)
    3) Evidence (main results; include numbers if present)
    4) Limits (assumptions/weaknesses)
    5) Why it matters (practical relevance)

    Avoid equations/LaTeX. No hype. No bullets beyond those 5 lines.

    Title: {title.strip()}
    Authors: {authors.strip() if authors else "Unknown"}
    Abstract:
    {abstract.strip()}
    """
    return textwrap.dedent(template).strip()

# --- Token budget helpers (very rough heuristics) ---
def estimate_tokens(text: str) -> int:
    # ~4 chars/token heuristic; add 10% safety margin
    return int(len(text) / 4 * 1.1) + 1

def trim_text_to_tokens(text: str, max_tokens: int) -> str:
    # Trim by characters using the 4 chars/token heuristic
    max_chars = int(max_tokens * 4 * 0.9)
    return (text[:max_chars] + "…") if len(text) > max_chars else text

# --- Fallback extractive summarizer (no API key) ---
def local_fallback_summary(title: str, authors: str, abstract: str) -> str:
    lines = []
    abstract = abstract.strip().replace("\n", " ")
    sents = [s.strip() for s in abstract.split(". ") if s.strip()]
    # crude heuristics: pick first, a middle, and last-ish sentences
    picks = [sents[0] if sents else "",
             sents[len(sents)//2] if len(sents) > 2 else "",
             sents[-1] if sents else ""]
    body = ". ".join([p for p in picks if p])[:900]
    return (
        f"What: {title.strip()}.\n"
        f"How: Based on the abstract; method described by authors {authors or 'Unknown'}.\n"
        f"Evidence: {body}\n"
        f"Limits: Derived from abstract only; may omit details.\n"
        f"Why it matters: Potential impact depends on claimed contributions."
    )

# --- API call with retries ---
@retry(wait=wait_exponential(multiplier=1, min=2, max=8), stop=stop_after_attempt(3))
def _chat_completion(model: str, system_prompt: str, user_prompt: str, max_output_tokens: int = 220) -> str:
    url = f"{API_BASE}/chat/completions"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.2,
        "max_tokens": max_output_tokens,
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"].strip()

def summarize_papers(papers: List[Dict], max_input_tokens: int = 3000, max_output_tokens: int = 220) -> Dict[str, str]:
    """
    Summarize a list of papers. Returns {paper_id: summary}.
    Cost-aware: trims abstract if input budget would be exceeded.
    If no API key, returns local fallback summaries.
    """
    summaries: Dict[str, str] = {}

    for p in papers:
        pid = p["id"]
        title = p.get("title", "") or ""
        authors = p.get("authors", "") or ""
        abstract = p.get("summary", "") or ""

        # Input budgeting: cap the abstract if it's huge
        base_prompt = build_user_prompt(title, authors, abstract)
        if estimate_tokens(base_prompt) > max_input_tokens:
            # Rebuild with trimmed abstract
            trimmed_abs = trim_text_to_tokens(abstract, max_tokens=int(max_input_tokens * 0.6))
            base_prompt = build_user_prompt(title, authors, trimmed_abs)
            logging.info("Trimmed abstract for %s to fit token budget.", pid)

        if not API_KEY:
            logging.warning("OPENAI_API_KEY not set; using local fallback summarizer for %s", pid)
            summaries[pid] = local_fallback_summary(title, authors, abstract)
            continue

        try:
            out = _chat_completion(
                model=DEFAULT_MODEL,
                system_prompt=SYSTEM_PROMPT,
                user_prompt=base_prompt,
                max_output_tokens=max_output_tokens,
            )
            summaries[pid] = out
        except Exception as e:
            logging.error("Summarization failed for %s: %s", pid, e)
            # Soft fallback to local so the pipeline keeps moving
            summaries[pid] = local_fallback_summary(title, authors, abstract)

    return summaries
