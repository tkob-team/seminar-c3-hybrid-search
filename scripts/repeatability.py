"""Collect p95/p50 medians (A, B) from results/summary.csv and results/repeat-*/summary.csv
into results/repeatability.csv (one row per `make measure` invocation)."""
import csv
import statistics

from common import RESULTS

dirs = [("1 (main)", RESULTS)] + [(f"{n}", RESULTS / f"repeat-{n}") for n in (2, 3, 4)]
rows = []
for label, d in dirs:
    with open(d / "summary.csv", encoding="utf-8") as f:
        s = {r["metric"]: r for r in csv.DictReader(f)}
    p95a, p95b = float(s["p95 median"]["A_vector_only"]), float(s["p95 median"]["B_hybrid"])
    p50a, p50b = float(s["p50 median"]["A_vector_only"]), float(s["p50 median"]["B_hybrid"])
    # delta and ratio as computed by measure.py from the unrounded medians
    rows.append([label, s["recall@10"]["A_vector_only"], s["recall@10"]["B_hybrid"],
                 f"{p95a:.2f}", f"{p95b:.2f}", s["p95 median"]["delta_B_minus_A"], s["p95 median"]["ratio_B_over_A"],
                 f"{p50a:.2f}", f"{p50b:.2f}", s["p50 median"]["delta_B_minus_A"], s["p50 median"]["ratio_B_over_A"]])
cols = list(zip(*rows))
summary = [f"median of {len(rows)}", cols[1][0], cols[2][0]]
for i, c in enumerate(cols[3:]):
    v = statistics.median(float(x) for x in c)
    summary.append(f"{v:+.2f}" if i in (2, 6) else f"{v:.2f}")
with open(RESULTS / "repeatability.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f, lineterminator="\n")
    w.writerow(["make_measure_run", "recall10_A_pct", "recall10_B_pct",
                "p95_median_A_ms", "p95_median_B_ms", "p95_delta_ms", "p95_ratio",
                "p50_median_A_ms", "p50_median_B_ms", "p50_delta_ms", "p50_ratio"])
    w.writerows(rows + [summary])
print(open(RESULTS / "repeatability.csv", encoding="utf-8").read())
