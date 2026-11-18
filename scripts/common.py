"""Shared paths, connection settings and data loaders for the C3 scripts.

Subforum is chosen with the SUBFORUM environment variable (default: android).
android (the main result) keeps its original layout:
    data/raw/, data/emb_*.npy, data/SHA256SUMS, results/, database c3
any other subforum <s> gets its own:
    data/raw/<s>/ (git-ignored), data/<s>/emb_*.npy, data/<s>/SHA256SUMS, results/<s>/, database c3_<s>
The table is always `docs` (one database per subforum), so sql/*.sql are shared unchanged.
"""
import hashlib
import json
import os
from pathlib import Path

# pinned dataset revisions: mteb/cqadupstack-<subforum>
REVISIONS = {
    "android": "e03f271e3f4a75f49787c838a62f671b35bc9004",
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
# expected counts (corpus lines / queries lines / qrels lines without header)
EXPECTED = {
    "android": {"corpus": 22998, "queries": 699, "qrels": 1696},
    "mathematica": {"corpus": 16705, "queries": 804, "qrels": 1358},
    "gaming": {"corpus": 45301, "queries": 1595, "qrels": 2263},
}

SUBFORUM = os.environ.get("SUBFORUM", "android").strip() or "android"
if SUBFORUM not in REVISIONS:
    raise SystemExit(f"unknown SUBFORUM {SUBFORUM!r}; choose one of {', '.join(REVISIONS)}")
IS_MAIN = SUBFORUM == "android"

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
SQL = ROOT / "sql"
SF_DATA = DATA if IS_MAIN else DATA / SUBFORUM          # embeddings + SHA256SUMS
RAW = DATA / "raw" if IS_MAIN else DATA / "raw" / SUBFORUM
RAW_REL = "raw" if IS_MAIN else f"raw/{SUBFORUM}"       # prefix used inside SHA256SUMS (relative to data/)
RESULTS = ROOT / "results" if IS_MAIN else ROOT / "results" / SUBFORUM
SUMS = SF_DATA / "SHA256SUMS"
DBNAME = "c3" if IS_MAIN else f"c3_{SUBFORUM}"

EMB_CORPUS = SF_DATA / "emb_corpus.npy"
EMB_QUERIES = SF_DATA / "emb_queries.npy"

MODEL_NAME = "BAAI/bge-small-en-v1.5"
MODEL_REVISION = "5c38ec7c405ec4b44b94cc5a9bb96e735b38267a"  # model repo commit used for all emb_*.npy
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "
EF_SEARCH = 100  # notes/S03 section 3: must be >= N = 100


def dsn(dbname: str = DBNAME) -> str:
    return (
        f"host={os.environ.get('PGHOST', 'localhost')} "
        f"port={os.environ.get('PGPORT', os.environ.get('PGPORT_HOST', '5432'))} "
        f"dbname={dbname} "
        f"user={os.environ.get('PGUSER', 'c3')} "
        f"password={os.environ.get('PGPASSWORD', 'c3')}"
    )


DSN = dsn()


def ensure_database() -> None:
    """Create the subforum's database (c3_<s>) if it does not exist yet."""
    if IS_MAIN:
        return
    import psycopg
    with psycopg.connect(dsn("c3"), autocommit=True) as conn:
        if not conn.execute("SELECT 1 FROM pg_database WHERE datname = %s", (DBNAME,)).fetchone():
            conn.execute(f'CREATE DATABASE "{DBNAME}"')
            print(f"created database {DBNAME}")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_sums() -> dict:
    """Return {relative_path: sha256} from data/SHA256SUMS."""
    out = {}
    if SUMS.exists():
        for line in SUMS.read_text(encoding="utf-8").splitlines():
            parts = line.strip().split("  ", 1)
            if len(parts) == 2:
                out[parts[1]] = parts[0]
    return out


def write_sum(rel: str, digest: str) -> None:
    sums = read_sums()
    sums[rel] = digest
    SUMS.write_text("".join(f"{v}  {k}\n" for k, v in sums.items()), encoding="utf-8", newline="\n")


def load_corpus():
    """List of (id, title, body) in file order."""
    with open(RAW / "corpus.jsonl", encoding="utf-8") as f:
        rows = [json.loads(l) for l in f if l.strip()]
    return [(r["_id"], r.get("title", "") or "", r.get("text", "") or "") for r in rows]


def load_queries():
    """List of (id, text) in file order."""
    with open(RAW / "queries.jsonl", encoding="utf-8") as f:
        rows = [json.loads(l) for l in f if l.strip()]
    return [(r["_id"], r["text"]) for r in rows]


def load_qrels() -> dict:
    """{query_id: set(corpus_id)} for score > 0."""
    rel = {}
    with open(RAW / "qrels" / "test.tsv", encoding="utf-8") as f:
        next(f)  # header
        for line in f:
            if not line.strip():
                continue
            qid, did, score = line.rstrip("\n").split("\t")
            if int(score) > 0:
                rel.setdefault(qid, set()).add(did)
    return rel
