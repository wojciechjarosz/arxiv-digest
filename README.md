# arxiv-digest

A minimal pipeline that fetches recent AI papers from arXiv, filters them, summarizes the most relevant ones, and delivers a daily digest (via email or chat).

## Project structure

arxiv-digest/
├── app/
│ ├── fetch.py # fetch arXiv Atom feeds
│ ├── triage.py # (planned) keyword/relevance filtering
│ ├── summarize.py # (planned) LLM-based summarization
│ ├── deliver.py # (planned) email/chat delivery
│ └── db.py # (planned) SQLite storage
├── main.py # orchestrates the pipeline
├── pyproject.toml # dependencies + metadata
├── README.md
└── arxiv_digest.db # local sqlite db (runtime only)

## Installation

```bash
# create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# install dependencies
pip install -e .
```

## 🎯 MVP Milestone

This project has reached a **Minimum Viable Product (MVP)** state.  
The full end-to-end pipeline is live and automated.

### ✅ What works
- **Fetch**: Pulls the latest AI papers from arXiv feeds.  
- **Store**: Saves metadata in SQLite (local) or ephemeral `/tmp` (Cloud Run).  
- **Triage**: Scores and ranks papers based on keywords.  
- **Summarize**: Uses an LLM to generate concise, 5-line executive summaries.  
  - Local fallback summarizer when API key is missing or call fails.  
- **Deliver**: Sends daily digest via email (SMTP + Gmail App Password).  
  - Supports plain text + HTML email.  
- **Automate**: Runs as a **Cloud Run Job**, triggered daily via **Cloud Scheduler**.  
- **Secrets**: Sensitive values (OpenAI key, SMTP password) managed with **Secret Manager**.  
- **Config**: All runtime options via environment variables (no rebuild required).

### 🛠 Dev-friendly
- `.venv` for local runs (WSL/Linux).  
- Config knobs:
  - `INCLUDE_PROCESSED=true` → re-run already processed papers.  
  - `FORCE_TOP_N=true` → pick top N regardless of score.  
  - `DELIVER=false` → skip sending emails while testing.  
  - `SUMMARY_LANG=pl` → experimental Polish summaries.  
- Fallback summaries ensure the pipeline never breaks.

### 🚀 What’s next
- **Persistence**: Move from ephemeral SQLite to Firestore or Cloud SQL for cross-day de-duplication.  
- **Smarter triage**: Replace keyword scoring with vector search or lightweight ML ranking.  
- **Formatting**: Improved HTML digest (grouping by topic, clickable TOC).  
- **More delivery channels**: Slack, Telegram, or Teams integration.  
- **Monitoring**: Alerts if the daily job fails; metrics via Cloud Logging.  
- **Optimization**: Token budget control (smaller model for triage, bigger for summaries).  

---

👉 **Summary**: The MVP is complete — new AI papers are fetched, filtered, summarized, and delivered daily to your inbox, fully automated on Cloud Run. 🎉
