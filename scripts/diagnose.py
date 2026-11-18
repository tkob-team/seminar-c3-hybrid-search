"""S12 diagnostics: why hybrid loses on android.

- recall@10 of full-text only (the fts CTE of sql/hybrid.sql, top-10 by ts_rank, ties by id)
- % of queries containing the token "android", and % of the corpus matching 'android'
- results/examples.md: 3 queries hybrid rescued (A recall 0, B > 0) and 3 it lost
  (B recall 0, A > 0), with query text, relevant titles, and ranks in vec / fts.
Reads per-query top-10 from results/raw.csv (run 1). Writes results/diagnostics.txt.
"""
import csv
import re
import statistics

import numpy as np
import psycopg
from pgvector.psycopg import register_vector

from common import DSN, EF_SEARCH, EMB_QUERIES, RESULTS, SQL, SUBFORUM, load_corpus, load_qrels, load_queries

K = 10
N_EXAMPLES = 3


def recall(top, rel):
    return len(set(top[:K]) & rel) / len(rel)


def main():
    queries = load_queries()
    qtext = dict(queries)
    qrels = load_qrels()
    titles = {d: t for d, t, _ in load_corpus()}
    eq = np.load(EMB_QUERIES)
    qvec = {qid: eq[i] for i, (qid, _) in enumerate(queries)}

    hybrid = (SQL / "hybrid.sql").read_text(encoding="utf-8")
    ctes = hybrid[hybrid.index("WITH vec AS ("):hybrid.index("\nSELECT id\nFROM vec FULL OUTER JOIN")]
    fts_only = ctes + "\nSELECT id FROM fts ORDER BY r, id LIMIT 10"
    vec_ranks = ctes + "\nSELECT id, r FROM vec"
    fts_full = """
WITH q AS (SELECT to_tsquery('english', replace(plainto_tsquery('english', $1)::text, '&', '|')) AS tq)
SELECT d.id, row_number() OVER (ORDER BY ts_rank(d.tsv, q.tq) DESC, d.id) AS r, count(*) OVER () AS n
FROM docs d, q WHERE d.tsv @@ q.tq"""

    # per-query top-10 of A and B from the main run
    tops = {"A": {}, "B": {}}
    with open(RESULTS / "raw.csv", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["run"] == "1":
                tops[row["branch"]][row["query_id"]] = [d for d in row["top10_ids"].split() if d != row["query_id"]]
    qids = [q for q, _ in queries if q in qrels]
    ra = {q: recall(tops["A"][q], qrels[q]) for q in qids}
    rb = {q: recall(tops["B"][q], qrels[q]) for q in qids}

    with psycopg.connect(DSN, autocommit=True, cursor_factory=psycopg.RawCursor) as conn:
        register_vector(conn)
        conn.execute(f"SET hnsw.ef_search = {EF_SEARCH}")
        n_docs = conn.execute("SELECT count(*) FROM docs").fetchone()[0]
        n_android = conn.execute("SELECT count(*) FROM docs WHERE tsv @@ plainto_tsquery('english', $1)",
                                 (SUBFORUM,)).fetchone()[0]
        rf = {}
        for q in qids:
            top = [r[0] for r in conn.execute(fts_only, (qvec[q], qtext[q]), prepare=False).fetchall()]
            rf[q] = recall([d for d in top if d != q], qrels[q])

        def ranks(q):
            v = dict(conn.execute(vec_ranks, (qvec[q], qtext[q]), prepare=False).fetchall())
            rows = conn.execute(fts_full, (qtext[q],), prepare=False).fetchall()
            f_ = {d: r for d, r, _ in rows}
            n = rows[0][2] if rows else 0
            return v, f_, n

        rescued = sorted((q for q in qids if ra[q] == 0 and rb[q] > 0), key=lambda q: (-rb[q], int(q)))[:N_EXAMPLES]
        lost = sorted((q for q in qids if rb[q] == 0 and ra[q] > 0), key=lambda q: (-ra[q], int(q)))[:N_EXAMPLES]
        examples = {"rescued": [(q, *ranks(q)) for q in rescued], "lost": [(q, *ranks(q)) for q in lost]}

    android_q = sum(bool(re.search(rf"\b{re.escape(SUBFORUM)}\b", qtext[q], re.I)) for q in qids)
    fts_recall = 100 * statistics.mean(rf.values())
    lines = [
        f"queries: {len(qids)}",
        f"recall@10 A vector-only: {100 * statistics.mean(ra.values()):.2f} %",
        f"recall@10 B hybrid (OR): {100 * statistics.mean(rb.values()):.2f} %",
        f"recall@10 full-text only (OR, ts_rank): {fts_recall:.2f} %",
        f"queries containing token '{SUBFORUM}': {android_q} / {len(qids)} = {100 * android_q / len(qids):.1f} %",
        f"corpus documents matching '{SUBFORUM}': {n_android} / {n_docs} = {100 * n_android / n_docs:.1f} %",
    ]
    (RESULTS / "diagnostics.txt").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(lines))

    def fmt(rank, limit=None):
        if rank is None:
            return "not matched" if limit is None else f">{limit}"
        return str(rank)

    md = ["# Examples: queries where hybrid (B) differs from vector-only (A)", "",
          "Source: run 1 of `results/raw.csv`; ranks from `sql/hybrid.sql` CTEs at `hnsw.ef_search = 100`.",
          "`vec rank` is the position in the HNSW top-100 (`>100` = not in it). `fts rank` is the position by",
          "`ts_rank` among all documents matching the OR tsquery (only ranks 1-100 enter RRF).", ""]
    for kind, title in (("rescued", "Hybrid rescued (A recall@10 = 0, B > 0)"),
                        ("lost", "Hybrid lost (A recall@10 > 0, B = 0)")):
        md += [f"## {title}", ""]
        for q, v, f_, n in examples[kind]:
            md += [f"### Query {q}: \"{qtext[q]}\"", "",
                   f"recall@10: A {ra[q]:.2f}, B {rb[q]:.2f}. OR tsquery matches {n} of {n_docs} documents "
                   f"({100 * n / n_docs:.0f} %).", "",
                   "| relevant doc | title | vec rank | fts rank |", "|---|---|---|---|"]
            for d in sorted(qrels[q], key=int):
                t = titles.get(d, "").replace("|", r"\|")
                md.append(f"| {d} | {t} | {fmt(v.get(d), 100)} | {fmt(f_.get(d))} |")
            md.append("")
    (RESULTS / "examples.md").write_text("\n".join(md), encoding="utf-8", newline="\n")
    print("wrote results/examples.md")


if __name__ == "__main__":
    main()
