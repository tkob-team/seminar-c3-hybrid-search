"""Evidence for "why it is slower": EXPLAIN (ANALYZE, BUFFERS) of the fts CTE of sql/hybrid.sql (android).

Three queries: 2461 (webcam, broad OR), the query whose OR tsquery matches the fewest documents among
the queries with qrels (ties by id), and the one with the fewest matches that still has >= MIN_MATCHES.
Writes results/explain-fts.txt. `--append-min10` adds only the third case to the existing file and keeps
the first two plans as recorded. Latency is not re-measured; the times here are single EXPLAIN ANALYZE
executions (with instrumentation overhead).
"""
import re
import sys

import psycopg

from common import DSN, RESULTS, SQL, SUBFORUM, load_qrels, load_queries

BROAD = "2461"
MIN_MATCHES = 10
NOTE_1102 = ('note: in query 1102 the parser reads "donut/froyo" as one token, so the OR tsquery '
             'matches 0 documents (degenerate case).')
RULE = "=" * 80
COUNT = """
SELECT count(*) FROM docs
WHERE tsv @@ to_tsquery('english', replace(plainto_tsquery('english', $1)::text, '&', '|'))"""


def main():
    append = "--append-min10" in sys.argv
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
        narrow10 = min((i for i in counts if counts[i] >= MIN_MATCHES), key=lambda i: (counts[i], int(i)))
        cases = [("broad OR", BROAD), ("narrowest OR", narrow),
                 (f"narrowest OR with >= {MIN_MATCHES} matches", narrow10)]
        if append:
            cases = cases[2:]
        summary, plans = [], []
        for label, qid in cases:
            plan = [r[0] for r in conn.execute("EXPLAIN (ANALYZE, BUFFERS) " + stmt, (text[qid],), prepare=False)]
            joined = "\n".join(plan)
            scans = sorted(set(re.findall(r"(Seq Scan|Bitmap Index Scan|Bitmap Heap Scan|Index Scan)", joined)))
            exec_ms = re.search(r"Execution Time: ([\d.]+) ms", joined).group(1)
            head = (f"query {qid} ({label}): \"{text[qid]}\"\n"
                    f"documents matching OR tsquery: {counts[qid]} / {n_docs} = {100 * counts[qid] / n_docs:.1f} %\n"
                    f"scan types: {', '.join(scans)}; execution time: {exec_ms} ms")
            summary.append(head)
            plans += [RULE, head, "-" * 80, *plan, ""]

    path = RESULTS / "explain-fts.txt"
    if append:
        old = path.read_text(encoding="utf-8")
        cut = old.index("\n" + RULE)
        top, rest = old[:cut].rstrip("\n"), old[cut + 1:].rstrip("\n")
        out = "\n".join([top, *summary, NOTE_1102, "", rest, "", *plans])
    else:
        out = "\n".join([f"subforum: {SUBFORUM}; statement = CTE q + fts of sql/hybrid.sql:", "", stmt, "",
                         "SUMMARY", *summary, NOTE_1102, "", *plans])
    path.write_text(out, encoding="utf-8", newline="\n")
    print("\n\n".join(summary))


if __name__ == "__main__":
    main()
