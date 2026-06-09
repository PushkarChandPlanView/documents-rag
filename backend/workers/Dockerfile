FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    libgl1 \
    curl \
    build-essential \
    g++ \
    cmake \
    && rm -rf /var/lib/apt/lists/*

# Resolve tessdata path at build time and bake it in as an env var
RUN TESSDATA=$(find /usr/share/tesseract-ocr -name "eng.traineddata" -exec dirname {} \; | head -1) && \
    echo "TESSDATA_PREFIX=$TESSDATA" && \
    echo "TESSDATA_PREFIX=$TESSDATA" >> /etc/environment
ENV TESSDATA_PREFIX=/usr/share/tesseract-ocr/5/tessdata

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download tiktoken encoding so workers have no outbound network dependency at runtime
ENV TIKTOKEN_CACHE_DIR=/app/.tiktoken_cache
RUN mkdir -p /app/.tiktoken_cache && \
    python -c "import tiktoken; tiktoken.get_encoding('cl100k_base')" || true

COPY . .

RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

CMD ["python", "-m", "worker_runner"]
