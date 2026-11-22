FROM python:3.13-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN groupadd --system app && useradd --system --gid app --no-create-home --shell /usr/sbin/nologin app

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt


FROM base AS test

RUN pip install httpx==0.28.1

COPY main.py main_secure.py test_versions.py init.sql ./
COPY instance/storage/ ./instance/storage/

USER app

CMD ["python", "test_versions.py"]


FROM base AS production

COPY main_secure.py init.sql ./
COPY instance/storage/ ./instance/storage/

RUN python -c "import sqlite3; sqlite3.connect('instance/workspace.db').executescript(open('init.sql').read())" \
    && rm init.sql \
    && chown -R app:app /app/instance \
    && chmod 700 /app/instance /app/instance/storage \
    && chmod 600 /app/instance/workspace.db /app/instance/storage/*

USER app

EXPOSE 5000

CMD ["uvicorn", "main_secure:app", "--host", "0.0.0.0", "--port", "5000", "--no-server-header"]