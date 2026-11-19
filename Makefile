# C3 hybrid search measurement. Needs Docker (Compose v2) and GNU make.
# Everything that talks to PostgreSQL runs in the `bench` container (python:3.12 + psycopg),
# so the host needs Python 3.12 only to re-create the embeddings (`make embed`).
#
# SUBFORUM selects the CQADupStack subforum (default android = main result, original paths).
#   make measure                          -> results/            (database c3)
#   make measure SUBFORUM=mathematica     -> results/mathematica/ (database c3_mathematica)

SUBFORUM ?= android
export SUBFORUM

COMPOSE := docker compose
BENCH   := $(COMPOSE) --profile tools run --rm -e SUBFORUM=$(SUBFORUM) bench

ifeq ($(SUBFORUM),android)
  RAW_DIR := data/raw
else
  RAW_DIR := data/raw/$(SUBFORUM)
endif

ifeq ($(OS),Windows_NT)
  PY_BOOT := py -3.12
  VENV_PY := .venv/Scripts/python.exe
else
  PY_BOOT := python3.12
  VENV_PY := .venv/bin/python
endif

.PHONY: up down bench-image download prepare check measure diagnose demo embed venv clean-db

## up: start PostgreSQL + pgvector (2 CPUs, 4 GB) and wait until healthy
up:
	$(COMPOSE) up -d --wait db

down:
	$(COMPOSE) down

bench-image:
	$(COMPOSE) --profile tools build bench

## download: fetch the subforum at its pinned revision into $(RAW_DIR)/ and verify checksums
download: $(RAW_DIR)/corpus.jsonl

$(RAW_DIR)/corpus.jsonl: | bench-image
	$(BENCH) python scripts/download.py

## prepare: verify embeddings (sha256), create table, load, build HNSW + GIN, ANALYZE
prepare: up download bench-image
	$(BENCH) python scripts/prepare.py

## check: CTE vec returns 100 rows; both plans use the HNSW index
check: up bench-image
	$(BENCH) python scripts/check_sql.py

## measure: warm-up + 5 alternating runs -> results[/<subforum>]/raw.csv, summary.csv
##   optional: make measure OUT=results/repeat-2 SQL_B=sql/hybrid_and.sql
OUT   ?=
SQL_B ?=
measure: up download bench-image
	$(BENCH) python scripts/measure.py $(if $(OUT),--out $(OUT)) $(if $(SQL_B),--sql-b $(SQL_B))

## diagnose: full-text-only recall@10 and example queries (needs a finished `make measure`)
diagnose: up bench-image
	$(BENCH) python scripts/diagnose.py

## demo: one question through A and B, top-10 tables with ★ = relevant (host embeds Q, bench runs SQL)
##   make demo Q="How to use an android phone as a wireless webcam?"
Q ?=
export Q
demo: up download bench-image venv
	$(VENV_PY) scripts/demo.py --embed
	$(BENCH) python scripts/demo.py

## embed: (host) create data[/<subforum>]/emb_*.npy with sentence-transformers; skipped if checksums match
embed: venv
	$(VENV_PY) scripts/prepare.py --embed-only

venv: $(VENV_PY)

$(VENV_PY):
	$(PY_BOOT) -m venv .venv
	$(VENV_PY) -m pip install -r requirements.txt

## clean-db: stop the database and delete its volume
clean-db:
	$(COMPOSE) down -v
