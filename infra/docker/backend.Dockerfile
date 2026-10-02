FROM node:24.21.0-bookworm-slim@sha256:0e0ff40c39bc087845bfb27465a0df4ea419520094bc35842ff83dd8cbe6f9b6 AS analyzer
WORKDIR /app/analyzers/typescript
COPY analyzers/typescript/package.json analyzers/typescript/package-lock.json ./
RUN npm ci --ignore-scripts --registry=https://registry.npmjs.org
COPY analyzers/typescript/tsconfig.json ./
COPY analyzers/typescript/src ./src
RUN npm run build && npm prune --omit=dev --ignore-scripts

FROM python:3.13.15-slim-bookworm@sha256:2325bb286ec344af3e5898cc224b5844e2707ac6e26b1632516fd3edc84a5e26
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 UV_LINK_MODE=copy
ENV MYPY_CACHE_DIR=/tmp/mypy-cache
WORKDIR /app/backend
RUN pip install --no-cache-dir uv==0.12.19 && useradd --uid 1000 --create-home lab
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --locked --no-managed-python
COPY --from=analyzer /usr/local/bin/node /usr/local/bin/node
COPY --from=analyzer /app/analyzers/typescript /app/analyzers/typescript
COPY contracts/typescript-analysis.schema.json /app/contracts/typescript-analysis.schema.json
RUN node --version
COPY backend/ ./
COPY content/ /app/content/
COPY examples/system-labs/ /app/examples/system-labs/
ENV PATH="/app/backend/.venv/bin:$PATH"
USER 1000:1000
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2", "--timeout", "15", "--error-logfile", "-"]
