Repository: https://github.com/tkob-team/seminar-c3-hybrid-search

> Note: this report is at most 3 pages.

# Report — Hybrid search vs vector-only (C3)

## Question

The question this seminar answers.

## Setup (versions, machine, data, load)

Software versions, machine specs, dataset, and query load used.

## Baseline and change

Baseline (vector-only) and the change under test (hybrid with RRF).

## Held fixed

Subforum android · file embedding (sha256) và model `bge-small-en-v1.5` · PostgreSQL 18 + pgvector 0.8.7 · `m = 16`, `ef_construction = 64`, `ef_search = 100`, iterative scan tắt · N = 100, k = 60 · tsquery OR, `ts_rank`, cấu hình `english` · 2 CPU, 4 GB RAM · warm-up 1 lượt, 5 lượt đo, xen kẽ A/B · p95 nearest-rank · latency chỉ tính thời gian SQL đo ở client.

## Results (median + spread, units)

Recall@10 (%) and p95 latency (ms), reported as median with spread.

## Recommendation (incl. when not to use)

What we recommend, and when hybrid search is not worth it.

## Limits

Threats to validity and what this measurement does not cover.

## Sources (link + date read)

References with links and the date each was read.
