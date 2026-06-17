FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml poetry.lock* ./

RUN pip install --no-cache-dir poetry && \
    poetry config virtualenvs.create false && \
    poetry install --no-root --no-interaction --no-ansi

COPY src/ ./src/
COPY gunicorn.conf.py ./
COPY .env ./.env

ENV PYTHONUNBUFFERED=1

EXPOSE 5000

CMD ["gunicorn", "-c", "gunicorn.conf.py", "app:app"]