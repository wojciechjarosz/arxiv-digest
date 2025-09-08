# Changelog
All notable changes to this project will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2025-09-08
### Added
- End-to-end MVP pipeline:
  - Fetch arXiv feeds (cs.AI, cs.LG, stat.ML)
  - SQLite storage (local) / `/tmp` in Cloud Run
  - Keyword-based triage and scoring
  - LLM summaries with local fallback
  - Email delivery via SMTP (text + HTML)
  - Cloud Run Job + Cloud Scheduler daily trigger
- Configuration via environment variables; secrets via Secret Manager
- Basic logging, retries, and token budgeting

### Notes
- DB persistence is ephemeral in Cloud Run; consider Firestore/Cloud SQL later.
