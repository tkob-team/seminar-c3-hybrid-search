# seminar-c3-hybrid-search

CSC13114 seminar, topic C3: hybrid search (pgvector HNSW + PostgreSQL full-text, fused with RRF) vs vector-only search, measured by recall@10 (%) and p95 latency (ms).

Report: [REPORT.md](REPORT.md). Slides: [slides.pdf](slides.pdf). Talk (slides, recording link): [TALK.md](TALK.md).

## Requirements

- **Docker** with Compose v2 (`docker compose`). The database container is limited to **2 CPUs and 4 GB RAM**, so the Docker engine needs at least that much free (we used 4 CPUs / 8 GB for the Docker Desktop WSL 2 VM). Start Docker Desktop (`docker desktop start`) if the daemon is not running; otherwise `make` fails with `Could not retrieve status. Is Docker Desktop running?`.
- **GNU make.** On Windows, install it with `winget install ezwinports.make` (then open a new shell), or run everything from WSL.
- **Git** and about 400 MB of disk space (the datasets, plus about 136 MB of committed embeddings for three subforums; see [Other subforums](#other-subforums)).
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

By default `make measure` writes to `results/` and **overwrites the committed main results** (`results/raw.csv`, `summary.csv`, `run_info.txt`). To keep them, write somewhere else with `OUT`:

```sh
make measure OUT=results/my-run   # any directory inside the repository (the bench container sees only the repo)
```

What it does (spec: `notes/S02-cach-do.md` sections 3–5):

1. Sets `hnsw.ef_search = 100` on the connection.
2. Warm-up: runs all 699 queries through A (`sql/vector_only.sql`) and B (`sql/hybrid.sql`) once, and discards the results.
3. Five measured runs. Odd runs go A→B, even runs go B→A. Each query is timed with `perf_counter()` around `execute()` + `fetchall()` at the client, so the time is SQL only. The query vector is pre-computed and not timed.
4. Computes recall@10 and nDCG@10 against the qrels. A result whose id equals the query id is removed first. It also counts per-query wins, losses and ties, and checks that the top-10 lists are identical in all 5 runs.
5. Computes p95 and p50 for each run and branch (nearest-rank), then reports the median (min–max) over the 5 runs, the difference B − A, and the ratio B / A.

To look at one question, `make demo Q="How to use an android phone as a wireless webcam?"` prints the top-10 of A and B (★ = relevant by qrels when Q is a dataset query) and the ranks of the duplicate in the vector and full-text lists; the host `.venv` embeds Q, the `bench` container runs the SQL.

A full run takes a few minutes on our machine. Other targets: `make down` stops the database, and `make clean-db` also deletes its volume.

## Output (results/)

| File | Content |
|---|---|
| `results/summary.csv` | One row per metric: recall@10 (%), nDCG@10, per-query B vs A counts, p95/p50 median, min and max (ms), each run's p95 and recall, the delta and the ratio |
| `results/raw.csv` | One row per (run, branch, query): `run, branch, query_id, ms, top10_ids` (5 runs × 2 branches × 699 queries) |
| `results/run_info.txt` | When the run finished, how long it took, PostgreSQL and pgvector versions, `hnsw.ef_search`, client versions, and whether top-10 was deterministic |
| `results/embed_timing.txt` | Time to embed 100 documents on the host CPU, with the machine and library versions |

The same summary table is printed to the terminal at the end of `make measure`.

## Other subforums

Every target takes a `SUBFORUM` variable (default `android`, the main result). The design (SQL, index parameters, `ef_search`, RRF, measurement) is identical; only the dataset changes. Either form works:

```sh
SUBFORUM=mathematica make prepare
SUBFORUM=mathematica make measure
make measure SUBFORUM=gaming
make measure SUBFORUM=gaming OUT=results/gaming/supplementary-and SQL_B=sql/hybrid_and.sql   # AND variant
make diagnose SUBFORUM=gaming                                                                # full-text-only recall
```

For a subforum other than android, files go to `data/raw/<subforum>/` (download, git-ignored), `data/<subforum>/` (embeddings and `SHA256SUMS`), `results/<subforum>/`, and the database `c3_<subforum>`. The table is always `docs`, so the SQL files are shared. Pinned dataset revisions and expected counts are in `scripts/common.py`.

Measured subforums (OR = main design, AND = supplementary `sql/hybrid_and.sql`):

| Subforum | Queries | Results |
|---|---|---|
| android | 699 | `results/summary.csv`, `results/supplementary-and/summary.csv`, `results/diagnostics.txt` |
| mathematica | 804 | `results/mathematica/summary.csv`, `results/mathematica/supplementary-and/summary.csv`, `results/mathematica/diagnostics.txt` |
| gaming | 1,595 | `results/gaming/summary.csv`, `results/gaming/supplementary-and/summary.csv`, `results/gaming/diagnostics.txt` |

`results/all-subforums.csv` has one row per subforum (recall@10 of A, B-OR, B-AND and full-text only; per-query win/loss/tie; p95 and ratios). Re-build it with `python scripts/summarize_subforums.py`.

Note: `data/gaming/emb_corpus.npy` is 66 MB. That is below GitHub's 100 MB file limit (GitHub warns above 50 MB), so it is committed as a normal file without Git LFS, but it makes the clone slower.
