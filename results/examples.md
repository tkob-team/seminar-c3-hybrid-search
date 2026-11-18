# Examples: queries where hybrid (B) differs from vector-only (A)

Source: run 1 of `results/raw.csv`; ranks from `sql/hybrid.sql` CTEs at `hnsw.ef_search = 100`.
`vec rank` is the position in the HNSW top-100 (`>100` = not in it). `fts rank` is the position by
`ts_rank` among all documents matching the OR tsquery (only ranks 1-100 enter RRF).

## Hybrid rescued (A recall@10 = 0, B > 0)

### Query 1799: "Is there a way to see the top apps across all categories?"

recall@10: A 0.00, B 1.00. OR tsquery matches 12516 of 22998 documents (54 %).

| relevant doc | title | vec rank | fts rank |
|---|---|---|---|
| 27268 | Where can I find official statistics of most downloaded android app in play market? | 49 | 1 |

### Query 2581: "App that reads images of QR codes?"

recall@10: A 0.00, B 1.00. OR tsquery matches 9939 of 22998 documents (43 %).

| relevant doc | title | vec rank | fts rank |
|---|---|---|---|
| 64255 | How can I scan barcodes on webpages in Firefox for Android? | 22 | 2 |

### Query 2906: "Knowing which applications to stop"

recall@10: A 0.00, B 1.00. OR tsquery matches 6971 of 22998 documents (30 %).

| relevant doc | title | vec rank | fts rank |
|---|---|---|---|
| 4491 | What running applications and services are safe to turn off? | 21 | 21 |

## Hybrid lost (A recall@10 > 0, B = 0)

### Query 1156: "How can I customize the list of services that pops up when I choose to "share" something in an app?"

recall@10: A 1.00, B 0.00. OR tsquery matches 11149 of 22998 documents (48 %).

| relevant doc | title | vec rank | fts rank |
|---|---|---|---|
| 8112 | Is there a way to edit the Share menu? | 5 | 1815 |

### Query 2461: "How to use an android phone as a wireless webcam?"

recall@10: A 1.00, B 0.00. OR tsquery matches 18641 of 22998 documents (81 %).

| relevant doc | title | vec rank | fts rank |
|---|---|---|---|
| 1159 | Can I turn my Android device into a webcam? | 1 | 7754 |

### Query 4064: "How to put a Call contact using Skype shortcut widget on the home screen?"

recall@10: A 1.00, B 0.00. OR tsquery matches 13651 of 22998 documents (59 %).

| relevant doc | title | vec rank | fts rank |
|---|---|---|---|
| 2171 | Quick Dial Shortcut with Skype | 1 | 1584 |
