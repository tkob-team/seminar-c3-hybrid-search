"""Shared paths, connection settings and data loaders for the C3 scripts."""
import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
RAW = DATA / "raw"
RESULTS = ROOT / "results"
SQL = ROOT / "sql"
SUMS = DATA / "SHA256SUMS"

EMB_CORPUS = DATA / "emb_corpus.npy"
EMB_QUERIES = DATA / "emb_queries.npy"

MODEL_NAME = "BAAI/bge-small-en-v1.5"
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "
EF_SEARCH = 100  # notes/S03 section 3: must be >= N = 100

DSN = (
    f"host={os.environ.get('PGHOST', 'localhost')} "
    f"port={os.environ.get('PGPORT', os.environ.get('PGPORT_HOST', '5432'))} "
    f"dbname={os.environ.get('PGDATABASE', 'c3')} "
    f"user={os.environ.get('PGUSER', 'c3')} "
    f"password={os.environ.get('PGPASSWORD', 'c3')}"
)


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
