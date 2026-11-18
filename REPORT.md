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

References with links and the date each was read.
