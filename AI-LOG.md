# AI Log

One entry per task where AI tools were used. Tools: **Claude (claude.ai)** for discussion, explanations, drafts and slides; **Claude Code** on the team's shared machine for code, measurement and commits. The discussion session wrote the commands, Claude Code ran them and reported back, and the team decided each step.

> Draft written with Claude from the session history on 2026-11-19. Each member checks and completes the entries for their own tasks, especially **By hand**. Lines marked `<…>` are still to be filled in.

## Task 1: Learning the topic and the measurement method (S02–S05)

- **Tool:** Claude (claude.ai).
- **Asked for:** Explanations of vector search, pgvector/HNSW, PostgreSQL full-text search, RRF, recall@10 and p95; study docs (glossary, 5W-1H, lesson) for S02–S04; the design notes `notes/S02`–`S05`.
- **Kept:** The structure of `notes/S02`–`S05`: definitions and formulas, the measurement procedure for `make measure`, the decision table for the 15/11 meeting, and the held-fixed list.
- **Changed:** The first explanation was too dense for us, so we asked for a glossary first, then 5W-1H, then the lesson. AI also corrected two of our misreadings: p95 "ignores slow queries" (it measures them), and recall needing a spread (it is deterministic).
- **Rejected:** AI's first claim that the topic title's semicolon "means two separate directions". It was AI's own inference, stated as fact. We challenged it, AI said it was only an inference, and the team decided the scope itself: one question, hybrid vs vector-only inside PostgreSQL.
- **By hand:** Choosing the subforum, model, HNSW parameters, N, k and OR in the 15/11 meeting. Explaining each part to the others. `<Hiệp / Hoà / Hoàng: add what you studied or decided yourselves>`

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
- **By hand:** Starting Docker Desktop, installing make, approving each step and pushing. `<Hoà / Hoàng: add your parts of S07–S11>`

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

## Where AI was wrong, and how we found out

| What AI got wrong | How it was detected | Fix |
|---|---|---|
| The hybrid SQL had no tie-break in the full-text ranking, so top-10s changed between runs | The "recall identical in all 5 runs" check failed for 2/699 queries | `6f5eb7b` |
| "android matches ~77% of the corpus" (a planner estimate reported as a count) | A direct count gave 47.1% | `61f56d0` |
| "The loss follows full-text/vector recall" | The numbers did not follow that order when placed side by side | REPORT uses the OR match share |
| "The B/A ratio transfers between machines" | repeat-4 (28.7×) and S14 (25.1×) fell outside it | REPORT reports the measured range |
| The topic scope stated as fact from the title's punctuation | We asked why, and AI said it was only an inference | The team decided the scope |
