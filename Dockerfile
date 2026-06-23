FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY pyproject.toml uv.lock README.md LICENSE ./
COPY agent ./agent
COPY common ./common
COPY mining_news_mcp ./mining_news_mcp
COPY mineral_pdf_mcp ./mineral_pdf_mcp
COPY lme_price_mcp ./lme_price_mcp
RUN pip install --no-cache-dir uv==0.11.23 \
    && uv sync --locked --no-dev

ENTRYPOINT ["/app/.venv/bin/python", "-m", "agent"]
CMD ["给我生成一份关于 Pilbara 锂矿的今日简报"]
