FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY requirements.lock .
RUN pip install --require-hashes -r requirements.lock \
    && groupadd --gid 10001 claims \
    && useradd --uid 10001 --gid claims --no-create-home claims \
    && mkdir /app/data \
    && chown claims:claims /app/data
COPY --chown=claims:claims . .
USER 10001:10001
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
