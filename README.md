# seminar-c3-hybrid-search

CSC13114 seminar, topic C3: hybrid search (pgvector HNSW + PostgreSQL full-text, fused with RRF) vs vector-only search, measured by recall@10 (%) and p95 latency (ms).

## Requirements

- **Docker** with Compose v2 (`docker compose`). The database container is limited to **2 CPUs and 4 GB RAM**, so the Docker engine needs at least that much free (we used 4 CPUs / 8 GB for the Docker Desktop WSL 2 VM).
- **GNU make.** On Windows, install it with `winget install ezwinports.make` (then open a new shell), or run everything from WSL.
- **Git** and about 200 MB of disk space (the dataset, plus about 37 MB of committed embeddings).
- **Python 3.12**, only if you need to re-create the embeddings (`make embed`). Everything that talks to PostgreSQL, including the dataset download, runs in a `bench` container (`python:3.12.10-slim-bookworm` with psycopg 3.3.9), so the host needs no PostgreSQL client library. We chose this because Windows Smart App Control blocks the libpq DLL that ships with `psycopg[binary]`.
- Internet access on the first run, to pull the Docker images and download the dataset from Hugging Face.

Pinned versions: PostgreSQL 18 + pgvector 0.8.7 (`pgvector/pgvector:0.8.7-pg18-trixie`); dataset `mteb/cqadupstack-android` at revision `e03f271e3f4a75f49787c838a62f671b35bc9004`; embedding model `BAAI/bge-small-en-v1.5` at revision `5c38ec7c405ec4b44b94cc5a9bb96e735b38267a`. Python packages are pinned in `requirements.txt` (host) and `docker/requirements-bench.txt` (container).

## Setup from a fresh clone

```sh
git clone https://github.com/tkob-team/seminar-c3-hybrid-search
cd seminar-c3-hybrid-search
make up         # start PostgreSQL + pgvector, wait until healthy
make download   # CQADupStack android -> data/raw/, checks counts (22,998 / 699 / 1,696) and data/SHA256SUMS
make prepare    # checks embedding sha256, creates the table, loads, builds HNSW + GIN, runs ANALYZE
make check      # optional: CTE vec returns 100 rows, and both plans use docs_embedding_hnsw
```

`make measure` runs `up` and `download` itself, and it loads the table if it is missing, so after cloning you can also call it directly.

The embeddings (`data/emb_corpus.npy`, `data/emb_queries.npy`) are committed together with their sha256 in `data/SHA256SUMS`, so you do not need to embed. If a checksum does not match, re-create them on the host:

```sh
make embed      # creates .venv with Python 3.12, installs requirements.txt, embeds on CPU (about 55 min on our machine)
```

A re-embed on another machine may give a different checksum (floating-point differences). If so, note it in your results.

## Run the measurement (`make measure`)

```sh
make measure
```

What it does (spec: `notes/S02-cach-do.md` sections 3–5):

1. Sets `hnsw.ef_search = 100` on the connection.
2. Warm-up: runs all 699 queries through A (`sql/vector_only.sql`) and B (`sql/hybrid.sql`) once, and discards the results.
3. Five measured runs. Odd runs go A→B, even runs go B→A. Each query is timed with `perf_counter()` around `execute()` + `fetchall()` at the client, so the time is SQL only. The query vector is pre-computed and not timed.
4. Computes recall@10 and nDCG@10 against the qrels. A result whose id equals the query id is removed first. It also counts per-query wins, losses and ties, and checks that the top-10 lists are identical in all 5 runs.
5. Computes p95 and p50 for each run and branch (nearest-rank), then reports the median (min–max) over the 5 runs, the difference B − A, and the ratio B / A.

A full run takes a few minutes on our machine. Other targets: `make down` stops the database, and `make clean-db` also deletes its volume.

## Output (results/)

| File | Content |
|---|---|
| `results/summary.csv` | One row per metric: recall@10 (%), nDCG@10, per-query B vs A counts, p95/p50 median, min and max (ms), each run's p95 and recall, the delta and the ratio |
| `results/raw.csv` | One row per (run, branch, query): `run, branch, query_id, ms, top10_ids` (5 runs × 2 branches × 699 queries) |
| `results/run_info.txt` | When the run finished, how long it took, PostgreSQL and pgvector versions, `hnsw.ef_search`, client versions, and whether top-10 was deterministic |
| `results/embed_timing.txt` | Time to embed 100 documents on the host CPU, with the machine and library versions |

The same summary table is printed to the terminal at the end of `make measure`.
