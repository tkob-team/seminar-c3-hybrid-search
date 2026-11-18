-- SUPPLEMENTARY branch B': same as hybrid.sql but the full-text side uses an AND tsquery
-- (plainto_tsquery as-is) instead of OR. Not part of the main design (notes/S05); see results/supplementary-and/.
-- $1 = query vector (vector(384)), $2 = query text.
WITH vec AS (
  SELECT id, row_number() OVER (ORDER BY embedding <=> $1) AS r
  FROM docs ORDER BY embedding <=> $1 LIMIT 100
),
q AS (
  SELECT plainto_tsquery('english', $2) AS tq
),
fts AS (
  SELECT d.id, row_number() OVER (ORDER BY ts_rank(d.tsv, q.tq) DESC, d.id) AS r
  FROM docs d, q WHERE d.tsv @@ q.tq
  ORDER BY ts_rank(d.tsv, q.tq) DESC, d.id LIMIT 100
)
SELECT id
FROM vec FULL OUTER JOIN fts USING (id)
ORDER BY coalesce(1.0/(60 + vec.r), 0) + coalesce(1.0/(60 + fts.r), 0) DESC, id
LIMIT 10;
