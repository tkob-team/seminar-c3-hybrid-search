"""S16: storage cost of the full-text branch -> results/storage.csv (MB = 2^20 bytes).

Per subforum database: docs table without indexes (pg_table_size, includes TOAST), the tsv column
(sum(pg_column_size(tsv))), the HNSW and GIN indexes (pg_relation_size).
android only: DROP and re-CREATE the GIN index from its catalog definition (pg_indexes.indexdef),
with the same maintenance_work_mem as prepare.py, and time it. Latency is not measured; HNSW is untouched.
"""
import csv
import time

import psycopg

from common import ROOT, dsn

SUBFORUMS = {"android": "c3", "mathematica": "c3_mathematica", "gaming": "c3_gaming"}
MB = 2 ** 20
SIZES = """
SELECT count(*),
       pg_table_size('docs'),
       sum(pg_column_size(tsv)),
       pg_relation_size('docs_embedding_hnsw'),
       pg_relation_size('docs_tsv_gin')
FROM docs"""


def main():
    rows = []
    for s, db in SUBFORUMS.items():
        with psycopg.connect(dsn(db), autocommit=True) as conn:
            n, table, tsv, hnsw, gin = conn.execute(SIZES).fetchone()
            row = {"subforum": s, "docs_rows": n, "table_mb": f"{table / MB:.1f}", "tsv_column_mb": f"{tsv / MB:.1f}",
                   "hnsw_index_mb": f"{hnsw / MB:.1f}", "gin_index_mb": f"{gin / MB:.1f}",
                   "gin_rebuild_s": "", "gin_index_mb_after_rebuild": ""}
            if s == "android":
                indexdef = conn.execute(
                    "SELECT indexdef FROM pg_indexes WHERE tablename = 'docs' AND indexname = 'docs_tsv_gin'"
                ).fetchone()[0]
                print(f"rebuilding: {indexdef}")
                conn.execute("SET maintenance_work_mem = '1GB'")
                conn.execute("DROP INDEX docs_tsv_gin")
                t0 = time.perf_counter()
                conn.execute(indexdef)
                secs = time.perf_counter() - t0
                after = conn.execute("SELECT pg_relation_size('docs_tsv_gin')").fetchone()[0]
                row["gin_rebuild_s"] = f"{secs:.2f}"
                row["gin_index_mb_after_rebuild"] = f"{after / MB:.1f}"
            rows.append(row)
            print(row)
    with open(ROOT / "results" / "storage.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    main()
