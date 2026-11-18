"""S12: measure A (vector-only) vs B (hybrid RRF). Spec: notes/S02 sections 3-5.

1 warm-up pass over all queries (A then B, discarded), then 5 runs with
alternating branch order (odd runs A->B, even runs B->A). Latency = perf_counter
around execute() + fetchall() at the client, SQL only.

Writes results/raw.csv, results/summary.csv, results/run_info.txt.
Options: --out DIR (default results/) and --sql-b FILE (default sql/hybrid.sql),
used for repeats and supplementary variants without overwriting the main results.
"""
import argparse
import csv
import math
import platform
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import psycopg
from pgvector.psycopg import register_vector

from common import (DSN, EF_SEARCH, EMB_QUERIES, RESULTS, SQL, SUBFORUM, ensure_database, load_corpus,
                    load_qrels, load_queries)

RUNS = 5
K = 10
BRANCHES = ("A", "B")  # A = vector-only, B = hybrid


def ensure_prepared(conn):
    """Load + index if the docs table is missing or incomplete (first run on a fresh clone)."""
    n_corpus = len(load_corpus())
    ok = conn.execute("SELECT to_regclass('docs') IS NOT NULL").fetchone()[0]
    if ok:
        n = conn.execute("SELECT count(*) FROM docs").fetchone()[0]
        idx = {r[0] for r in conn.execute("SELECT indexname FROM pg_indexes WHERE tablename = 'docs'")}
        ok = n == n_corpus and {"docs_embedding_hnsw", "docs_tsv_gin"} <= idx
    if not ok:
        print("docs table missing or incomplete: running prepare (load + index)")
        import prepare
        if prepare.main() != 0:
            sys.exit("prepare failed")


def nearest_rank(values, p):
    s = sorted(values)
    return s[math.ceil(p * len(s)) - 1]


def recall_at_k(top, rel):
    return len(set(top[:K]) & rel) / len(rel)


def ndcg_at_k(top, rel):
    dcg = sum(1.0 / math.log2(i + 2) for i, d in enumerate(top[:K]) if d in rel)
    idcg = sum(1.0 / math.log2(i + 2) for i in range(min(len(rel), K)))
    return dcg / idcg


