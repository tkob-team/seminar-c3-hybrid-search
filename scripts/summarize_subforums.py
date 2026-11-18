"""S23: one row per measured subforum -> results/all-subforums.csv.

Inputs per subforum (android uses results/, others results/<s>/):
  summary.csv (A vs B-OR, main design), supplementary-and/summary.csv (A vs B-AND),
  diagnostics.txt (full-text-only recall@10); screening criteria from results/subforum-screening.csv.
p95 A is taken from the OR measurement (A is identical SQL in both).
"""
import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "results"
SUBFORUMS = ["android", "mathematica", "gaming"]


def summary(path):
    with open(path, encoding="utf-8") as f:
        return {r["metric"]: r for r in csv.DictReader(f)}


def counts(note):
    m = re.search(r"B>A (\d+); B<A (\d+); B=A (\d+)", note)
    return m.groups()


def main():
    with open(RES / "subforum-screening.csv", encoding="utf-8") as f:
        screen = {r["subforum"].split(" ")[0]: r for r in csv.DictReader(f)}
    rows = []
    for s in SUBFORUMS:
        d = RES if s == "android" else RES / s
        o, a = summary(d / "summary.csv"), summary(d / "supplementary-and" / "summary.csv")
        fts = re.search(r"full-text only \(OR, ts_rank\): ([\d.]+)", (d / "diagnostics.txt").read_text(encoding="utf-8"))
        wo, lo, to = counts(o["per-query recall B vs A"]["note"])
        wa, la, ta = counts(a["per-query recall B vs A"]["note"])
        assert o["recall@10"]["A_vector_only"] == a["recall@10"]["A_vector_only"]
        p95a = float(o["p95 median"]["A_vector_only"])
        p95o, p95n = float(o["p95 median"]["B_hybrid"]), float(a["p95 median"]["B_hybrid"])
        rows.append({
            "subforum": s,
            "queries": o["queries"]["A_vector_only"],
            "median_or_match_pct": screen[s]["median_or_match_pct"],
            "code_token_queries_pct": screen[s]["code_token_queries_pct"],
            "recall10_A_pct": o["recall@10"]["A_vector_only"],
            "recall10_B_or_pct": o["recall@10"]["B_hybrid"],
            "recall10_B_and_pct": a["recall@10"]["B_hybrid"],
            "recall10_fts_only_pct": fts.group(1),
            "delta_B_or_pp": o["recall@10"]["delta_B_minus_A"],
            "delta_B_and_pp": a["recall@10"]["delta_B_minus_A"],
            "B_or_win_loss_tie": f"{wo}/{lo}/{to}",
            "B_and_win_loss_tie": f"{wa}/{la}/{ta}",
            "p95_A_ms": f"{p95a:.2f}",
            "p95_B_or_ms": f"{p95o:.2f}",
            "p95_B_and_ms": f"{p95n:.2f}",
            "p95_ratio_B_or": f"{p95o / p95a:.2f}",
            "p95_ratio_B_and": f"{p95n / float(a['p95 median']['A_vector_only']):.2f}",
        })
    with open(RES / "all-subforums.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    print(open(RES / "all-subforums.csv", encoding="utf-8").read())


if __name__ == "__main__":
    main()
