# S23: Thử các subforum khác (kế hoạch và tiêu chí)

> Task S23 · Viết ngày 18/11/2026, **trước khi tính** bất kỳ số liệu nào cho các subforum khác.
> Kết quả chính vẫn là subforum android với thiết kế đã chốt ở S05. Phần này chỉ là phần bổ sung.

## 1. Lý do

- Trên android, hybrid (vector + full-text OR + RRF) **kém hơn** vector-only: recall@10 đạt 50.54% so với 60.63% (Δ −10.09 điểm phần trăm), còn p95 tăng khoảng ×21.
- Có một nguyên nhân khả dĩ nằm ở chính dữ liệu: `android` có trong 10,823/22,998 = 47.1% tài liệu; tỉ lệ khớp OR trung vị 41.0% corpus. Vì vậy tsquery OR khớp một phần rất lớn corpus, `ts_rank` xếp hạng nhiễu, và Postgres chọn Seq Scan thay vì GIN.
  - *Sửa ngày 18/11/2026:* bản đầu của file này ghi "~77% corpus". Đó thực ra là ước lượng của planner cho cả tsquery OR của một truy vấn, không phải cho token `android` (xem `results/diagnostics.txt`, `results/subforum-screening.csv`).
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

## 3b. Quyết định sau sàng lọc (18/11/2026)

Bảng sàng lọc nằm ở `results/subforum-screening.csv`. Đo đầy đủ hai subforum:

| Subforum | Lý do chọn | Tỉ lệ khớp OR trung vị | % truy vấn có token kiểu mã | Ước lượng thời gian embed |
|---|---|---|---|---|
| **gaming** | Tỉ lệ khớp thấp nhất trong 12 subforum | 13.5% | 4.6% | ~119 phút |
| **mathematica** | Rẻ nhất để embed, có nhiều token kiểu mã | 30.8% | 17.0% | ~44 phút |

- Thiết kế giữ nguyên theo S05, chỉ đổi subforum: cùng model và revision, cùng tiền tố truy vấn, HNSW, N, k, ef_search, quy trình đo.
- Mỗi subforum đo cả **OR** (nhánh chính, giống android) và **AND** (bổ sung, như `sql/hybrid_and.sql`), cùng recall@10 khi chỉ dùng full-text.

## 4. Cách báo cáo

- REPORT có một bảng gồm **mọi subforum đã đo đầy đủ**, kể cả subforum mà kết quả không ủng hộ hybrid. Không chọn lọc kết quả.
- Slide nhấn vào android (kết quả chính) và thêm 1 trường hợp minh hoạ từ các subforum khác.
- Ghi vào Limits: tiêu chí được chọn sau khi đã thấy kết quả android, nên phần này mang tính thăm dò (exploratory), không phải kiểm định giả thuyết.
