# Changelog
All notable changes to this project will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.0](https://github.com/wojciechjarosz/arxiv-digest/compare/v1.1.0...v1.2.0) (2025-09-10)


### Features

* data model and storage design ([19d7497](https://github.com/wojciechjarosz/arxiv-digest/commit/19d749778b8a86ab19e92e2f7e5ca631ba45f9fa))

## [1.1.0](https://github.com/wojciechjarosz/arxiv-digest/compare/v1.0.0...v1.1.0) (2025-09-08)


### Features

* don't rebuild on release-please only ([0b58f9b](https://github.com/wojciechjarosz/arxiv-digest/commit/0b58f9b4b5ec65e4878ec4dff2bfe37bb17a72db))

## 1.0.0 (2025-09-08)


### Bug Fixes

* create and bucket for build ([9f02f19](https://github.com/wojciechjarosz/arxiv-digest/commit/9f02f198f90b3e79bb66c770b462495d34073a36))
* remove readme.md to .dockerignore ([6e42cdb](https://github.com/wojciechjarosz/arxiv-digest/commit/6e42cdbbb6fefa2e2e82dc2b8535c3c3cd082c84))
* rename cloud run job name ([3fcc840](https://github.com/wojciechjarosz/arxiv-digest/commit/3fcc8402a7f5f67aae7b3bf888164a7a3c482121))

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
