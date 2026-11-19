"""S17 demo: run one free-text question through A (sql/vector_only.sql) and B (sql/hybrid.sql).

Two steps, because embedding needs torch (host .venv) and the DB client runs in the bench container:
  python scripts/demo.py --embed     # host: embed $Q (model + query prefix of notes/S04) -> data/raw[/<s>]/demo_query.json
  python scripts/demo.py             # bench: print both top-10 tables, ★ = relevant by qrels
`make demo Q="..."` runs both. If Q equals a dataset query (case-insensitive), its qrels are used,
and the ranks of the relevant documents in the vec top-100 and the full fts ranking are printed.
"""
import json
import os
import sys

from common import (DSN, EF_SEARCH, MODEL_NAME, MODEL_REVISION, QUERY_PREFIX, RAW, SQL, SUBFORUM, load_corpus,
                    load_qrels, load_queries)

STATE = RAW / "demo_query.json"
WIDTH = 70


def embed():
    from sentence_transformers import SentenceTransformer

    q = os.environ.get("Q", "").strip()
    if not q:
        print('ERROR: set Q, e.g. make demo Q="How to use an android phone as a wireless webcam?"', file=sys.stderr)
        return 1
    model = SentenceTransformer(MODEL_NAME, revision=MODEL_REVISION, device="cpu")
    vec = model.encode(QUERY_PREFIX + q, normalize_embeddings=True).tolist()
    STATE.write_text(json.dumps({"subforum": SUBFORUM, "q": q, "vec": vec}), encoding="utf-8")
    return 0


def run():
    import numpy as np
    import psycopg
    from pgvector.psycopg import register_vector

    state = json.loads(STATE.read_text(encoding="utf-8"))
    q, vec = state["q"], np.array(state["vec"], dtype=np.float32)
    titles = {d: t for d, t, _ in load_corpus()}
    qid = next((i for i, t in load_queries() if t.strip().lower() == q.lower()), None)
    rel = load_qrels().get(qid, set()) if qid else set()

    hybrid = (SQL / "hybrid.sql").read_text(encoding="utf-8")
    ctes = hybrid[hybrid.index("WITH vec AS ("):hybrid.index("\nSELECT id\nFROM vec FULL OUTER JOIN")]
    fts_full = """
WITH q AS (SELECT to_tsquery('english', replace(plainto_tsquery('english', $1)::text, '&', '|')) AS tq)
SELECT d.id, row_number() OVER (ORDER BY ts_rank(d.tsv, q.tq) DESC, d.id) AS r
FROM docs d, q WHERE d.tsv @@ q.tq"""

    with psycopg.connect(DSN, autocommit=True, cursor_factory=psycopg.RawCursor) as conn:
        register_vector(conn)
        conn.execute(f"SET hnsw.ef_search = {EF_SEARCH}")
        ex = lambda sql, params: conn.execute(sql, params, prepare=False).fetchall()  # noqa: E731
        top = {
            "A vector-only (sql/vector_only.sql)": [r[0] for r in ex((SQL / "vector_only.sql").read_text(), (vec,))],
            "B hybrid OR + RRF (sql/hybrid.sql)": [r[0] for r in ex(hybrid, (vec, q))],
        }
        vec_rank = dict(ex(ctes + "\nSELECT id, r FROM vec", (vec, q)))
        fts_rank = dict(ex(fts_full, (q,)))

    print(f'subforum: {SUBFORUM}   question: "{q}"')
    print(f"dataset query id: {qid} (relevant: {', '.join(sorted(rel, key=int))})" if qid
          else "not a dataset query: no qrels, no ★")
    for name, ids in top.items():
        print(f"\n{name}\n rank  id      title")
        for i, d in enumerate([d for d in ids if d != qid][:10], 1):
            t = titles.get(d, "")
            t = t if len(t) <= WIDTH else t[:WIDTH - 1] + "…"
            print(f" {i:>3} {'★' if d in rel else ' '} {d:<7} {t}")
    if rel:
        print(f"\nrelevant document ranks (vec = HNSW top-100, '>100' if absent; fts = among {len(fts_rank)} OR matches):")
        for d in sorted(rel, key=int):
            print(f"  {d}: vec {vec_rank.get(d, '>100')}, fts {fts_rank.get(d, 'not matched')}  \"{titles.get(d, '')}\"")
        site = f"https://{SUBFORUM}.stackexchange.com/questions"
        print(f"\nquestion: {site}/{qid}")
        for d in sorted(rel, key=int):
            print(f"duplicate: {site}/{d}")
    return 0


if __name__ == "__main__":
    sys.exit(embed() if "--embed" in sys.argv else run())
