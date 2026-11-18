"""S08: download a BEIR CQADupStack subforum (mteb/cqadupstack-<SUBFORUM>) at a pinned revision.

Default SUBFORUM=android: writes data/raw/ (git-ignored), checks the expected counts
(22,998 docs / 699 queries / 1,696 qrels lines) and data/SHA256SUMS.
Other subforums: data/raw/<s>/ and data/<s>/SHA256SUMS (see scripts/common.py).
If the checksum file already lists the raw files, the downloaded files must match it.
"""
import json
import shutil
import sys
from pathlib import Path

from huggingface_hub import hf_hub_download

from common import EXPECTED, RAW, RAW_REL, REVISIONS, ROOT, SUBFORUM, SUMS, read_sums, sha256, write_sum

FILES = ["corpus.jsonl", "queries.jsonl", "qrels/test.tsv"]


def count_jsonl(path: Path) -> int:
    with open(path, encoding="utf-8") as f:
        return sum(1 for line in f if line.strip())


def count_qrels(path: Path) -> int:
    with open(path, encoding="utf-8") as f:
        lines = [l for l in f if l.strip()]
    # first line is the header "query-id corpus-id score"
    return len(lines) - 1 if lines and lines[0].startswith("query-id") else len(lines)


def main() -> int:
    repo = f"mteb/cqadupstack-{SUBFORUM}"
    RAW.mkdir(parents=True, exist_ok=True)
    for name in FILES:
        src = hf_hub_download(repo, name, repo_type="dataset", revision=REVISIONS[SUBFORUM])
        dst = RAW / name
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
        print(f"downloaded {repo}@{REVISIONS[SUBFORUM][:7]} {name}")

    counts = {
        "corpus": count_jsonl(RAW / "corpus.jsonl"),
        "queries": count_jsonl(RAW / "queries.jsonl"),
        "qrels": count_qrels(RAW / "qrels" / "test.tsv"),
    }
    print("counts:", json.dumps(counts))
    expected = EXPECTED.get(SUBFORUM)
    if expected is None:
        print(f"note: no expected counts recorded for {SUBFORUM}")
    elif counts != expected:
        print(f"ERROR: counts differ from expected {expected}", file=sys.stderr)
        return 1

    actual = {f"{RAW_REL}/{n}": sha256(RAW / n) for n in FILES}
    known = read_sums()
    if all(k in known for k in actual):
        if any(known[k] != v for k, v in actual.items()):
            print(f"ERROR: checksums differ from {SUMS}", file=sys.stderr)
            return 1
        print(f"checksums match {SUMS.relative_to(ROOT).as_posix()}")
    else:
        SUMS.parent.mkdir(parents=True, exist_ok=True)
        for k, v in actual.items():
            write_sum(k, v)
        print(f"wrote raw checksums to {SUMS.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
