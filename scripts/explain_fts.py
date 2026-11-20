"""Evidence for "why it is slower": EXPLAIN (ANALYZE, BUFFERS) of the fts CTE of sql/hybrid.sql (android).

Two queries: 2461 (webcam, broad OR) and the query whose OR tsquery matches the fewest documents
among the queries with qrels (ties by id). Writes results/explain-fts.txt. Latency is not re-measured;
the times here are single EXPLAIN ANALYZE executions (with instrumentation overhead).
"""
import re

import psycopg

from common import DSN, RESULTS, SQL, SUBFORUM, load_qrels, load_queries

BROAD = "2461"
COUNT = """
SELECT count(*) FROM docs
WHERE tsv @@ to_tsquery('english', replace(plainto_tsquery('english', $1)::text, '&', '|'))"""


def main():
    hybrid = (SQL / "hybrid.sql").read_text(encoding="utf-8")
    q_cte = hybrid[hybrid.index("q AS ("):hybrid.index("fts AS (")].rstrip().rstrip(",")
    fts_body = hybrid[hybrid.index("fts AS (") + len("fts AS ("):hybrid.index("\n)\nSELECT id\nFROM vec FULL OUTER JOIN")]
    stmt = f"WITH {q_cte}\n{fts_body.strip()}".replace("$2", "$1")  # query text is $2 in hybrid.sql

    qrels = load_qrels()
    queries = [(i, t) for i, t in load_queries() if i in qrels]
    text = dict(queries)
    with psycopg.connect(DSN, autocommit=True, cursor_factory=psycopg.RawCursor) as conn:
        n_docs = conn.execute("SELECT count(*) FROM docs").fetchone()[0]
        counts = {i: conn.execute(COUNT, (t,), prepare=False).fetchone()[0] for i, t in queries}
        narrow = min(counts, key=lambda i: (counts[i], int(i)))
        out = [f"subforum: {SUBFORUM}; statement = CTE q + fts of sql/hybrid.sql:", "", stmt, ""]
        summary = []
        for label, qid in (("broad OR", BROAD), ("narrowest OR", narrow)):
            plan = [r[0] for r in conn.execute("EXPLAIN (ANALYZE, BUFFERS) " + stmt, (text[qid],), prepare=False)]
            joined = "\n".join(plan)
            scans = sorted(set(re.findall(r"(Seq Scan|Bitmap Index Scan|Bitmap Heap Scan|Index Scan)", joined)))
            exec_ms = re.search(r"Execution Time: ([\d.]+) ms", joined).group(1)
            head = (f"query {qid} ({label}): \"{text[qid]}\"\n"
                    f"documents matching OR tsquery: {counts[qid]} / {n_docs} = {100 * counts[qid] / n_docs:.1f} %\n"
                    f"scan types: {', '.join(scans)}; execution time: {exec_ms} ms")
            summary.append(head)
            out += ["=" * 80, head, "-" * 80, *plan, ""]
    text_out = "\n".join(out[:4] + ["SUMMARY", *summary, ""] + out[4:])
    (RESULTS / "explain-fts.txt").write_text(text_out, encoding="utf-8", newline="\n")
    print("\n\n".join(summary))


if __name__ == "__main__":
    main()
