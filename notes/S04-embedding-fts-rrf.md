# S04 — Embedding local, full-text PostgreSQL và RRF

> Task S04 · Người phụ trách: Hoàng · Cập nhật: 18/11/2026 (theo kết quả họp 15/11)
> Đầu vào cho S09 (prepare) và S10 (truy vấn hai nhánh).

## 1. Model embedding: `BAAI/bge-small-en-v1.5`

| Thuộc tính | Giá trị (model card, đọc 18/11/2026) |
|---|---|
| Số chiều | 384 |
| Độ dài tối đa | 512 token (phần dài hơn bị cắt) |
| License | MIT |
| Chỉ dẫn cho truy vấn | `"Represent this sentence for searching relevant passages: "`, dùng cho truy vấn ngắn; tài liệu không cần |

**Quyết định cách embed (giữ cố định):**
- **Tài liệu:** `title + " " + body`, không thêm tiền tố.
- **Truy vấn:** thêm tiền tố chỉ dẫn ở trên. Truy vấn CQADupStack là tiêu đề câu hỏi ngắn, đúng trường hợp model card khuyên dùng.
- `normalize_embeddings=True`, để khoảng cách cosine `<=>` có ý nghĩa đúng.
- Chạy bằng `sentence-transformers` trên CPU, pin phiên bản thư viện trong `requirements.txt`.
- **Tính một lần**, lưu `data/emb_corpus.npy` và `data/emb_queries.npy` kèm `sha256`. Người chạy lại chỉ cần kiểm checksum. Nếu tự embed lại thì phải ra cùng checksum, nếu không phải ghi chú lại.
- Thời gian embed 100 tài liệu: đo trên máy nhóm rồi ghi vào REPORT.

**Rủi ro (đưa vào Limits):** model card chỉ nói model được huấn luyện bằng contrastive learning trên dữ liệu cặp quy mô lớn, **không công bố bộ dữ liệu cụ thể**. Vì vậy không loại trừ được khả năng model đã gặp dữ liệu StackExchange. Nếu đúng vậy, baseline vector sẽ mạnh hơn bình thường trên CQADupStack.

## 2. Full-text search của PostgreSQL

- Cột `tsv` tạo sẵn (`GENERATED ... STORED`) với cấu hình `'english'`, cộng index GIN:
  ```sql
  CREATE INDEX docs_tsv_gin ON docs USING gin (tsv);
  ```
- **Kiểu truy vấn: OR (đã chốt).** `plainto_tsquery` mặc định nối các từ bằng AND. Ta đổi sang OR:
  ```sql
  to_tsquery('english', replace(plainto_tsquery('english', $q)::text, '&', '|'))
  ```
- Xếp hạng bằng `ts_rank(tsv, query)`, không dùng trọng số tiêu đề. **Không phải BM25** (đưa vào Limits).
- Lưu ý độ trễ: `ts_rank` phải chấm điểm **mọi** tài liệu khớp. Dùng OR thì số tài liệu khớp nhiều hơn, nên nhánh hybrid chậm hơn. Cái giá này nằm trong phần đo, không phải lỗi.
- Truy vấn chỉ gồm stopword sẽ cho tsquery rỗng. Khi đó nhánh full-text không trả gì, và hybrid tự rơi về kết quả của vector.

## 3. Trộn RRF và câu SQL hai nhánh

Tham số: **N = 100** ứng viên mỗi nhánh, **k = 60**, lấy top 10.

```sql
-- $1 = vector truy vấn, $2 = text truy vấn
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
```

**Baseline (vector-only)** dùng đúng CTE `vec` ở trên và lấy `ORDER BY r LIMIT 10`. Nhờ vậy hai nhánh chỉ khác phần full-text và RRF.

`id` ở cuối mệnh đề `ORDER BY` dùng để phá hoà điểm, giúp kết quả tất định qua các lượt.

## 4. Nguồn

- Model card `BAAI/bge-small-en-v1.5`: https://huggingface.co/BAAI/bge-small-en-v1.5 (đọc 18/11/2026)
- PostgreSQL docs, Full Text Search: https://www.postgresql.org/docs/current/textsearch.html
- Mẫu hybrid + RRF trong PostgreSQL (Supabase): https://supabase.com/docs/guides/ai/hybrid-search
