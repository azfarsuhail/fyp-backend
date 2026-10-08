# GPU base by default (prod, g4dn). The offline/CPU stack overrides this with
# tensorflow/tensorflow:2.15.0 via docker-compose.offline.yml build args.
ARG BASE_IMAGE=tensorflow/tensorflow:2.15.0-gpu

# ===== BUILD STAGE =====
FROM ${BASE_IMAGE} as builder

WORKDIR /build

RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN python -m venv --system-site-packages /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Optional: install torch/torchvision (pins taken from requirements.txt) from another
# index first, e.g. https://download.pytorch.org/whl/cpu for CPU-only builds — skips
# ~2.5GB of nvidia-* CUDA wheels. 2.1.2+cpu satisfies the ==2.1.2 pins afterwards.
ARG TORCH_INDEX_URL=
RUN pip install --no-cache-dir --upgrade pip && \
    if [ -n "$TORCH_INDEX_URL" ]; then \
        pip install --no-cache-dir $(grep -E '^(torch|torchvision)==' requirements.txt | tr -d '\r') \
            --index-url "$TORCH_INDEX_URL"; \
    fi && \
    pip install --no-cache-dir -r requirements.txt

# ===== RUNTIME STAGE =====
FROM ${BASE_IMAGE} as runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH="/code" \
    HF_HOME=/tmp/huggingface

RUN groupadd -r appgroup && useradd -r -g appgroup appuser

RUN mkdir -p /tmp/huggingface && chown -R appuser:appgroup /tmp/huggingface

RUN apt-get update && apt-get install -y \
    libpq5 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

WORKDIR /code

COPY --from=builder /opt/venv /opt/venv

# Bake HuggingFace models (RAG embeddings + CLIP gatekeeper) into the image so
# the API never downloads at runtime (required for the offline setup).
# Placed before the app COPY so code edits don't re-trigger the download.
RUN USE_TF=0 python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')" && \
    USE_TF=0 python -c "from transformers import pipeline; pipeline('zero-shot-image-classification', model='openai/clip-vit-base-patch32')" && \
    chown -R appuser:appgroup /tmp/huggingface

# =====================================================================
# THE BULLETPROOF FIX: Search and Destroy the broken compiler
# 1. Finds exactly where pip installed the patched ptxas binary
# 2. Forcefully overwrites the broken one inside NVIDIA's locked folder
# =====================================================================
RUN PATCHED_PTXAS=$(find /opt/venv -name ptxas -type f | head -n 1) && \
    mkdir -p /usr/local/cuda/bin && \
    rm -f /usr/local/cuda/bin/ptxas && \
    ln -s $PATCHED_PTXAS /usr/local/cuda/bin/ptxas && \
    ln -s $PATCHED_PTXAS /usr/local/bin/ptxas

COPY --chown=appuser:appgroup app/ ./app/
COPY --chown=appuser:appgroup alembic/ ./alembic/
COPY --chown=appuser:appgroup alembic.ini .
COPY --chown=appuser:appgroup scripts/ ./scripts/
COPY --chown=appuser:appgroup migrations/ ./migrations/
COPY --chown=appuser:appgroup static/ ./static/
COPY --chown=appuser:appgroup download/ ./download/

RUN chown -R appuser:appgroup /code

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=180s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=5)" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]