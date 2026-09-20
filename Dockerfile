# Stage 1: Dependency builder and model caching
FROM python:3.11-slim AS builder

WORKDIR /build

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FASTEMBED_CACHE_PATH=/app/model_cache \
    PYTHONPATH=/install/lib/python3.11/site-packages

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Pre-download ONNX weights using escaped multi-line syntax
RUN python3 -c "\
import os; \
from fastembed import TextEmbedding; \
cache = os.environ.get('FASTEMBED_CACHE_PATH', '/app/model_cache'); \
print(f'Caching FastEmbed model to {cache}...'); \
model = TextEmbedding(cache_dir=cache); \
list(model.embed(['warmup'])); \
print('Model caching complete.')"

# Stage 2: Minimal runtime image
FROM python:3.11-slim AS runtime

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FASTEMBED_CACHE_PATH=/app/model_cache \
    PYTHONPATH=/app

# Copy site-packages and CLI binaries
COPY --from=builder /install /usr/local

# Copy cached ONNX weights
COPY --from=builder /app/model_cache /app/model_cache

# Copy application code
COPY app/ /app/app/

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