def med_range(xs):
    return statistics.median(xs), min(xs), max(xs)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(RESULTS))
    ap.add_argument("--sql-b", default=str(SQL / "hybrid.sql"))
    args = ap.parse_args()
    out = Path(args.out)
    sql_b = Path(args.sql_b)
    t_start = time.perf_counter()
    queries = load_queries()
    qrels = load_qrels()
    eq = np.load(EMB_QUERIES)
    assert eq.shape[0] == len(queries)
    items = [(qid, text, eq[i]) for i, (qid, text) in enumerate(queries) if qid in qrels]
    sql = {"A": (SQL / "vector_only.sql").read_text(encoding="utf-8"),
           "B": sql_b.read_text(encoding="utf-8")}

    def params(branch, text, vec):
        return (vec,) if branch == "A" else (vec, text)

    raw = []  # (run, branch, qid, ms, top10)
    ensure_database()
    with psycopg.connect(DSN, autocommit=True, cursor_factory=psycopg.RawCursor) as conn:
        ensure_prepared(conn)
        register_vector(conn)
        conn.execute(f"SET hnsw.ef_search = {EF_SEARCH}")
        pg_version = conn.execute("SHOW server_version").fetchone()[0]
        pgvector_version = conn.execute("SELECT extversion FROM pg_extension WHERE extname = 'vector'").fetchone()[0]
        ef = conn.execute("SHOW hnsw.ef_search").fetchone()[0]

        def run_branch(branch, run):
            q = sql[branch]
            for qid, text, vec in items:
                t0 = time.perf_counter()
                cur = conn.execute(q, params(branch, text, vec), prepare=False)
                rows = cur.fetchall()
                ms = (time.perf_counter() - t0) * 1000.0
                if run:
                    raw.append((run, branch, qid, ms, [r[0] for r in rows]))

        print(f"warm-up: {len(items)} queries x 2 branches")
        run_branch("A", 0)
        run_branch("B", 0)
        for run in range(1, RUNS + 1):
            order = ("A", "B") if run % 2 == 1 else ("B", "A")
            for b in order:
                run_branch(b, run)
            print(f"run {run} done ({'->'.join(order)})")

    out.mkdir(parents=True, exist_ok=True)
    with open(out / "raw.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["run", "branch", "query_id", "ms", "top10_ids"])
        for run, b, qid, ms, top in raw:
            w.writerow([run, b, qid, f"{ms:.3f}", " ".join(top)])

    # --- quality: per query, excluding a result whose id equals the query id ---
    tops = {}  # (run, branch) -> {qid: top}
    for run, b, qid, ms, top in raw:
        tops.setdefault((run, b), {})[qid] = [d for d in top if d != qid]
    deterministic = all(tops[(r, b)] == tops[(1, b)] for b in BRANCHES for r in range(2, RUNS + 1))
    rec, ndcg = {}, {}
    for b in BRANCHES:
        rec[b] = {qid: recall_at_k(top, qrels[qid]) for qid, top in tops[(1, b)].items()}
        ndcg[b] = {qid: ndcg_at_k(top, qrels[qid]) for qid, top in tops[(1, b)].items()}
    per_run_recall = {(r, b): 100 * statistics.mean(recall_at_k(t, qrels[q]) for q, t in tops[(r, b)].items())
                      for r in range(1, RUNS + 1) for b in BRANCHES}
    qids = list(rec["A"])
    wins = sum(rec["B"][q] > rec["A"][q] for q in qids)
    losses = sum(rec["B"][q] < rec["A"][q] for q in qids)
    ties = len(qids) - wins - losses
    rescued = sum(rec["A"][q] == 0 and rec["B"][q] > 0 for q in qids)
    lost = sum(rec["B"][q] == 0 and rec["A"][q] > 0 for q in qids)
    recall = {b: 100 * statistics.mean(rec[b].values()) for b in BRANCHES}
    nd = {b: statistics.mean(ndcg[b].values()) for b in BRANCHES}

    # --- latency: p95 / p50 per run x branch (nearest-rank) ---
    ms_by = {}
    for run, b, qid, ms, top in raw:
        ms_by.setdefault((run, b), []).append(ms)
    p95 = {b: [nearest_rank(ms_by[(r, b)], 0.95) for r in range(1, RUNS + 1)] for b in BRANCHES}
    p50 = {b: [nearest_rank(ms_by[(r, b)], 0.50) for r in range(1, RUNS + 1)] for b in BRANCHES}
    p95m = {b: med_range(p95[b]) for b in BRANCHES}
    p50m = {b: med_range(p50[b]) for b in BRANCHES}

    rows = [
        ("queries", "count", len(qids), len(qids), "", "", "queries with qrels; each run"),
        ("recall@10", "%", f"{recall['A']:.2f}", f"{recall['B']:.2f}", f"{recall['B'] - recall['A']:+.2f}",
         f"{recall['B'] / recall['A']:.3f}", "delta in percentage points; identical in all 5 runs" if deterministic
         else "WARNING: differs between runs"),
        ("nDCG@10", "score", f"{nd['A']:.4f}", f"{nd['B']:.4f}", f"{nd['B'] - nd['A']:+.4f}",
         f"{nd['B'] / nd['A']:.3f}", "secondary"),
        ("per-query recall B vs A", "count", "", "", "", "",
         f"B>A {wins}; B<A {losses}; B=A {ties}; A=0 & B>0 {rescued}; B=0 & A>0 {lost}"),
        ("p95 median", "ms", f"{p95m['A'][0]:.2f}", f"{p95m['B'][0]:.2f}", f"{p95m['B'][0] - p95m['A'][0]:+.2f}",
         f"{p95m['B'][0] / p95m['A'][0]:.2f}", "median of 5 runs, nearest-rank p95"),
        ("p95 min", "ms", f"{p95m['A'][1]:.2f}", f"{p95m['B'][1]:.2f}", "", "", ""),
        ("p95 max", "ms", f"{p95m['A'][2]:.2f}", f"{p95m['B'][2]:.2f}", "", "", ""),
        ("p50 median", "ms", f"{p50m['A'][0]:.2f}", f"{p50m['B'][0]:.2f}", f"{p50m['B'][0] - p50m['A'][0]:+.2f}",
         f"{p50m['B'][0] / p50m['A'][0]:.2f}", "secondary"),
        ("p50 min", "ms", f"{p50m['A'][1]:.2f}", f"{p50m['B'][1]:.2f}", "", "", ""),
        ("p50 max", "ms", f"{p50m['A'][2]:.2f}", f"{p50m['B'][2]:.2f}", "", "", ""),
    ]
    for r in range(1, RUNS + 1):
        rows.append((f"p95 run {r}", "ms", f"{p95['A'][r - 1]:.2f}", f"{p95['B'][r - 1]:.2f}", "", "",
                     "order A->B" if r % 2 else "order B->A"))
    for r in range(1, RUNS + 1):
        rows.append((f"recall@10 run {r}", "%", f"{per_run_recall[(r, 'A')]:.2f}", f"{per_run_recall[(r, 'B')]:.2f}",
                     "", "", ""))
    with open(out / "summary.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["metric", "unit", "A_vector_only", "B_hybrid", "delta_B_minus_A", "ratio_B_over_A", "note"])
        w.writerows(rows)

    elapsed = time.perf_counter() - t_start
    (out / "run_info.txt").write_text(
        f"finished_utc: {datetime.now(timezone.utc).isoformat(timespec='seconds')}\n"
        f"subforum: {SUBFORUM}\n"
        f"measure_seconds: {elapsed:.0f}\n"
        f"postgresql: {pg_version}\npgvector: {pgvector_version}\nhnsw.ef_search: {ef}\n"
        f"client: python {platform.python_version()}, psycopg {psycopg.__version__}, {platform.platform()}\n"
        f"client_cpus_visible: {__import__('os').cpu_count()}\n"
        f"runs: {RUNS} (+1 warm-up), queries: {len(qids)}, branches: A=vector_only.sql B={sql_b.name}\n"
        f"deterministic_top10_across_runs: {deterministic}\n",
        encoding="utf-8", newline="\n")

    w = max(len(r[0]) for r in rows)
    print(f"\n{'metric':<{w}}  {'unit':<6} {'A':>10} {'B':>10} {'B-A':>9} {'B/A':>7}  note")
    for m, u, a, b, d, ra, note in rows:
        print(f"{m:<{w}}  {u:<6} {a!s:>10} {b!s:>10} {d!s:>9} {ra!s:>7}  {note}")
    print(f"\nrecall identical across 5 runs: {deterministic}; measure took {elapsed:.0f} s")
    return 0 if deterministic else 1


if __name__ == "__main__":
    sys.exit(main())
