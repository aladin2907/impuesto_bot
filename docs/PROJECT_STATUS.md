# Project Status (Code Reality)

This document describes the current state of the repository based on the code,
not the historical deployment docs.

## Current State

- The API cannot start as-is: `app/api/webhook.py` imports
  `app/services/search_service`, but that module is missing.
- `app/services/rag/langchain_rag.py` still uses Elasticsearch via
  `langchain_elasticsearch`, yet `app/config/settings.py` no longer defines
  `ELASTICSEARCH_URL` or `ELASTICSEARCH_API_KEY`, and
  `langchain-elasticsearch` is not listed in `requirements.txt`.
- Supabase integration exists only for user/session management in
  `app/services/supabase_service.py`. Repository classes under `app/repositories`
  are present, but vector search methods are stubs and there is no unified
  search service wiring them into the API.
- Embeddings: `app/services/embeddings/huggingface_embeddings.py` uses
  `sentence_transformers`, which is not listed in `requirements.txt`.
- Ingestion scripts are partial: only Telegram and Calendar migration scripts
  exist under `scripts/ingestion/`. There are no active scripts for PDF or News.
- Tests are absent (only `tests/__pycache__` remains).

## Documentation Mismatch

Most docs still describe the Elasticsearch-based production system from
October 2025 (see `docs/SUMMARY.md` and `docs/DEPLOYMENT_SUCCESS_REPORT.md`).
Those documents should be treated as historical snapshots until the current
code path is restored or completed.

## Immediate Decision Needed

Pick the target search backend and align code + docs:

- If Elasticsearch: restore `search_service.py`, Elasticsearch config in
  `app/config/settings.py`, and dependencies (`langchain-elasticsearch`,
  `elasticsearch`).
- If Supabase/pgvector: implement vector search RPCs, repository search methods,
  and a new unified `search_service` to replace the Elasticsearch RAG path.

