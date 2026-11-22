FROM ghcr.io/astral-sh/uv:0.13.7 AS uv
FROM python:3.14-slim
COPY --from=uv /uv /usr/local/bin/uv
ENV UV_PROJECT_ENVIRONMENT=/opt/venv UV_PYTHON_DOWNLOADS=never \
    PYTHONDONTWRITEBYTECODE=1 WHATIF_MCP_DATA=/var/lib/whatif-mcp
WORKDIR /app/mcp
COPY mcp/pyproject.toml mcp/uv.lock ./
RUN uv sync --locked --no-dev --no-cache
COPY mcp/whatif_mcp ./whatif_mcp
COPY backend/servidor /app/backend/servidor
COPY backend/scripts /app/backend/scripts
COPY backend/contexto /app/backend/contexto
COPY backend/data/agentes /app/backend/data/agentes
COPY backend/data/pruebas/poblacion/al_azar_2000.jsonl /app/backend/data/pruebas/poblacion/
RUN install -d -m 0700 -o 10001 -g 10001 /var/lib/whatif-mcp
USER 10001:10001
HEALTHCHECK --interval=5s --timeout=2s --start-period=15s --retries=5 \
    CMD ["/opt/venv/bin/python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8788/healthz', timeout=1).close()"]
CMD ["/opt/venv/bin/python", "-m", "whatif_mcp"]
