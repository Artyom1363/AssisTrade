FROM python:3.10-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
WORKDIR /agents

COPY . /agents/
RUN uv sync --frozen --no-install-project
ADD . /agents


HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/healthcheck || exit 1
CMD ["uv","run", "main.py"]
