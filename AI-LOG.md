# AI Log

One entry per task where AI tools were used. Tools: **Claude (claude.ai)** for discussion, explanations, drafts and slides; **Claude Code** on the team's shared machine for code, measurement and commits. The discussion session wrote the commands, Claude Code ran them and reported back, and the team decided each step.

> Draft written with Claude from the session history on 2026-11-19. Each member checks and completes the entries for their own tasks, especially **By hand**. Lines marked `<…>` are still to be filled in.

## Task 1: Learning the topic and the measurement method (S02–S05)

- **Tool:** Claude (claude.ai).
- **Asked for:** Explanations of vector search, pgvector/HNSW, PostgreSQL full-text search, RRF, recall@10 and p95; study docs (glossary, 5W-1H, lesson) for S02–S04; the design notes `notes/S02`–`S05`.
- **Kept:** The structure of `notes/S02`–`S05`: definitions and formulas, the measurement procedure for `make measure`, the decision table for the 15/11 meeting, and the held-fixed list.
- **Changed:** The first explanation was too dense for us, so we asked for a glossary first, then 5W-1H, then the lesson. AI also corrected two of our misreadings: p95 "ignores slow queries" (it measures them), and recall needing a spread (it is deterministic).
- **Rejected:** AI's first claim that the topic title's semicolon "means two separate directions". It was AI's own inference, stated as fact. We challenged it, AI said it was only an inference, and the team decided the scope itself: one question, hybrid vs vector-only inside PostgreSQL.
- **By hand:** Choosing the subforum, model, HNSW parameters, N, k and OR in the 15/11 meeting. Explaining each part to the others. `<Hiệp / Hoà: add what you studied or decided yourselves>`. Hoàng's part (S04) is in Task 8.

## Task 2: Building the pipeline and `make measure` (S07–S12)

- **Tool:** Claude Code (shared machine), with commands written in Claude (claude.ai).
- **Asked for:** docker-compose with pinned pgvector and resource limits; dataset download with checksums; embedding, loading and indexing; the two SQL branches; `make measure` with warm-up, 5 runs, recall@10, p95, median and min–max; sources with versions.
- **Kept:** `docker-compose.yml`, `scripts/` (download, prepare, measure), `sql/vector_only.sql`, `sql/hybrid.sql`, the `results/` layout, and the README run instructions.
- **Changed:**
  - Windows Smart App Control blocked the psycopg-binary DLL, so all database access was moved into a bench container.
  - Python 3.12 instead of 3.14 for the venv; GNU make installed through winget.
  - **AI was wrong:** the hybrid SQL (from the AI-written `notes/S04` spec) did not break ties inside the full-text CTE, so 2 of 699 queries gave a different top-10 between runs. **Detected by** the check "recall must be identical in all 5 runs". Fixed by adding `d.id` to the ordering (commit `6f5eb7b`).
  - p95 ratios were first computed from rounded medians (21.1× vs 21.2×). Recomputed from unrounded values (`ea6d645`, `6d4fcf8`).
- **Rejected:** Re-running the embedding on every run; embeddings are computed once and checked by sha256.
- **By hand:** Starting Docker Desktop, installing make, approving each step and pushing. `<Hoà: add your parts of S07–S08>`. Hoàng's parts (S09–S11) are in Tasks 9–11.

## Task 3: Explaining the result and measuring more subforums (S12 diagnostics, S23)

- **Tool:** Claude Code; analysis and planning in Claude (claude.ai).
- **Asked for:** Repeat runs, a full-text-only diagnostic, worked examples, a supplementary AND variant, screening of the other 11 subforums, and full runs on mathematica and gaming.
- **Kept:** `results/repeat-*`, `results/examples.md`, `results/supplementary-and/`, `results/subforum-screening.csv`, `results/all-subforums.csv`, `notes/S23-subforum-khac.md`.
- **Changed:**
  - **AI was wrong:** Claude Code reported that "android" matches about 77% of the corpus. That figure was the query planner's estimate for one whole OR query, not a count. **Detected** when Claude Code counted directly: 47.1%. The wrong figure had already been written into `notes/S23` (`f7ecbfc`) and was corrected in `61f56d0`.
  - Run-to-run p95 differences turned out larger than the spread inside one run, so we added more repeat runs.
