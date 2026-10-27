# The relay image. Build context is the repo root (azure.yaml: docker.context ..), because the
# relay imports B's tely.qa and reads the judge-cut bundle it answers from. The root .dockerignore keeps the
# context to exactly those files. No keys are baked in: auth is the container's managed identity at run time.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PIP_NO_CACHE_DIR=1 PYTHONPATH=/app
WORKDIR /app

COPY relay/requirements.txt relay/requirements.txt
RUN pip install -r relay/requirements.txt

# B's package, editable, so qa/bundle.py still finds web/public/replay/v1/judge/ two folders up (its JUDGE path).
COPY pipeline/pyproject.toml pipeline/pyproject.toml
COPY pipeline/tely pipeline/tely
RUN pip install -e "./pipeline[mcp]"

# Only what B's load_bundle() reads: the match the tools answer from (no audio, no cues).
COPY web/public/replay/v1/judge/meta.json web/public/replay/v1/judge/events.jsonl \
     web/public/replay/v1/judge/signals.json web/public/replay/v1/judge/ticks.json.gz \
     web/public/replay/v1/judge/
COPY relay relay

USER 65534
EXPOSE 8080
CMD ["uvicorn", "relay.app:app", "--host", "0.0.0.0", "--port", "8080"]
