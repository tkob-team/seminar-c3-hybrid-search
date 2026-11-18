Repository: https://github.com/tkob-team/seminar-c3-hybrid-search

> Note: this report is at most 3 pages.

# Report — Hybrid search vs vector-only (C3)

## Question

The question this seminar answers.

## Setup (versions, machine, data, load)

Software versions, machine specs, dataset, and query load used.

## Baseline and change

Baseline (vector-only) and the change under test (hybrid with RRF).

## Held fixed

Subforum: CQADupStack android (BEIR) · Embeddings: BAAI/bge-small-en-v1.5, normalized, instruction prefix on queries only, embedding files fixed by sha256 · Software: PostgreSQL 18 + pgvector 0.8.7 (pgvector/pgvector:0.8.7-pg18-trixie) · HNSW: m = 16, ef_construction = 64, hnsw.ef_search = 100, iterative scan off · Full-text: 'english' config, OR tsquery, ts_rank · Fusion: RRF, N = 100 candidates per branch, k = 60, top-10 · Resources: container limited to 2 CPUs and 4 GB RAM · Runs: 1 warm-up pass, 5 measured runs, alternating branch order · p95: nearest-rank · Latency: SQL execution time only, measured at the client.

## Results (median + spread, units)

Recall@10 (%) and p95 latency (ms), reported as median with spread.

## Recommendation (incl. when not to use)

What we recommend, and when hybrid search is not worth it.

## Limits

Threats to validity and what this measurement does not cover.

## Sources (link + date read)

- pgvector README (HNSW, `hnsw.ef_search`, iterative scan, Docker tags): https://github.com/pgvector/pgvector — read 2026-11-18; version used: pgvector 0.8.7.
- Docker image `pgvector/pgvector`: https://hub.docker.com/r/pgvector/pgvector — read 2026-11-18; tag used: `0.8.7-pg18-trixie`.
- PostgreSQL documentation, Full Text Search (`to_tsquery`, `plainto_tsquery`, `ts_rank`, GIN): https://www.postgresql.org/docs/18/textsearch.html — read 2026-11-18; version used: PostgreSQL 18.7.
- Model card `BAAI/bge-small-en-v1.5` (384 dimensions, 512 tokens, query instruction): https://huggingface.co/BAAI/bge-small-en-v1.5 — read 2026-11-18; revision used: `5c38ec7c405ec4b44b94cc5a9bb96e735b38267a`.
- Dataset `mteb/cqadupstack-android` (BEIR CQADupStack android: corpus, queries, test qrels): https://huggingface.co/datasets/mteb/cqadupstack-android — read 2026-11-18; revision used: `e03f271e3f4a75f49787c838a62f671b35bc9004`.
- sentence-transformers (`SentenceTransformer.encode`, `normalize_embeddings`): https://sbert.net — read 2026-11-18; version used: 6.3.0 (with torch 2.15.0+cpu, transformers 5.23.0).
- psycopg 3 (`RawCursor` with `$1` placeholders, `COPY`): https://www.psycopg.org/psycopg3/docs/ — read 2026-11-18; version used: psycopg 3.3.9 (`psycopg[binary]`), with pgvector-python 0.5.1.
