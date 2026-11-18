-- Branch B: hybrid = HNSW vector top-100 + full-text (OR tsquery, ts_rank) top-100, fused with RRF (k = 60).
-- Source: notes/S04 section 3. $1 = query vector (vector(384)), $2 = query text.
WITH vec AS (
  SELECT id, row_number() OVER (ORDER BY embedding <=> $1) AS r
  FROM docs ORDER BY embedding <=> $1 LIMIT 100
),
q AS (
  SELECT to_tsquery('english', replace(plainto_tsquery('english', $2)::text, '&', '|')) AS tq
),
fts AS (
  SELECT d.id, row_number() OVER (ORDER BY ts_rank(d.tsv, q.tq) DESC) AS r
  FROM docs d, q WHERE d.tsv @@ q.tq
  ORDER BY ts_rank(d.tsv, q.tq) DESC LIMIT 100
)
SELECT id
FROM vec FULL OUTER JOIN fts USING (id)
ORDER BY coalesce(1.0/(60 + vec.r), 0) + coalesce(1.0/(60 + fts.r), 0) DESC, id
LIMIT 10;
