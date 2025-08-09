FROM python:3.13.1-slim-bookworm

ENV PYTHONUNBUFFERED=1
ENV UV_SYSTEM_PYTHON=1

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Cache dependencies
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Copy source
COPY cast /app/cast

# Create non-root user
RUN useradd -m -u 1000 cast && \
    chown -R cast:cast /app

USER cast

# Default command
ENTRYPOINT ["/app/.venv/bin/cast"]
CMD ["--help"]