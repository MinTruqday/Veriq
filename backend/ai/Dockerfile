FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DEFAULT_TIMEOUT=120 \
    PIP_RETRIES=10 \
    UV_HTTP_TIMEOUT=120 \
    UV_HTTP_RETRIES=10 \
    HF_HOME=/home/appuser/.cache/huggingface \
    TMPDIR=/home/appuser/.cache/tmp

WORKDIR /app

COPY ai/requirements.txt .

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    libgl1 \
    libglib2.0-0 \
    tesseract-ocr \
    tesseract-ocr-vie \
    && mkdir -p /home/appuser/.cache/tmp \
    && pip install --no-cache-dir uv==0.12.3 \
    && uv pip install --system --no-cache \
        --index-strategy unsafe-best-match -r requirements.txt \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/*

RUN groupadd --gid 10001 appuser && useradd --uid 10001 --gid appuser -m -s /bin/bash appuser
RUN mkdir -p /home/appuser/.cache/huggingface /home/appuser/.cache/tmp && chown -R appuser:appuser /home/appuser/.cache

COPY --chown=appuser:appuser ai/src/ ./src/

USER 10001:10001
HEALTHCHECK --interval=30s --timeout=20s --start-period=90s --retries=3 CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/san-sang', timeout=15)"]
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
