FROM node:22-bookworm-slim AS node_tools

RUN npm config set fetch-retries 5 \
    && npm config set fetch-retry-mintimeout 20000 \
    && npm config set fetch-retry-maxtimeout 120000 \
    && npm install --global newman@6.2.1 @playwright/test@1.55.0 \
    && npm cache clean --force

FROM python:3.12-slim-bookworm

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DEFAULT_TIMEOUT=120 \
    PIP_RETRIES=10 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    NODE_PATH=/usr/local/lib/node_modules

COPY worker/requirements.txt .

COPY --from=node_tools /usr/local/bin/node /usr/local/bin/node
COPY --from=node_tools /usr/local/lib/node_modules /usr/local/lib/node_modules

RUN pip install --no-cache-dir -r requirements.txt \
    && ln -s /usr/local/lib/node_modules/newman/bin/newman.js /usr/local/bin/newman \
    && ln -s /usr/local/lib/node_modules/@playwright/test/cli.js /usr/local/bin/playwright \
    && playwright install-deps chromium \
    && playwright install chromium \
    && rm -rf /var/lib/apt/lists/*

COPY worker/src/ ./src/

RUN groupadd --gid 10001 appuser \
    && useradd --uid 10001 --gid appuser -m -s /usr/sbin/nologin appuser \
    && chown -R appuser:appuser /app

USER 10001:10001

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=20s --start-period=10s --retries=3 CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/san-sang', timeout=15)"]

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
