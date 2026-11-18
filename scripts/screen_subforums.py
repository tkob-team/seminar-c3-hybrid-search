"""S23: screen the other 11 CQADupStack subforums without embedding (plan: notes/S23-subforum-khac.md).

For each subforum (pinned revision of mteb/cqadupstack-<name>): download into data/raw/<name>/,
load text into a temporary table with the same tsv ('english', title || ' ' || body) + GIN,
then compute
  - primary:   median OR-tsquery match rate (% of corpus) over queries with qrels
  - secondary: % of queries with a code-like token (_, camelCase, (), number with >= 3 digits)
  - counts (documents / queries with qrels / qrels lines) and estimated embed minutes
    (= documents x 15.73 s / 100 / 60, our machine; results/embed_timing.txt).
android (main dataset, already loaded in table docs) is added as a reference row.
Writes results/subforum-screening.csv sorted by match rate ascending, and data/SHA256SUMS.screening.
No embedding, no measurement.
"""
import csv
import json
import re
import shutil
import statistics
import sys
import time

import psycopg
from huggingface_hub import hf_hub_download

from common import DATA, DSN, RAW, RESULTS, load_qrels, load_queries, sha256

REVISIONS = {
    "english": "fa6afc4ce926dafd42b7b7c0a19ae40c4632d895",
    "gaming": "1c9769860b1d666aae049c6ba60d76ecb244253e",
    "gis": "080d0534a7c9fa7b856e77b752c042a6ddbd9714",
    "mathematica": "fc1af0b6c82dfd3a2aabfb4d9606ba7226268f05",
    "physics": "9c2faaa08d173bccf24e1cc3fc1e39bf3caea961",
    "programmers": "339629ee116f204b54b1cfd50b9084199a6d415c",
    "stats": "6b474f6f6dca1fe17f197f04500b537417692250",
    "tex": "2b6f1e278efc77f54ab343b200f5fc7fcd2fc934",
    "unix": "3197b09145642430d9db451fcdc1e1987e54d74c",
    "webmasters": "c691d4af16c19a79df7ee93bfbd12cc186a5bc92",
    "wordpress": "6117bc4829afb46d0af6ad6106d1f942e1048281",
}
ANDROID_REVISION = "e03f271e3f4a75f49787c838a62f671b35bc9004"
FILES = ["corpus.jsonl", "queries.jsonl", "qrels/test.tsv"]
EMBED_S_PER_100 = 15.73

OR_TSQ = "to_tsquery('english', replace(plainto_tsquery('english', %s)::text, '&', '|'))"
CODE_TOKEN = re.compile(r"_|[a-z][A-Z]|\(\)|\d{3,}")


def has_code_token(text: str) -> bool:
    return any(CODE_TOKEN.search(tok) for tok in text.split())


def download(name: str):
    out = RAW / name
    for f in FILES:
        src = hf_hub_download(f"mteb/cqadupstack-{name}", f, repo_type="dataset", revision=REVISIONS[name])
        dst = out / f
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
    return out


def read_subforum(d):
    with open(d / "corpus.jsonl", encoding="utf-8") as f:
        corpus = [json.loads(l) for l in f if l.strip()]
    with open(d / "queries.jsonl", encoding="utf-8") as f:
        queries = [(r["_id"], r["text"]) for r in (json.loads(l) for l in f if l.strip())]
    qrels, n_lines = {}, 0
    with open(d / "qrels" / "test.tsv", encoding="utf-8") as f:
        next(f)
        for line in f:
            if line.strip():
                n_lines += 1
                qid, did, score = line.rstrip("\n").split("\t")
                if int(score) > 0:
                    qrels.setdefault(qid, set()).add(did)
    return corpus, queries, qrels, n_lines


def rates(conn, table, queries, n_docs):
    sql = f"SELECT count(*) FROM {table} WHERE tsv @@ {OR_TSQ}"
    return [100.0 * conn.execute(sql, (text,)).fetchone()[0] / n_docs for _, text in queries]


