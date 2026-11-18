-- Branch A: vector-only baseline. Same CTE vec as hybrid.sql, top-10 by rank, ties broken by id.
-- Source: notes/S04 section 3. $1 = query vector (vector(384)).
WITH vec AS (
  SELECT id, row_number() OVER (ORDER BY embedding <=> $1) AS r
  FROM docs ORDER BY embedding <=> $1 LIMIT 100
)
SELECT id
FROM vec
ORDER BY r, id
LIMIT 10;
