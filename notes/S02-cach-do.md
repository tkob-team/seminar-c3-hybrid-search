# S02 — Phương pháp đo (recall@10, p95) và dataset

> Task S02 · Người phụ trách: Hiệp · Cập nhật: 15/11/2026
> Mục đích: đặc tả cách đo để S05 chốt thiết kế và S12 (`make measure`) cài đặt theo. REPORT trích từ file này.

## 1. Câu hỏi

> In PostgreSQL with pgvector, how much does hybrid search (HNSW vector search fused with built-in full-text search via reciprocal rank fusion) raise recall@10 over vector-only search on a public labeled retrieval dataset, and how much does it add to p95 query latency (ms)?

| | A — vector-only (baseline) | B — hybrid |
|---|---|---|
| Vector search (HNSW, N ứng viên) | có | có, cùng truy vấn với A |
| Full-text (tsvector + GIN, `ts_rank`) | không | có, N ứng viên |
| Trộn | không (lấy top-10 của vector) | RRF, k cố định |
| Đầu ra | top-10 | top-10 |

Hai nhánh chỉ khác phần full-text và RRF.

## 2. Dataset

CQADupStack trong BEIR. Mỗi subforum gồm 3 phần:
- `corpus`: câu hỏi cũ, tức tài liệu cần tìm.
- `queries`: câu hỏi mới, tức truy vấn.
- `qrels`: các cặp `query-id corpus-id score`. Một truy vấn có thể có nhiều tài liệu đúng.

| Subforum | Corpus | Queries | Qrels (test) |
|---|---|---|---|
| **android** (đề xuất) | 22,998 | 699 | 1,696 |
| programmers (dự phòng) | 32,176 | 876 | 1,675 |
| webmasters | 17,405 | 506 | 1,395 |
| wordpress | 48,605 | 541 | — |

**Đề xuất chọn android**, vì ba lý do:
- 699 truy vấn, nên p95 dựa trên khoảng 35 điểm ở phần đuôi.
- Corpus vừa sức để embed bằng model local.
- Nội dung có tên thiết bị, phiên bản, thông báo lỗi, nên hợp với giả thuyết rằng full-text bù được chỗ hụt của vector.

## 3. Recall@10

```
recall@10(q) = |rel(q) ∩ top10(q)| / |rel(q)|
recall@10    = trung bình recall@10(q) trên mọi q có trong qrels
```

- `rel(q)`: tập corpus-id có score > 0 trong qrels.
- **Loại tài liệu trùng ID với truy vấn** khỏi `top10(q)` trước khi tính. Cần đối chiếu lại cách BEIR `EvaluateRetrieval` xử lý.
- Đây là recall theo **nhãn qrels**, khác với recall của ANN (HNSW so với tìm chính xác).
- **Báo theo cặp:**
  - Δ = recall_B − recall_A (điểm phần trăm).
  - Số truy vấn B > A, B < A, B = A.
  - Số truy vấn A hụt hoàn toàn (recall = 0) mà B bắt được ít nhất một đáp án.
- **Số phụ, không đổi câu hỏi:** nDCG@10.
- **Recall phải giống nhau ở cả 5 lượt.** Kết quả là tất định, nên nếu khác nhau thì script có lỗi.

## 4. Độ trễ: p95, trung vị, khoảng dao động

- **Phạm vi đo:** chỉ đo thời gian SQL ở client, `perf_counter()` bao quanh `execute()` và `fetchall()`.
- **Không đo:** việc embed truy vấn (đã tính trước, lưu file), việc mở kết nối, việc tính metric.
- **p95 của một lượt:** nearest-rank, lấy giá trị ở vị trí `ceil(0.95 × n)` sau khi sắp tăng dần. Với n = 699 là vị trí 665.
- **Qua 5 lượt:** báo **trung vị (min–max)** của 5 giá trị p95 cho mỗi nhánh.
- **Kết quả chính:**
  - ΔP95 = median p95_B − median p95_A (ms).
  - Tỉ lệ = median p95_B / median p95_A.
- **Số phụ:** p50 của mỗi nhánh.

## 5. Quy trình `make measure` (đầu vào cho S12)

```
1. Bật container (giới hạn CPU/RAM theo docker-compose), chờ sẵn sàng.
2. SET hnsw.ef_search = EF  (cho mọi kết nối; EF ≥ N)
3. Warm-up: chạy toàn bộ truy vấn qua A và B một lượt, bỏ kết quả.
4. for run in 1..5:
       thứ tự nhánh: run lẻ A→B, run chẵn B→A
       for q in queries:
           t0 = perf_counter(); execute; fetchall; t1 = perf_counter()
           ghi results/raw.csv: run, branch, query_id, ms, top10_ids
5. Tính recall@10 (+ nDCG@10) từ top10_ids và qrels; kiểm 5 lượt giống nhau.
6. Tính p95, p50 mỗi run × branch → in trung vị (min–max), Δ, tỉ lệ.
   Ghi results/summary.csv (và in ra màn hình).
```

## 6. Giữ cố định (đưa vào mục Held fixed của REPORT)

Subforum · model embedding và file embedding (checksum) · phiên bản PostgreSQL và pgvector (pin) · `m`, `ef_construction`, `ef_search` · N · RRF k · kiểu tsquery · giới hạn CPU/RAM · số lượt (5) · cách tính phân vị.

## 7. Quyết định cần chốt ở S05

| Quyết định | Đề xuất | Ảnh hưởng |
|---|---|---|
| Subforum | android | Kích thước, số truy vấn, độ hợp với giả thuyết |
| N ứng viên mỗi nhánh | 100 | Độ sâu RRF; cần `ef_search` ≥ N |
| `hnsw.ef_search` | ≥ N (ví dụ 100) | Mặc định là 40 sẽ cắt nhánh vector |
| RRF k | 60 | k lớn ưu tiên tài liệu có mặt ở cả hai danh sách |
| Kiểu tsquery | OR, nhưng thử trước trên khoảng 50 truy vấn | AND: nhanh, dễ khớp rỗng. OR: recall cao hơn nhưng `ts_rank` phải chấm mọi tài liệu khớp, nên chậm hơn ở p95 |

## 8. Rủi ro và giới hạn (đưa vào mục Limits)

- Chỉ dùng 1 subforum và 1 model embedding.
- Full-text của PostgreSQL (`ts_rank`) **không phải BM25**.
- Model embedding có thể đã được huấn luyện trên cặp câu trùng của StackExchange, khiến baseline mạnh bất thường. Kiểm model card.
- Kết quả phụ thuộc N, k và kiểu tsquery.
- Latency phụ thuộc máy. Đã giảm phụ thuộc bằng giới hạn container, warm-up, xen kẽ A/B, 5 lượt, báo tỉ lệ.

## 9. Nguồn (đọc 15/11/2026)

- TensorFlow Datasets — BEIR (số liệu android, programmers, webmasters): https://www.tensorflow.org/datasets/catalog/beir
- MTEB — cqadupstack-wordpress: https://huggingface.co/datasets/mteb/cqadupstack-wordpress
- CQADupStack (Hoogeveen et al., ADCS 2015): https://github.com/D1Doris/CQADupStack
- BEIR (Thakur et al., 2021): https://arxiv.org/abs/2104.08663
- Mẫu hybrid + RRF trong PostgreSQL (Supabase): https://supabase.com/docs/guides/ai/hybrid-search
- pgvector (HNSW, `hnsw.ef_search`): https://github.com/pgvector/pgvector. Phiên bản và giá trị mặc định do S11 đối chiếu.
