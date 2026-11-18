# Examples: queries where hybrid (B) differs from vector-only (A)

Source: run 1 of `results/raw.csv`; ranks from `sql/hybrid.sql` CTEs at `hnsw.ef_search = 100`.
`vec rank` is the position in the HNSW top-100 (`>100` = not in it). `fts rank` is the position by
`ts_rank` among all documents matching the OR tsquery (only ranks 1-100 enter RRF).

## Hybrid rescued (A recall@10 = 0, B > 0)

### Query 2214: "Point Renderings Slightly Off in Mathematica"

recall@10: A 0.00, B 1.00. OR tsquery matches 8953 of 16705 documents (54 %).

| relevant doc | title | vec rank | fts rank |
|---|---|---|---|
| 2173 | ErrorListPlot marker missaligned with error bar | >100 | 1 |

### Query 9035: "How Can I use Solve/Reduce Output"

recall@10: A 0.00, B 1.00. OR tsquery matches 9555 of 16705 documents (57 %).

| relevant doc | title | vec rank | fts rank |
|---|---|---|---|
| 9077 | How Can I Use Conditional with Rational Domain Restrictions | >100 | 1 |

### Query 9483: "How to put terms in lexicographic order?"

recall@10: A 0.00, B 1.00. OR tsquery matches 2421 of 16705 documents (14 %).

| relevant doc | title | vec rank | fts rank |
|---|---|---|---|
| 10438 | Equation of the plane passing through the three points | 13 | 3 |

## Hybrid lost (A recall@10 > 0, B = 0)

### Query 938: "How to make a drop-shadow for Graphics3D objects"

recall@10: A 1.00, B 0.00. OR tsquery matches 3832 of 16705 documents (23 %).

| relevant doc | title | vec rank | fts rank |
|---|---|---|---|
| 39981 | How to get shadow of a 3d object | 2 | 81 |

### Query 2729: "Ordering problem"

recall@10: A 1.00, B 0.00. OR tsquery matches 4294 of 16705 documents (26 %).

| relevant doc | title | vec rank | fts rank |
|---|---|---|---|
| 39219 | Problem with Sort - unexpected order with Sqrt | 7 | 144 |

### Query 3897: "Plotting Error Bars on a Log Scale"

recall@10: A 1.00, B 0.00. OR tsquery matches 5565 of 16705 documents (33 %).

| relevant doc | title | vec rank | fts rank |
|---|---|---|---|
| 55634 | Making a Logplot with errorbars | 4 | 73 |
