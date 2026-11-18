Repository: https://github.com/tkob-team/seminar-c3-hybrid-search

> Note: this report is at most 3 pages.

# Report — Hybrid search vs vector-only (C3)

## Question

In PostgreSQL with pgvector, how much does hybrid search (HNSW vector search fused with built-in full-text search via reciprocal rank fusion) raise recall@10 over vector-only search on a public labeled retrieval dataset, and how much does it add to p95 query latency (ms)?

**Answer:** it does not raise recall@10. On CQADupStack android, hybrid search **lowered recall@10 by 10.1 points** (60.6% → 50.5%) and **added 42.7 ms to p95** (2.1 → 44.8 ms, about 20×). It also lowered recall on the two other subforums we measured. A stricter AND full-text query removed the harm, at about 1.3× p95.

## Setup (versions, machine, data, load)

- **Software:** PostgreSQL 18.7 + pgvector 0.8.7 (`pgvector/pgvector:0.8.7-pg18-trixie`). Client: Python 3.12 + psycopg 3.3.9, in a separate container on the same Docker network.
- **Machine:** i5-13500H (12 cores / 16 threads), 16 GB RAM, Windows 11, Docker Desktop on WSL2. The database container is limited to 2 CPUs / 4 GB.
- **Data:** BEIR CQADupStack via `mteb/cqadupstack-*` (pinned revisions): android 22,998 docs / 699 queries (main); mathematica 16,705 / 804; gaming 45,301 / 1,595.
- **Embeddings:** `BAAI/bge-small-en-v1.5`, computed once on CPU (15.7 s per 100 docs), stored and checked by sha256.
- **Load:** one connection, one query at a time; 1 warm-up pass + 5 runs per branch, branch order alternated. Latency = SQL execute + fetch at the client; query embedding not included.

## Baseline and change

- **A — vector-only (baseline):** top-10 of 100 HNSW candidates (cosine).
- **B — hybrid (change):** the same 100 vector candidates, plus the top-100 from full-text search (OR tsquery, `ts_rank`), fused by RRF (Σ 1/(60 + rank)), top-10.

Nothing else differs (`sql/vector_only.sql`, `sql/hybrid.sql`).

## Held fixed

Subforum: CQADupStack android (BEIR) · Embeddings: BAAI/bge-small-en-v1.5, normalized, instruction prefix on queries only, embedding files fixed by sha256 · Software: PostgreSQL 18 + pgvector 0.8.7 (pgvector/pgvector:0.8.7-pg18-trixie) · HNSW: m = 16, ef_construction = 64, hnsw.ef_search = 100, iterative scan off · Full-text: 'english' config, OR tsquery, ts_rank · Fusion: RRF, N = 100 candidates per branch, k = 60, top-10 · Resources: container limited to 2 CPUs and 4 GB RAM · Runs: 1 warm-up pass, 5 measured runs, alternating branch order · p95: nearest-rank · Latency: SQL execution time only, measured at the client. For mathematica and gaming, only the subforum changes.

## Results (median + spread, units)

Recall@10 was identical in all 5 runs of every measurement, so it has no spread. p95 = median of 5 runs (min–max).

| Subforum | recall@10 A → B (%) | Δ (pp) | B better/worse/same | p95 A (ms) | p95 B (ms) | B/A |
|---|---|---|---|---|---|---|
| android | 60.63 → 50.54 | −10.09 | 33/133/533 | 2.12 (1.45–2.50) | 44.80 (41.30–48.90) | 21.1× |
| mathematica | 41.65 → 33.27 | −8.38 | 32/117/655 | 2.15 (1.86–2.19) | 55.75 (55.00–57.72) | 25.9× |
| gaming | 69.98 → 63.51 | −6.48 | 93/226/1276 | 2.35 (2.20–4.57) | 47.86 (47.15–51.29) | 20.4× |

nDCG@10 (secondary) drops the same way (0.476 → 0.401, 0.297 → 0.238, 0.561 → 0.507). Three separate `make measure` runs on android gave p95 B = 44.80 / 44.28 / 43.40 ms (A = 2.12 / 2.33 / 2.25 ms) with identical recall.

<!-- S14: internal rerun on another machine — fill after the rerun (machine, recall A/B, p95 B/A ratio, README issues). -->

**Why hybrid lost.** The median OR query matches 41% of the android corpus (mathematica 31%, gaming 14%). `ts_rank`, which is not BM25, ranks these thousands of weak matches poorly. So full-text alone reaches only 35.4% recall@10, against 60.6% for vector (mathematica 19.2 vs 41.7, gaming 47.3 vs 70.0).

