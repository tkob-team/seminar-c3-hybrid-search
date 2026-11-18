"""S08: download BEIR CQADupStack android (mteb/cqadupstack-android) at a pinned revision.

Writes the raw files to data/raw/ (git-ignored), checks the expected counts
(22,998 docs / 699 queries / 1,696 qrels lines) and writes data/SHA256SUMS.
If data/SHA256SUMS already exists, the downloaded files must match it.
"""
import hashlib
import json
import shutil
import sys
from pathlib import Path

from huggingface_hub import hf_hub_download

REPO_ID = "mteb/cqadupstack-android"
REVISION = "e03f271e3f4a75f49787c838a62f671b35bc9004"  # pinned commit (2025-05-04)
FILES = ["corpus.jsonl", "queries.jsonl", "qrels/test.tsv"]
EXPECTED = {"corpus": 22998, "queries": 699, "qrels": 1696}

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
SUMS = ROOT / "data" / "SHA256SUMS"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def count_jsonl(path: Path) -> int:
    with open(path, encoding="utf-8") as f:
        return sum(1 for line in f if line.strip())


def count_qrels(path: Path) -> int:
    with open(path, encoding="utf-8") as f:
        lines = [l for l in f if l.strip()]
    # first line is the header "query-id corpus-id score"
    return len(lines) - 1 if lines and lines[0].startswith("query-id") else len(lines)


def main() -> int:
    RAW.mkdir(parents=True, exist_ok=True)
    for name in FILES:
        src = hf_hub_download(REPO_ID, name, repo_type="dataset", revision=REVISION)
        dst = RAW / name
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
        print(f"downloaded {name}")

    counts = {
        "corpus": count_jsonl(RAW / "corpus.jsonl"),
        "queries": count_jsonl(RAW / "queries.jsonl"),
        "qrels": count_qrels(RAW / "qrels" / "test.tsv"),
    }
    print("counts:", json.dumps(counts))
    if counts != EXPECTED:
        print(f"ERROR: counts differ from expected {EXPECTED}", file=sys.stderr)
        return 1

    lines = [f"{sha256(RAW / n)}  raw/{n}" for n in FILES]
    if SUMS.exists():
        expected = [l for l in SUMS.read_text(encoding="utf-8").splitlines() if l.startswith(tuple("0123456789abcdef")) and "  raw/" in l]
        if sorted(expected) != sorted(lines):
            print("ERROR: checksums differ from data/SHA256SUMS", file=sys.stderr)
            return 1
        print("checksums match data/SHA256SUMS")
    else:
        SUMS.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
        print("wrote data/SHA256SUMS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
