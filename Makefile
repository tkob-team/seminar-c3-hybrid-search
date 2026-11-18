# C3 hybrid search measurement. Needs Docker (Compose v2) and GNU make.
# Everything that talks to PostgreSQL runs in the `bench` container (python:3.12 + psycopg),
# so the host needs Python 3.12 only to re-create the embeddings (`make embed`).

COMPOSE := docker compose
BENCH   := $(COMPOSE) --profile tools run --rm bench

ifeq ($(OS),Windows_NT)
  PY_BOOT := py -3.12
  VENV_PY := .venv/Scripts/python.exe
else
  PY_BOOT := python3.12
  VENV_PY := .venv/bin/python
endif

.PHONY: up down bench-image download prepare check measure embed venv clean-db

## up: start PostgreSQL + pgvector (2 CPUs, 4 GB) and wait until healthy
up:
	$(COMPOSE) up -d --wait db

down:
	$(COMPOSE) down

bench-image:
	$(COMPOSE) --profile tools build bench

## download: fetch CQADupStack android at the pinned revision into data/raw/ and verify checksums
download: data/raw/corpus.jsonl

data/raw/corpus.jsonl: | bench-image
	$(BENCH) python scripts/download.py

## prepare: verify embeddings (sha256), create table, load, build HNSW + GIN, ANALYZE
prepare: up download bench-image
	$(BENCH) python scripts/prepare.py

## check: CTE vec returns 100 rows; both plans use the HNSW index
check: up bench-image
	$(BENCH) python scripts/check_sql.py

## measure: warm-up + 5 alternating runs -> results/raw.csv, results/summary.csv
measure: up download bench-image
	$(BENCH) python scripts/measure.py

## embed: (host) re-create data/emb_*.npy with sentence-transformers; only needed if checksums differ
embed: venv
	$(VENV_PY) scripts/prepare.py --embed-only

venv: $(VENV_PY)

$(VENV_PY):
	$(PY_BOOT) -m venv .venv
	$(VENV_PY) -m pip install -r requirements.txt

## clean-db: stop the database and delete its volume
clean-db:
	$(COMPOSE) down -v