RRF then weighs both lists equally. A document ranked about 30th in *both* lists scores 2/90 ≈ 0.022, which beats the vector list's correct answer at rank 1 when that answer is absent from the full-text top-100 (1/61 ≈ 0.016). Example: for "How to use an android phone as a wireless webcam?", the duplicate is vector rank 1 but full-text rank 7,754, and it drops out of the hybrid top-10 (`results/examples.md`).

The loss shrinks as the OR query gets narrower: −10.1 → −8.4 → −6.5 pp for matched share 41% → 31% → 14%. With only three subforums, this is a pattern, not a proof.

**Why it is slower.** Broad OR queries make PostgreSQL scan the table instead of using the GIN index, and compute `ts_rank` for every matching row.

**Supplementary, not the answer: hybrid with an AND full-text query.**

| Subforum | Δ recall@10 (pp) | better/worse (sign test p) | p95 A → B (ms) | B/A |
|---|---|---|---|---|
| android | −0.42 | 16/20 (0.62) | 2.14 → 2.79 | 1.30× |
| mathematica | −0.32 | 9/14 (0.40) | 2.13 → 2.75 | 1.29× |
| gaming | +0.94 | 40/23 (0.04) | 2.26 → 2.99 | 1.32× |

## Recommendation (incl. when not to use)

- **Do not add PostgreSQL full-text search through an OR query with equal-weight RRF** on top of a reasonable embedding model. In all three subforums it cost 6–10 recall points and about 20× p95 (+42–54 ms).
- **If you want hybrid search in PostgreSQL, keep the full-text branch precise** (AND). It was harmless, and slightly helpful only on gaming, where full-text alone reached about two-thirds of vector recall. The cost was about +0.7 ms p95. Measure full-text-only recall on your own labeled queries first.
- **When not to use hybrid search:** the full-text branch is much weaker than vector; queries share common domain words ("android" appears in 47% of documents); or the latency budget is tight and the full-text query is broad.

## Limits

- **Embedding model:** only one, and its card does not list its training data. It may have seen StackExchange, which would make the vector baseline unusually strong here.
- **Full-text ranking:** `ts_rank` is not BM25, and we tested no other full-text engine.
- **Fusion settings:** RRF k = 60, N = 100, equal weights; no other values were tested.
- **Subforums:** 3 of 12. mathematica and gaming were chosen after the android result, by a criterion written down before measuring them (`notes/S23-subforum-khac.md`, `results/subforum-screening.csv`). All measured subforums are reported here.
- **Latency:** one machine, Docker on WSL2, one client, no concurrent load. Absolute ms will differ elsewhere; the B/A ratio should transfer better.
- **Inputs and AND variant:** queries are titles only; documents are truncated at 512 tokens. AND is one supplementary configuration; its gaming gain is small (p ≈ 0.04, uncorrected for three comparisons).
- **No dedicated vector database** was compared; that would be a second change.

## Sources (link + date read)

- pgvector README (HNSW, `hnsw.ef_search`, iterative scan, Docker tags): https://github.com/pgvector/pgvector — read 2026-11-18; version used: pgvector 0.8.7.
- Docker image `pgvector/pgvector`: https://hub.docker.com/r/pgvector/pgvector — read 2026-11-18; tag used: `0.8.7-pg18-trixie`.
- PostgreSQL 18 docs, Full Text Search: https://www.postgresql.org/docs/18/textsearch.html — read 2026-11-18; version used: 18.7.
- Model card `BAAI/bge-small-en-v1.5`: https://huggingface.co/BAAI/bge-small-en-v1.5 — read 2026-11-18; revision used: `5c38ec7c405ec4b44b94cc5a9bb96e735b38267a`.
- Datasets `mteb/cqadupstack-{android, mathematica, gaming}`: https://huggingface.co/datasets/mteb/cqadupstack-android (and `-mathematica`, `-gaming`) — read 2026-11-18; revisions used: android `e03f271e3f4a`, mathematica `fc1af0b6c82d`, gaming `1c9769860b1d` (full hashes in `scripts/common.py`).
- BEIR (Thakur et al., 2021): https://arxiv.org/abs/2104.08663 — read 2026-11-18.
- Client libraries: sentence-transformers 6.3.0 (https://sbert.net; torch 2.15.0+cpu, transformers 5.23.0), psycopg 3.3.9 (https://www.psycopg.org/psycopg3/docs/) with pgvector-python 0.5.1 — read 2026-11-18.
