# S14 — Red-team nội bộ: chạy lại trên máy khác

> Người chạy: Hoà · Ngày chạy: 18/11/2026 (kết thúc 15:48 UTC) · Ghi lại: 19/11/2026
> Kết quả thô: [results/rerun-s14/](../results/rerun-s14/) (`summary.csv`, `run_info.txt`)

## Máy và phiên bản

- Intel Core i5-12500H (12 nhân, 16 luồng), RAM 16 GiB, Windows 11 Home Single Language 64-bit (build 26300)
- Docker Desktop 4.99.0, Engine 29.9.3, Compose v5.7.0; container benchmark thấy 4 CPU qua WSL2
- GNU make 4.4.1 (`winget install ezwinports.make`, theo README)
- Commit đã clone: `1337749` (đã có `6f5eb7b`, `sql/hybrid.sql` phá hoà bằng `d.id`)

## Làm theo README

- Setup: 2 phút 44 giây, tính từ `git clone` tới khi `make prepare` nạp xong dữ liệu, dựng index và chạy `ANALYZE`. Cả hai file embedding khớp SHA-256.
- `make up`, `make download`, `make prepare`, `make check`, `make measure` đều chạy được theo README.

## Lỗi hoặc thiếu trong README

1. **Requirements:** thiếu bước khởi động Docker Desktop khi daemon đang tắt. Lỗi nguyên văn: `Could not retrieve status. Is Docker Desktop running?`. Cách xử lý: chạy `docker desktop start` rồi làm tiếp.
2. **Run:** README chưa nói rõ `make measure` ghi đè các file kết quả đang được Git theo dõi. Người chạy phải tự chạy trên bản sao tạm để giữ bản clone sạch.

## So với kết quả của nhóm (android)

| | Nhóm (lần chính) | Máy red-team |
|---|---|---|
| recall@10 A / B | 60.63 / 50.54 | 60.63 / 50.54 (giống hệt) |
| Tốt lên / tệ đi / giữ nguyên | 33 / 133 / 533 | 33 / 133 / 533 (giống hệt) |
| nDCG@10 A / B | 0.4759 / 0.4010 | 0.4759 / 0.4004 |
| p95 A / B (ms) | 2.12 / 44.80 | 1.98 / 49.70 |
| p95 B − A / B / A | +42.7 ms / 21.2× | +47.7 ms / 25.1× |

- Top-10 giống nhau ở cả 5 lượt trên máy red-team.
- nDCG@10 của B lệch −0.0006 dù đã có phần phá hoà. Recall, số câu tốt lên/tệ đi và nDCG của A đều trùng, nên chỉ có thứ tự bên trong top-10 của hybrid khác nhau ở vài truy vấn. Nguyên nhân chưa xác định. Nghi là index HNSW dựng lại trên máy khác làm thứ hạng ứng viên 11–100 bên vector hơi khác.
- Độ trễ: hybrid-OR chậm hơn vector cả về ms lẫn tỉ lệ, nằm trong khoảng 5 lần đo trên 2 máy (+40 đến +48 ms, 19–29×). Cả hiệu số lẫn tỉ lệ đều không giữ nguyên giữa các máy.

## Đã sửa sau red-team

- README: thêm bước khởi động Docker Desktop.
- `make measure OUT=<thư mục>`: ghi kết quả ra thư mục khác để không ghi đè kết quả chính thức. Mặc định vẫn là `results/`.
