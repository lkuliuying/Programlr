FROM python:3.13.15-slim-bookworm@sha256:2325bb286ec344af3e5898cc224b5844e2707ac6e26b1632516fd3edc84a5e26
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 UV_LINK_MODE=copy
ENV MYPY_CACHE_DIR=/tmp/mypy-cache
WORKDIR /app/backend
RUN pip install --no-cache-dir uv==0.12.19 && useradd --uid 1000 --create-home lab
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-managed-python
COPY ./ ./
ENV PATH="/app/backend/.venv/bin:$PATH"
USER 1000:1000
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2", "--timeout", "15", "--error-logfile", "-"]
