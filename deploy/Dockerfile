FROM ghcr.io/astral-sh/uv:0.12.13-python3.12-trixie AS base

# Окружение вне /app: в dev compose монтирует туда код с хоста, и он не должен
# перекрыть зависимости.
ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_LINK_MODE=copy \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# djvutxt и djvused: текст книг DJVU, из него берём данные для ссылки на книгу
RUN apt-get update \
    && apt-get install -y --no-install-recommends djvulibre-bin \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock .python-version ./

FROM base AS prod

RUN --mount=type=cache,target=/root/.cache/uv,sharing=locked \
    uv sync --frozen --no-dev

COPY app ./app

# В dev-образе ещё ruff и mypy: make check-code запускает их в контейнере.
FROM base AS dev

RUN --mount=type=cache,target=/root/.cache/uv,sharing=locked \
    uv sync --frozen

COPY app ./app