def row(name, revision, n_docs, queries, n_lines, match, nul_docs=0):
    code = 100.0 * sum(has_code_token(t) for _, t in queries) / len(queries)
    return {
        "subforum": name,
        "median_or_match_pct": f"{statistics.median(match):.1f}",
        "p25_or_match_pct": f"{statistics.quantiles(match, n=4)[0]:.1f}",
        "p75_or_match_pct": f"{statistics.quantiles(match, n=4)[2]:.1f}",
        "code_token_queries_pct": f"{code:.1f}",
        "documents": n_docs,
        "queries_with_qrels": len(queries),
        "qrels_lines": n_lines,
        "est_embed_minutes": f"{n_docs * EMBED_S_PER_100 / 100 / 60:.0f}",
        "docs_with_nul_stripped": nul_docs,
        "revision": revision,
    }


def main() -> int:
    rows, sums = [], []
    with psycopg.connect(DSN, autocommit=True) as conn:
        # reference: android (table docs, loaded by prepare)
        n_docs = conn.execute("SELECT count(*) FROM docs").fetchone()[0]
        qrels = load_qrels()
        qs = [(q, t) for q, t in load_queries() if q in qrels]
        with open(RAW / "qrels" / "test.tsv", encoding="utf-8") as f:
            n_lines = sum(1 for l in f if l.strip()) - 1
        rows.append(row("android (main, reference)", ANDROID_REVISION, n_docs, qs, n_lines,
                        rates(conn, "docs", qs, n_docs)))
        print(f"android: median {rows[-1]['median_or_match_pct']} %")

        for name in REVISIONS:
            t0 = time.perf_counter()
            d = download(name)
            sums += [f"{sha256(d / f)}  raw/{name}/{f}" for f in FILES]
            corpus, queries, qrels, n_lines = read_subforum(d)
            qs = [(q, t) for q, t in queries if q in qrels]
            conn.execute("DROP TABLE IF EXISTS screen_docs")
            conn.execute("""
                CREATE TEMP TABLE screen_docs (
                  id text PRIMARY KEY, title text, body text,
                  tsv tsvector GENERATED ALWAYS AS
                      (to_tsvector('english', coalesce(title,'') || ' ' || coalesce(body,''))) STORED)""")
            nul_docs = 0  # PostgreSQL text cannot hold NUL bytes: strip them (counted in the CSV)
            with conn.cursor() as cur:
                with cur.copy("COPY screen_docs (id, title, body) FROM STDIN") as cp:
                    for r in corpus:
                        title, body = r.get("title", "") or "", r.get("text", "") or ""
                        if "\x00" in title or "\x00" in body:
                            nul_docs += 1
                            title, body = title.replace("\x00", ""), body.replace("\x00", "")
                        cp.write_row((r["_id"], title, body))
            conn.execute("CREATE INDEX ON screen_docs USING gin (tsv)")
            conn.execute("ANALYZE screen_docs")
            rows.append(row(name, REVISIONS[name], len(corpus), qs, n_lines,
                            rates(conn, "screen_docs", qs, len(corpus)), nul_docs))
            conn.execute("DROP TABLE screen_docs")
            print(f"{name}: median {rows[-1]['median_or_match_pct']} %, code {rows[-1]['code_token_queries_pct']} %, "
                  f"{len(corpus)} docs ({time.perf_counter() - t0:.0f} s)")

    rows.sort(key=lambda r: float(r["median_or_match_pct"]))
    RESULTS.mkdir(exist_ok=True)
    with open(RESULTS / "subforum-screening.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    (DATA / "SHA256SUMS.screening").write_text("\n".join(sums) + "\n", encoding="utf-8", newline="\n")
    print(open(RESULTS / "subforum-screening.csv", encoding="utf-8").read())
    return 0


if __name__ == "__main__":
    sys.exit(main())