- **Rejected:** Our own idea to run all subforums and show only android plus one where hybrid wins. AI pushed back: it would be cherry-picking, and about 20 CPU-hours. Instead we screened all 11 cheaply, chose by a criterion written down before measuring, and report every subforum we measured.
- **By hand:** Choosing mathematica and gaming within the time budget; deciding to stop measuring after three subforums.

## Task 4: REPORT (S16)

- **Tool:** Claude (claude.ai) for the draft; Claude Code to check numbers and commit.
- **Asked for:** A REPORT of at most 3 pages that follows the template sections, using only numbers from `results/`.
- **Kept:** The structure, the answer-first opening, the results tables, the explanation of why hybrid lost, the recommendation and the limits.
- **Changed:**
  - The first draft was 5 pages; it was cut to 3.
  - Claude Code checked about 115 numbers against `results/` before the first commit and found no mismatch.
  - **AI was wrong:** the draft said the loss "shrinks as full-text/vector recall gets closer". The numbers do not follow that order (mathematica 0.46 → −8.4, android 0.58 → −10.1). **Detected** when the numbers were put side by side. Replaced by the OR match share, which does follow the order.
  - **AI was wrong:** the REPORT said "the B/A ratio should transfer better" between machines. **Refuted** by repeat-4 (28.7×) and the S14 rerun (25.1×). Rewritten as a measured range: +40 to +48 ms, 19–29×.
  - Added the storage cost and missing Vietnamese text-search config after measuring them (`results/storage.csv`, `results/textsearch-configs.txt`).
- **Rejected:** Changing the design after seeing hybrid lose. The agreed OR design stays the main result; AND is labeled supplementary.
- **By hand:** Reading and approving the final text. `<team: add edits you made yourselves>`

## Task 5: Slides (S15)

- **Tool:** Claude (claude.ai), Slides artifact; slide-design rules read from public skills (`anthropics/skills` pptx, `educational-presentation`, `presentation-slides`).
- **Asked for:** A 10-minute deck for listeners who know nothing about the topic, following the flow problem → solution → cost → demo.
- **Kept:** The flow, the speaker notes split across the three of us, and figures built inside the slides from `results/`.
- **Changed:**
  - Three background colours replaced by one light background, because switching backgrounds was tiring on screen.
  - Minimum text raised from 24 px to 28 px, body to 40 px; paragraphs moved into the speaker notes.
  - Added a terminology slide about vector search, placed before the problem slide.
  - The "cost" slide first showed OR vs AND results, which is not a trade-off. It was rebuilt as four costs: latency, storage, tuning knobs, language support.
  - Added real screenshots (the StackExchange duplicate pair, `make demo`, `make measure`); the `make measure` screenshot was first saved as `results/repeat-4` so its numbers are in the log.
- **Rejected:** Alternating backgrounds (recommended by the public skills) and decorative stock photos.
- **By hand:** Taking the screenshots; reviewing every slide; `<Hoà: slide edits>`.

## Task 6: Demo command (S17 preparation)

- **Tool:** Claude Code.
- **Asked for:** `make demo Q="..."`, which runs one question through both branches and prints both top-10s with the correct answer marked.
- **Kept:** `scripts/demo.py` and the Makefile target. The demo output matched `results/raw.csv` run 1 for both branches.
- **Changed:** Nothing.
- **Rejected:** —
- **By hand:** Running the demo and taking the screenshot.

## Task 7: Internal rerun on another machine (S14)

- **Tool:** `<Hoà: tool used, if any>`
- **Asked for:** Follow only the README on a fresh clone, run `make measure`, compare with the team's numbers, and report README gaps.
- **Kept:** `results/rerun-s14/`, `notes/S14-red-team-noi-bo.md`.
- **Changed:** The two README gaps found (starting Docker Desktop; `make measure` overwriting `results/`) were fixed in `a0180e2`.
- **Rejected:** `<Hoà>`
- **By hand:** `<Hoà: running the rerun, checking the commit and the nDCG difference>`

## Task 8: Embedding, full-text search and RRF notes (S04, Hoàng)

- **Tool:** Claude (claude.ai) for the explanations and the note draft (see Task 1); Claude Code to commit it (commit `3fe71bd`, trailer `Co-Authored-By: Claude Opus 5.5`).
- **Asked for:**
  - How a local embedding model works, and what the model card of `bge-small-en-v1.5` says about dimensions, input length, license and the query instruction.
  - How PostgreSQL full-text search works (`tsvector`, `to_tsquery` vs `plainto_tsquery`, `ts_rank`, GIN) and how RRF fuses two ranked lists.
  - `notes/S04-embedding-fts-rrf.md` as the input for S09 (prepare) and S10 (queries): model, how to embed, full-text setup, the two-branch SQL, risks, sources.
