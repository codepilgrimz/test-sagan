FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p data
ENV DATABASE_PATH=/app/data/portal.db
ENV PORT=8000

EXPOSE 8000
# Shell form so $PORT expands when set by the host (e.g., Railway); falls back to 8000.
CMD gunicorn -b 0.0.0.0:${PORT:-8000} app:app
