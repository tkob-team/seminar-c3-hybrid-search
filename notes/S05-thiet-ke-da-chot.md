# S05 — Thiết kế đã chốt (họp 15/11/2026)

> Người ghi: Hiệp · Chi tiết: [S02](S02-cach-do.md), [S03](S03-pgvector-hnsw-docker.md), [S04](S04-embedding-fts-rrf.md)

## Câu hỏi

> In PostgreSQL with pgvector, how much does hybrid search (HNSW vector search fused with built-in full-text search via reciprocal rank fusion) raise recall@10 over vector-only search on a public labeled retrieval dataset, and how much does it add to p95 query latency (ms)?

**Phạm vi:** một câu hỏi, một baseline (vector-only), một thay đổi (thêm full-text + RRF), trong PostgreSQL. Không so với vector database riêng.

## Quyết định

| Hạng mục | Đã chốt |
|---|---|
| Dataset | BEIR CQADupStack, subforum **android** (22,998 tài liệu, 699 truy vấn, 1,696 dòng qrels) |
| Model embedding | `BAAI/bge-small-en-v1.5` (384 chiều), chuẩn hoá; truy vấn có tiền tố chỉ dẫn, tài liệu không |
| Phần mềm | `pgvector/pgvector:0.8.7-pg18-trixie` (PostgreSQL 18 + pgvector 0.8.7) |
| HNSW | `m = 16`, `ef_construction = 64`, `hnsw.ef_search = 100`, cosine (`vector_cosine_ops`) |
| Full-text | Cấu hình `english`, GIN, tsquery **OR**, `ts_rank` |
| Trộn | RRF, **k = 60**, **N = 100** ứng viên mỗi nhánh, top-10 |
| Đo | Warm-up 1 lượt; 5 lượt × 2 nhánh, xen kẽ thứ tự; recall@10 theo qrels; p95 theo nearest-rank; báo trung vị (min–max), hiệu và tỉ lệ |
| Tài nguyên | Container 2 CPU, 4 GB RAM |

## Held fixed (chép vào REPORT)

Subforum android · file embedding (sha256) và model `bge-small-en-v1.5` · PostgreSQL 18 + pgvector 0.8.7 · `m = 16`, `ef_construction = 64`, `ef_search = 100`, iterative scan tắt · N = 100, k = 60 · tsquery OR, `ts_rank`, cấu hình `english` · 2 CPU, 4 GB RAM · warm-up 1 lượt, 5 lượt đo, xen kẽ A/B · p95 nearest-rank · latency chỉ tính thời gian SQL đo ở client.