- **Kept:**
  - The model `BAAI/bge-small-en-v1.5` (384 dimensions, 512 tokens, MIT), normalized, with documents embedded as `title + " " + body` without a prefix and queries with the model card's instruction prefix.
  - "Embed once, store the `.npy` files with a sha256" so a re-runner only checks a checksum.
  - A stored generated `tsv` column with the `english` configuration plus a GIN index; an OR tsquery (`replace(plainto_tsquery(...)::text, '&', '|')`) ranked by `ts_rank`; RRF with N = 100 candidates per branch and k = 60.
  - The baseline reuses the exact `vec` CTE of the hybrid query, so the two branches differ only in full-text + RRF.
  - The risk that the model card does not list its training data, so the model may have seen StackExchange. It became the "Embedding model" limit in REPORT.
  - The warning that `ts_rank` must score every matching document, so OR queries would make hybrid slower. The measurement confirmed it: median p95 2.12 ms (vector-only) vs 44.80 ms (hybrid), +42.69 ms, 21.17× (`results/summary.csv`).
- **Changed:**
  - The SQL in section 3 of the note later changed: it needed a tie-break (Task 10).
  - The PostgreSQL docs link in the note points to `/docs/current/`; REPORT cites `/docs/18/`, the version we actually ran (Task 11).
  - The Supabase hybrid-search example is cited in the notes as a hybrid + RRF pattern. It is not listed in REPORT sources.
- **Rejected (left out on purpose, as recorded in the note):**
  - Title weighting in `ts_rank` and any BM25-style extension: the full-text branch is plain `ts_rank`, and REPORT says it is not BM25.
  - The default AND behaviour of `plainto_tsquery` as the main design. The team chose OR at the 15/11 meeting; AND was measured later as a supplementary variant (`sql/hybrid_and.sql`, `results/supplementary-and/`).
- **By hand:** `<Hoàng: what you read yourself (model card, PostgreSQL docs chapter, RRF description) and what you could explain to the others without AI>`

## Task 9: Prepare script — embeddings, loading and indexes (S09, Hoàng)

- **Tool:** Claude Code (shared machine), with commands written in Claude (claude.ai).
- **Asked for:** One script that embeds the corpus and queries with the local model, saves the embeddings with a sha256, creates the table, bulk-loads it, builds the HNSW and GIN indexes and runs `ANALYZE`.
- **Kept:**
  - `scripts/prepare.py` and `scripts/common.py`. Table `docs(id, title, body, embedding vector(384), tsv generated stored)`, HNSW `m = 16`, `ef_construction = 64` with `vector_cosine_ops`, GIN on `tsv`, `maintenance_work_mem = 1GB` for the build.
  - Embedding is skipped when `data/emb_*.npy` match `data/SHA256SUMS`; the files are committed (`emb_corpus.npy` 35.3 MB, `emb_queries.npy` 1.1 MB) and marked binary in `.gitattributes`.
  - The model revision pinned to a commit hash (`5c38ec7c…`), not only the model name, and library versions pinned in `requirements.txt`.
  - Timing of 100 documents written to `results/embed_timing.txt`: 15.73 s on an i5-13500H, CPU only, 12 torch threads, Python 3.12.10, torch 2.15.0+cpu, sentence-transformers 6.3.0.
- **Changed:**
  - The script has two modes. `--embed-only` runs on the host `.venv` (needs torch). The load and index steps run in a `bench` container, because Windows Smart App Control blocked the psycopg-binary DLL on the host. The same commit added the `bench` service and `docker/bench.Dockerfile`.
  - Later, for S23, the script was parameterized by the `SUBFORUM` variable. Full embedding times recorded: mathematica 16,705 documents in 42.3 min, gaming 45,301 documents in 30.9 min. For android only the 100-document timing is in `results/embed_timing.txt`; the README says about 55 min for the full run.
- **Rejected:** Re-embedding on every run (see Task 2); the checksum check replaced it.
- **By hand:** `<Hoàng: whether you ran make embed / make prepare yourself, what you checked (row count 22,998, index build times), and what you would verify before trusting the embedding files>`

## Task 10: Vector-only and hybrid SQL (S10, Hoàng)

