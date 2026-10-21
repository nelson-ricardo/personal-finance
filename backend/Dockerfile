# syntax=docker/dockerfile:1
FROM python:3.13-slim AS base

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy

# Install essential runtime tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install uv from official binary
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy dependency definition files
COPY pyproject.toml uv.lock README.md ./

# --- Development Target ---
FROM base AS dev
RUN uv sync --frozen --no-install-project
ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8000
CMD ["uv", "run", "python", "main.py", "--dev"]

# --- Production Target ---
FROM base AS prod
COPY alembic.ini ./
COPY alembic ./alembic
COPY src ./src
COPY main.py ./
RUN uv sync --frozen --no-dev
ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8000
CMD ["uv", "run", "python", "main.py"]
