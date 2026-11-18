# S03 — pgvector, HNSW và Docker

> Task S03 · Người phụ trách: Hoà · Cập nhật: 18/11/2026 (theo kết quả họp 15/11)
> Đầu vào cho S07 (docker-compose) và S09 (tạo index).

## 1. Phiên bản (pin, đọc ngày 18/11/2026)

| Thành phần | Giá trị | Nguồn |
|---|---|---|
| pgvector | **0.8.7** | README pgvector: `git clone --branch v0.8.7` |
| Image Docker | **`pgvector/pgvector:0.8.7-pg18-trixie`** (PostgreSQL 18) | README pgvector, mục Docker: tag = phiên bản pgvector + bản Postgres + bản Debian |

Không dùng tag `latest` hay `pg18`: hai tag này trôi theo phiên bản mới, nên chạy lại sau này có thể ra phần mềm khác.

## 2. Cài và dùng pgvector

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE docs (
  id        text PRIMARY KEY,           -- corpus-id của BEIR
  title     text,
  body      text,
  embedding vector(384),                -- bge-small-en-v1.5 ra 384 chiều
  tsv       tsvector GENERATED ALWAYS AS
            (to_tsvector('english', coalesce(title,'') || ' ' || coalesce(body,''))) STORED
);
```

- Kiểu `vector(384)` phải khớp số chiều của model.
- Toán tử khoảng cách: `<=>` là **cosine distance**. Embedding được chuẩn hoá (S04), nên cosine là lựa chọn tự nhiên.

## 3. Index HNSW

```sql
SET maintenance_work_mem = '1GB';      -- xây graph trong bộ nhớ cho nhanh
CREATE INDEX docs_embedding_hnsw ON docs
  USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);
```

**Ba tham số đã chốt:**

| Tham số | Giá trị | Ghi chú |
|---|---|---|
| `m` | 16 | Mặc định của pgvector: số kết nối tối đa mỗi tầng |
| `ef_construction` | 64 | Mặc định của pgvector: độ kỹ khi xây |
| `hnsw.ef_search` | **100** | Mặc định là 40. Tăng lên vì N = 100 |

**Vì sao phải tăng `ef_search`:** README pgvector ghi rằng số kết quả bị giới hạn bởi kích thước danh sách ứng viên động (`hnsw.ef_search`). Để mặc định 40 thì nhánh vector chỉ trả về khoảng 40 dòng, không đủ 100 ứng viên cho RRF.

Đặt cho mọi kết nối trong script đo: `SET hnsw.ef_search = 100;`, giống nhau ở cả hai nhánh.

**Iterative index scan** (có từ 0.8.0) chỉ cần khi truy vấn có điều kiện lọc. Seminar không lọc nên **không bật**. Để mặc định và ghi vào Held fixed.

## 4. Docker: giới hạn CPU/RAM

Mục đích là để độ trễ đo được ít phụ thuộc vào việc máy đang chạy gì khác, và giống nhau hơn giữa các máy (S14).

| Thiết lập | Giá trị đề xuất |
|---|---|
| CPU | `cpus: "2"` |
| RAM | `mem_limit: 4g` |
| Tham số Postgres | `-c maintenance_work_mem=1GB` (xây index); các tham số khác để mặc định |
| Dữ liệu | Volume tên `pgdata`. Với image PostgreSQL 18, mount vào `/var/lib/postgresql` (image 18 đổi thư mục dữ liệu so với bản 17; kiểm lại trong tài liệu image Postgres chính thức trước khi chốt) |

Máy chạy lại (S14) phải có tối thiểu 2 CPU và 4 GB RAM trống cho container. Ghi điều kiện này vào README.

## 5. Nguồn

- pgvector README (phiên bản, tag Docker, HNSW, `ef_search`, iterative scan): https://github.com/pgvector/pgvector (đọc 18/11/2026)
