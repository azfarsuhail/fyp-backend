# ===== BUILD STAGE =====
FROM tensorflow/tensorflow:2.15.0-gpu as builder

WORKDIR /build

RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN python -m venv --system-site-packages /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ===== RUNTIME STAGE =====
FROM tensorflow/tensorflow:2.15.0-gpu as runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH="/code"

RUN groupadd -r appgroup && useradd -r -g appgroup appuser

RUN apt-get update && apt-get install -y \
    libpq5 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

WORKDIR /code

COPY --from=builder /opt/venv /opt/venv

COPY --chown=appuser:appgroup app/ ./app/
COPY --chown=appuser:appgroup alembic/ ./alembic/
COPY --chown=appuser:appgroup alembic.ini .
COPY --chown=appuser:appgroup scripts/ ./scripts/
COPY --chown=appuser:appgroup migrations/ ./migrations/
COPY --chown=appuser:appgroup static/ ./static/
COPY --chown=appuser:appgroup ml_assets/ ./ml_assets/
COPY --chown=appuser:appgroup download/ ./download/


RUN chown -R appuser:appgroup /code

USER appuser

EXPOSE 8000

# Updated to use urllib.request to avoid dependency issues
HEALTHCHECK --interval=30s --timeout=10s --start-period=180s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=5)" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]