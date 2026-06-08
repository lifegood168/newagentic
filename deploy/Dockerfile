FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

FROM base AS deps
RUN pip install --no-cache-dir uv
COPY pyproject.toml ./
RUN uv pip install --system --no-cache .

FROM base AS runtime
COPY --from=deps /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=deps /usr/local/bin /usr/local/bin
COPY app ./app
COPY agents ./agents

RUN mkdir -p /app/data && chmod 755 /app/data

EXPOSE 8000
STOPSIGNAL SIGTERM

CMD ["uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
