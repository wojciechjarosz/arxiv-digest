# arxiv-digest

A minimal pipeline that fetches recent AI papers from arXiv, filters them, summarizes the most relevant ones, and delivers a daily digest (via email or chat).

## Project structure
```
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
```

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

## CI/CD & Releases

This repo ships a lightweight pipeline for the daily **arxiv-digest** job.

### Deploy pipeline (GitHub Actions)
- **When**: on pushes to `main` (and manual **Run workflow**).
- **What**:
  1. (Optional) quick Python import smoke.
  2. Auth to GCP using **Workload Identity Federation** (OIDC).
  3. Build container with **Cloud Build**:  
     `gcloud builds submit --tag "europe-central2-docker.pkg.dev/$PROJECT_ID/arxiv-digest/arxiv-digest:${GITHUB_SHA}"`
  4. Update the **Cloud Run Job** image:  
     `gcloud run jobs update arxiv-digest-job --image "…:${GITHUB_SHA}"`
  5. (Optional) Execute the job immediately (manual toggle).

**Required GitHub Secrets**
- `GCP_PROJECT_ID` – your GCP project id.
- `GCP_WIF_PROVIDER` – the full WIF provider path (from the setup script), e.g.  
  `projects/123456789/locations/global/workloadIdentityPools/github-pool/providers/github`

**Repo permissions**
- Actions needs `id-token: write` to fetch the GitHub OIDC token.
- Default `GITHUB_TOKEN` is enough for Release Please.

### Workload Identity Federation (one-time)
Run the provided script in this README to create:
- WIF pool and provider for GitHub OIDC.
- CI service account: `arxiv-digest-ci@…`
- IAM roles (least-privilege):
  - `roles/cloudbuild.builds.editor` (run builds)
  - `roles/run.admin` (update Cloud Run Job)
  - `roles/iam.serviceAccountUser` (actAs if needed)
- Grants `roles/artifactregistry.writer` to the project Cloud Build SA so builds can push.

### Releases & CHANGELOG
- We use **Conventional Commits**. Common types:
  - `feat:` new feature
  - `fix:` bug fix
  - `docs:`, `chore:`, `refactor:`, `perf:`, `test:`, `ci:`, `build:`
- The **release-please** action opens a **Release PR** updating `CHANGELOG.md` and version.
- Merging that PR creates a **Git tag** and **GitHub Release** with notes.

### Cutting a release
1. Merge PRs with conventional commit messages.
2. Wait for the **Release PR** (`release-please--branches--main`).
3. Merge the Release PR → tag + release are created automatically.

### Acceptance checklist
- Push a commit to `main`:
  - ✅ CI builds & pushes image.
  - ✅ Cloud Run Job updated to `…:${GITHUB_SHA}`.
  - ✅ (Optional) Execute job → logs show the new image tag.
- Merge a `feat:` or `fix:` PR:
  - ✅ Release PR opens.
  - ✅ `CHANGELOG.md` updates.
  - ✅ Git tag + GitHub Release created.


### 🚀 What’s next
- **Persistence**: Move from ephemeral SQLite to Firestore or Cloud SQL for cross-day de-duplication.  
- **Smarter triage**: Replace keyword scoring with vector search or lightweight ML ranking.  
- **Formatting**: Improved HTML digest (grouping by topic, clickable TOC).  
- **More delivery channels**: Slack, Telegram, or Teams integration.  
- **Monitoring**: Alerts if the daily job fails; metrics via Cloud Logging.  
- **Optimization**: Token budget control (smaller model for triage, bigger for summaries).  

---

👉 **Summary**: The MVP is complete — new AI papers are fetched, filtered, summarized, and delivered daily to your inbox, fully automated on Cloud Run. 🎉