#!/bin/sh

set e

echo "Running migrations"
python -m alembic upgrade head

echo "Start web server"
uvicorn app.main:app --host 0.0.0.0 --port 8000

celery -A app worker --loglevel=info --pool=solo --concurrency=1 &