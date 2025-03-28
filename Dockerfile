# syntax=docker/dockerfile:1

FROM python:3.10-alpine AS base

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

FROM base AS builder

WORKDIR /app

COPY --link requirements.txt ./
RUN --mount=type=cache,target=/root/.cache/pip \
    python -m venv .venv && \
    .venv/bin/pip install --no-cache-dir --compile -r requirements.txt

FROM base AS final

WORKDIR /app

COPY --link --from=builder /app/.venv /app/.venv
COPY --link app.py ./
COPY --link templates ./templates

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8080

CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "1", "app:app"]