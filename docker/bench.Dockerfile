# Client container for load / SQL check / measurement (avoids host libpq / DLL issues).
FROM python:3.12.10-slim-bookworm
COPY docker/requirements-bench.txt /tmp/requirements-bench.txt
RUN pip install --no-cache-dir -r /tmp/requirements-bench.txt
WORKDIR /work
