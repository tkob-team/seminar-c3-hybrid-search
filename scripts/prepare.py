"""S09: embed corpus and queries, load PostgreSQL, build HNSW + GIN indexes.

Embedding (notes/S04 section 1): BAAI/bge-small-en-v1.5, normalized, documents
as "title body" without prefix, queries with the instruction prefix. Skipped
when data/emb_*.npy exist and match data/SHA256SUMS.
Schema and indexes: notes/S03 sections 2-3.

  python scripts/prepare.py --embed-only   # host .venv (needs torch)
  python scripts/prepare.py                # bench container: check embeddings, load, index
"""
import platform
import sys
import time

import numpy as np

from common import (DSN, EMB_CORPUS, EMB_QUERIES, MODEL_NAME, MODEL_REVISION, QUERY_PREFIX, RESULTS, ROOT, SUBFORUM,
                    SUMS, ensure_database,
                    load_corpus, load_queries, read_sums, sha256, write_sum)

SCHEMA = """
DROP TABLE IF EXISTS docs;
CREATE EXTENSION IF NOT EXISTS vector;
CREATE TABLE docs (
  id        text PRIMARY KEY,
  title     text,
  body      text,
  embedding vector(384),
  tsv       tsvector GENERATED ALWAYS AS
            (to_tsvector('english', coalesce(title,'') || ' ' || coalesce(body,''))) STORED
);
"""

INDEXES = [
    "SET maintenance_work_mem = '1GB'",
    "CREATE INDEX docs_embedding_hnsw ON docs USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64)",
    "CREATE INDEX docs_tsv_gin ON docs USING gin (tsv)",
    "ANALYZE docs",
]

WIN_CPU_KEY = "HARDWARE\\DESCRIPTION\\System\\CentralProcessor\\0"


def emb_ok(path, rel) -> bool:
    expected = read_sums().get(rel)
    return path.exists() and expected is not None and sha256(path) == expected


def cpu_name() -> str:
    try:
        import winreg
        k = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, WIN_CPU_KEY)
        return winreg.QueryValueEx(k, "ProcessorNameString")[0].strip()
    except Exception:
        return platform.processor()


def embed(corpus, queries):
    from sentence_transformers import SentenceTransformer
    import sentence_transformers
    import torch

    model = SentenceTransformer(MODEL_NAME, revision=MODEL_REVISION, device="cpu")
    docs = [f"{t} {b}" for _, t, b in corpus]

    # timing: 100 documents, after one warm-up call
    model.encode(docs[:8], normalize_embeddings=True)
    t0 = time.perf_counter()
    model.encode(docs[:100], normalize_embeddings=True, batch_size=32)
    secs = time.perf_counter() - t0
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "embed_timing.txt").write_text(
        f"model: {MODEL_NAME}\n"
        f"documents: 100 (first 100 of corpus.jsonl, 'title body', batch_size=32, normalized)\n"
        f"seconds: {secs:.2f}\n"
        f"device: cpu, torch threads: {torch.get_num_threads()}\n"
        f"processor: {cpu_name()}\n"
        f"os: {platform.platform()}\n"
        f"python: {platform.python_version()}, torch {torch.__version__}, "
        f"sentence-transformers {sentence_transformers.__version__}\n",
        encoding="utf-8", newline="\n")
    print(f"embed 100 docs: {secs:.2f} s")

    t0 = time.perf_counter()
    ec = model.encode(docs, normalize_embeddings=True, batch_size=32, show_progress_bar=True).astype(np.float32)
    eq = model.encode([QUERY_PREFIX + t for _, t in queries], normalize_embeddings=True,
                      batch_size=32).astype(np.float32)
    full_secs = time.perf_counter() - t0
    print(f"embedded {len(docs)} docs + {len(queries)} queries in {full_secs:.0f} s")
    with open(RESULTS / "embed_timing.txt", "a", encoding="utf-8", newline="\n") as f:
        f.write(f"subforum: {SUBFORUM}\nfull embed: {len(docs)} documents + {len(queries)} queries "
                f"in {full_secs:.0f} s ({full_secs / 60:.1f} min)\n")
    np.save(EMB_CORPUS, ec)
    np.save(EMB_QUERIES, eq)
    write_sum("emb_corpus.npy", sha256(EMB_CORPUS))
    write_sum("emb_queries.npy", sha256(EMB_QUERIES))


def vec_text(v) -> str:
    return "[" + ",".join(f"{x:.8g}" for x in v) + "]"


def load(corpus, ec):
    import psycopg

    ensure_database()
    with psycopg.connect(DSN, autocommit=True) as conn:
        conn.execute(SCHEMA)
        t0 = time.perf_counter()
        with conn.cursor() as cur:
            with cur.copy("COPY docs (id, title, body, embedding) FROM STDIN") as cp:
                for (did, title, body), v in zip(corpus, ec):
                    cp.write_row((did, title, body, vec_text(v)))
        print(f"loaded {len(corpus)} rows in {time.perf_counter() - t0:.0f} s")
        for stmt in INDEXES:
            t0 = time.perf_counter()
            conn.execute(stmt)
            print(f"{stmt[:60]}... {time.perf_counter() - t0:.1f} s")
        n = conn.execute("SELECT count(*) FROM docs").fetchone()[0]
        print(f"docs rows: {n}")
        return n


def main() -> int:
    embed_only = "--embed-only" in sys.argv
    corpus, queries = load_corpus(), load_queries()
    if emb_ok(EMB_CORPUS, "emb_corpus.npy") and emb_ok(EMB_QUERIES, "emb_queries.npy"):
        print(f"embeddings present and sha256 matches {SUMS.relative_to(ROOT).as_posix()}: skipping embed")
    else:
        if read_sums().get("emb_corpus.npy") and EMB_CORPUS.exists():
            print(f"WARNING: embedding file does not match {SUMS.relative_to(ROOT).as_posix()}; re-embedding",
                  file=sys.stderr)
        try:
            embed(corpus, queries)
        except ImportError as e:
            print(f"ERROR: embeddings missing or changed and {e}; run `make embed` on the host first",
                  file=sys.stderr)
            return 1
    if embed_only:
        return 0
    ec = np.load(EMB_CORPUS)
    assert ec.shape == (len(corpus), 384), ec.shape
    return 0 if load(corpus, ec) == len(corpus) else 1


if __name__ == "__main__":
    sys.exit(main())
