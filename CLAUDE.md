# CLAUDE.md — Seminar C3 (hybrid search vs vector-only)

## Repo
- Repo chính (máy local): `D:\HK7\Advanced_Web_Dev\Seminar\seminar-c3-hybrid-search`
- Remote: https://github.com/tkob-team/seminar-c3-hybrid-search (nhánh `main`)
- Chỉ làm việc trong repo chính, không tạo clone phụ.

## Quyết định đã chốt
- Xem `notes/S05-thiet-ke-da-chot.md` (nguồn duy nhất; không chép lại vào đây).

## Spec đo
- Cách đo recall@10, p95, dataset: `notes/S02-cach-do.md`
- pgvector HNSW + Docker: `notes/S03-pgvector-hnsw-docker.md`
- Embedding, full-text, RRF: `notes/S04-embedding-fts-rrf.md`

## Quy ước
- Mỗi task một commit riêng.
- Commit message: `<loại>(Sxx): ...` (vd. `docs(S05): ...`, `feat(S06): ...`).
- KHÔNG thêm dòng `Co-Authored-By: Claude ...` (hay bất kỳ attribution Claude nào) vào commit message.
- Docs của repo (README, REPORT, AI-LOG, TALK, code comment) viết tiếng Anh.
- `notes/` viết tiếng Việt.
- KHÔNG commit `SELF_ASSESSMENT_REPORT.md` (hay file SELF_ASSESSMENT nào) vào repo.

## Kết thúc mỗi lệnh
In khối **"Báo cáo cho phiên thảo luận"** gồm:
- Nhiệm vụ
- File đã tạo/sửa
- Kết quả kiểm
- Commit (hash + link)
- Bất thường
- Cần quyết định