- **Tool:** Claude Code (shared machine); the SQL came from the AI-written spec in `notes/S04` section 3.
- **Asked for:** Two queries that differ only in the full-text part and RRF, plus a check script.
- **Kept:**
  - `sql/vector_only.sql` and `sql/hybrid.sql`, with an identical `vec` CTE (top-100 by cosine distance).
  - `scripts/check_sql.py`. It asserts that the `vec` CTE text is identical in both files, that `vec` returns exactly 100 rows for all 699 queries at `hnsw.ef_search = 100`, and that both `EXPLAIN` plans use `Index Scan using docs_embedding_hnsw`.
- **Changed:**
  - **AI was wrong:** the spec ordered `ts_rank` without a tie-break. Ties at the `LIMIT 100` cut gave different candidates, so 2 of 699 queries changed top-10 between runs. **Detected by** the measurement check "recall must be identical in all 5 runs". Fixed in `6f5eb7b` by adding `d.id` to the full-text ordering. After the fix, recall is identical in all five runs (60.63 % and 50.54 %, `results/summary.csv`). The deviation from the note is written in the header of `sql/hybrid.sql`.
  - The vector-only query also breaks ties by `id`, so both branches are deterministic.
  - `check_sql.py` does not test determinism; only the repeat check did.
- **Rejected:** —
- **By hand:** `<Hoàng: reading the SQL line by line, the EXPLAIN output, what you tested>`

## Task 11: Sources with versions (S11, Hoàng)

- **Tool:** Claude Code (shared machine) to write the entries into REPORT; the versions come from the files and logs of the real run.
- **Asked for:** The official sources for PostgreSQL, pgvector, the dataset and the model, each with the date read and the exact version or revision used.
- **Kept:** Seven entries (commit `f41210c`), all marked read on 2026-11-18, with versions that match `docker-compose.yml`, `requirements.txt` and `scripts/common.py`: pgvector 0.8.7, image tag `0.8.7-pg18-trixie`, PostgreSQL 18.7, the model revision hash, the dataset revision hash, sentence-transformers 6.3.0 (torch 2.15.0+cpu, transformers 5.23.0), psycopg 3.3.9 with pgvector-python 0.5.1.
- **Changed:**
  - The PostgreSQL docs link was changed from `/docs/current/` (in `notes/S04`) to `/docs/18/`, so the link matches the version we ran.
  - The list grew later: BEIR (Thakur et al., 2021) was added, and the dataset entry now covers mathematica and gaming with their revisions.
- **Rejected:** — (The Supabase example from `notes/S04` is not in REPORT sources; REPORT lists only official docs, model and dataset pages, and the BEIR paper.)
- **By hand:** `<Hoàng: opening each link and checking that the page says what the entry claims, and that the versions match what we ran>`

## Task 12: This AI-LOG (S18, Hoàng)

- **Tool:** Claude Code.
- **Asked for:** Read the team tracker (`LeeTKOB-seminar-tracker.xlsx`) and the repository history, then write more detailed entries for Hoàng's tasks (S04, S09, S10, S11) so the repo shows the context behind them.
- **Kept:** Only statements that can be checked in the repo: commit hashes, `notes/`, `sql/`, `scripts/`, `results/` and REPORT. Task 8 to Task 11 were written from that evidence, not from Hoàng's memory of the sessions.
- **Changed:** Placeholders in Tasks 1 and 2 now point to Tasks 8–11 for Hoàng's parts.
- **Rejected:** Writing the **By hand** lines for Hoàng. Only Hoàng knows what was done by hand, so those lines stay as `<Hoàng: …>` until filled in.
- **By hand:** `<Hoàng: checking every line of Tasks 8–11 against what actually happened, filling the By hand lines, and adding S21/S22 if AI is used for them>`

## Where AI was wrong, and how we found out

| What AI got wrong | How it was detected | Fix |
|---|---|---|
| The hybrid SQL had no tie-break in the full-text ranking, so top-10s changed between runs | The "recall identical in all 5 runs" check failed for 2/699 queries | `6f5eb7b` |
| "android matches ~77% of the corpus" (a planner estimate reported as a count) | A direct count gave 47.1% | `61f56d0` |
| "The loss follows full-text/vector recall" | The numbers did not follow that order when placed side by side | REPORT uses the OR match share |
| "The B/A ratio transfers between machines" | repeat-4 (28.7×) and S14 (25.1×) fell outside it | REPORT reports the measured range |
| The topic scope stated as fact from the title's punctuation | We asked why, and AI said it was only an inference | The team decided the scope |
