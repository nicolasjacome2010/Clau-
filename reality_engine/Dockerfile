# syntax=docker/dockerfile:1
FROM python:3.11-slim AS builder

WORKDIR /build
RUN pip install --no-cache-dir --upgrade pip

COPY pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir --prefix=/install .

FROM python:3.11-slim AS runtime

RUN useradd --create-home --uid 1000 varos
WORKDIR /app

COPY --from=builder /install /usr/local
COPY src ./src

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

USER varos
EXPOSE 8100

HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8100/healthz')" || exit 1

CMD ["uvicorn", "reality_engine.main:app", "--host", "0.0.0.0", "--port", "8100"]
