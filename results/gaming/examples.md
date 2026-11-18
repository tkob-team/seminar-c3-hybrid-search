# Examples: queries where hybrid (B) differs from vector-only (A)

Source: run 1 of `results/raw.csv`; ranks from `sql/hybrid.sql` CTEs at `hnsw.ef_search = 100`.
`vec rank` is the position in the HNSW top-100 (`>100` = not in it). `fts rank` is the position by
`ts_rank` among all documents matching the OR tsquery (only ranks 1-100 enter RRF).

## Hybrid rescued (A recall@10 = 0, B > 0)

### Query 18903: "What is kiting?"

recall@10: A 0.00, B 1.00. OR tsquery matches 44 of 45301 documents (0 %).

| relevant doc | title | vec rank | fts rank |
|---|---|---|---|
| 164498 | What does "kite" mean in LoL? | >100 | 1 |

### Query 28920: "What's the difference between the difficulty options?"

recall@10: A 0.00, B 1.00. OR tsquery matches 6808 of 45301 documents (15 %).

| relevant doc | title | vec rank | fts rank |
|---|---|---|---|
| 30288 | What are the differences between difficulty levels in Deus Ex: Human Revolution? | 13 | 1 |

### Query 33226: "What are the advantages and disadvantages of being in human form?"

recall@10: A 0.00, B 1.00. OR tsquery matches 1290 of 45301 documents (3 %).

| relevant doc | title | vec rank | fts rank |
|---|---|---|---|
| 159889 | What does humanity do? | 15 | 21 |

## Hybrid lost (A recall@10 > 0, B = 0)

### Query 236: "Refurbishing "loose" Xbox360 Controller"

recall@10: A 1.00, B 0.00. OR tsquery matches 1507 of 45301 documents (3 %).

| relevant doc | title | vec rank | fts rank |
|---|---|---|---|
| 105807 | How do I fix Xbox 360 controller drift? | 1 | 644 |

### Query 6406: "How do I sell back a completed building in StarCraft 2?"

recall@10: A 1.00, B 0.00. OR tsquery matches 13757 of 45301 documents (30 %).

| relevant doc | title | vec rank | fts rank |
|---|---|---|---|
| 5381 | How do I remove a building in StarCraft 2? | 1 | 144 |

### Query 7786: "How do you cope with nausea in FPS?"

recall@10: A 1.00, B 0.00. OR tsquery matches 279 of 45301 documents (1 %).

| relevant doc | title | vec rank | fts rank |
|---|---|---|---|
| 902 | How can I prevent Gaming Sickness? | 1 | 273 |
| 36103 | Why do I get sick when I'm lost (in a game)? | 2 | 229 |
