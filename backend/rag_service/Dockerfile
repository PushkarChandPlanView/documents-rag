FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    g++ \
    cmake \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

ENV TIKTOKEN_CACHE_DIR=/app/.tiktoken_cache
RUN mkdir -p /app/.tiktoken_cache && \
    python -c "import tiktoken; tiktoken.get_encoding('cl100k_base')"

COPY . .

RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "2"]
