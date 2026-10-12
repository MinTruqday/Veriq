FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DEFAULT_TIMEOUT=30 \
    PIP_RETRIES=3 \
    PYTHONPATH=/app

COPY cloud/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY cloud/src/ ./src/

RUN groupadd --gid 10001 app && useradd --uid 10001 --gid app --create-home --home-dir /home/app --shell /usr/sbin/nologin app && mkdir -p /app/storage/chunks /app/storage/tmp && chown -R app:app /app

USER 10001:10001

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=20s --start-period=30s --retries=3 CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/san-sang', timeout=15)"]

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
