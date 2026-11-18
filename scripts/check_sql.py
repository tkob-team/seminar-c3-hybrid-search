"""S10 check: CTE vec returns exactly 100 rows at hnsw.ef_search = 100, and the
plan of both branches uses the HNSW index (Index Scan using docs_embedding_hnsw)."""
import re
import sys

import numpy as np
import psycopg
from pgvector.psycopg import register_vector

from common import DSN, EF_SEARCH, EMB_QUERIES, SQL, load_queries


def vec_cte(sql: str) -> str:
    start = sql.index("WITH vec AS (")
    depth, i = 0, sql.index("(", start)
    while True:
        depth += {"(": 1, ")": -1}.get(sql[i], 0)
        if depth == 0:
            return sql[start:i + 1]
        i += 1


def main() -> int:
    queries = load_queries()
    eq = np.load(EMB_QUERIES)
    hybrid = (SQL / "hybrid.sql").read_text(encoding="utf-8")
    vonly = (SQL / "vector_only.sql").read_text(encoding="utf-8")
    assert vec_cte(hybrid) == vec_cte(vonly), "CTE vec differs between the two files"
    ok = True
    with psycopg.connect(DSN, autocommit=True, cursor_factory=psycopg.RawCursor) as conn:
        register_vector(conn)
        conn.execute(f"SET hnsw.ef_search = {EF_SEARCH}")
        counts = [conn.execute(vec_cte(hybrid) + " SELECT count(*) FROM vec", (eq[i],)).fetchone()[0]
                  for i in range(len(queries))]
        print(f"CTE vec rows: min={min(counts)} max={max(counts)} over {len(counts)} queries")
        ok &= min(counts) == max(counts) == 100
        for name, sql, params in [("vector_only", vonly, (eq[0],)), ("hybrid", hybrid, (eq[0], queries[0][1]))]:
            plan = "\n".join(r[0] for r in conn.execute("EXPLAIN " + sql, params).fetchall())
            has = "Index Scan using docs_embedding_hnsw" in plan
            print(f"{name}: 'Index Scan using docs_embedding_hnsw' in plan = {has}")
            print(re.sub(r"'\[[^\]]*\]'::vector", "'[...]'::vector", plan))
            ok &= has
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
