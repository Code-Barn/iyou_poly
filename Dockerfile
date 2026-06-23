# Stage 1: Build
FROM python:3.13-slim AS builder
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_PREFERENCE=only-system
ENV DJANGO_SETTINGS_MODULE=config.settings
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libpq-dev gcc
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
COPY pyproject.toml .
RUN uv sync --no-dev
COPY . .
ENV POLY_DEBUG=false
ENV OIDC_RP_CLIENT_ID=builder OIDC_RP_CLIENT_SECRET=builder OIDC_RP_CALLBACK_URL=builder
RUN uv run python manage.py collectstatic --noinput

# Stage 2: Run
FROM python:3.13-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libpq5 && rm -rf /var/lib/apt/lists/*
COPY --from=builder /app /app
COPY --from=builder /app/docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh
ENV PATH="/app/.venv/bin:$PATH"
ENTRYPOINT ["/docker-entrypoint.sh"]
