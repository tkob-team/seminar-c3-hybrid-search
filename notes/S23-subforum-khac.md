# S23: Thử các subforum khác (kế hoạch và tiêu chí)

> Task S23 · Viết ngày 18/11/2026, **trước khi tính** bất kỳ số liệu nào cho các subforum khác.
> Kết quả chính vẫn là subforum android với thiết kế đã chốt ở S05. Phần này chỉ là phần bổ sung.

## 1. Lý do

- Trên android, hybrid (vector + full-text OR + RRF) **kém hơn** vector-only: recall@10 đạt 50.54% so với 60.63% (Δ −10.09 điểm phần trăm), còn p95 tăng khoảng ×21.
- Có một nguyên nhân khả dĩ nằm ở chính dữ liệu: token `android` khớp khoảng **77% corpus**. Vì vậy tsquery OR gần như khớp mọi tài liệu, `ts_rank` xếp hạng nhiễu, và Postgres chọn Seq Scan thay vì GIN.
- Câu hỏi phụ: liệu kết quả có khác trên subforum mà full-text "sắc" hơn (mỗi truy vấn khớp ít tài liệu hơn, có nhiều token kiểu mã)? Mục đích là để mục Recommendation nói được **khi nào nên và không nên dùng** hybrid.

## 2. Tiêu chí sàng lọc (không cần embed)

| | Tiêu chí | Cách tính |
|---|---|---|
| **Chính** | Tỉ lệ khớp trung vị của tsquery OR (% corpus) | Với mỗi truy vấn, đếm số tài liệu có `tsv @@ tsquery_OR(query)` rồi chia cho kích thước corpus. Lấy trung vị trên mọi truy vấn có trong qrels. Thấp hơn là tốt hơn. |
| Phụ | % truy vấn có token kiểu mã | Token chứa `_`, hoặc kiểu camelCase (chữ thường đứng ngay trước chữ hoa), hoặc có `()`, hoặc có số từ 3 chữ số trở lên. Cao hơn là tốt hơn, vì full-text hợp với khớp chính xác. |

Cấu hình full-text giống hệt android: `'english'`, `tsv` tạo từ `title || ' ' || body`, tsquery OR (đổi `&` thành `|`).

## 3. Phạm vi

- **Sàng lọc cả 11 subforum còn lại** của CQADupStack: english, gaming, gis, mathematica, physics, programmers, stats, tex, unix, webmasters, wordpress. Mỗi subforum pin revision `mteb/cqadupstack-<tên>`. Chỉ nạp text vào bảng tạm có `tsv` + GIN, không embed.
- Kết quả: `results/subforum-screening.csv`, sắp theo tỉ lệ khớp tăng dần, kèm số tài liệu, số truy vấn, số dòng qrels, và ước lượng thời gian embed = số tài liệu × 15.73 s / 100 / 60 (phút, trên máy nhóm).
- **Đo đầy đủ 2–3 subforum có tỉ lệ khớp thấp nhất**, có cân nhắc thời gian embed. Ví dụ, nếu subforum xếp đầu cần hơn 2 giờ embed thì có thể lấy subforum kế tiếp. Đo bằng đúng quy trình của android: cùng model, HNSW, N, k, ef_search, warm-up + 5 lượt xen kẽ A/B.
- Việc chọn subforum để đo là một quyết định riêng, đưa ra **sau** khi có bảng sàng lọc.

## 4. Cách báo cáo

- REPORT có một bảng gồm **mọi subforum đã đo đầy đủ**, kể cả subforum mà kết quả không ủng hộ hybrid. Không chọn lọc kết quả.
- Slide nhấn vào android (kết quả chính) và thêm 1 trường hợp minh hoạ từ các subforum khác.
- Ghi vào Limits: tiêu chí được chọn sau khi đã thấy kết quả android, nên phần này mang tính thăm dò (exploratory), không phải kiểm định giả thuyết.
