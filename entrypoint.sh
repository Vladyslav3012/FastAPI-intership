#!/bin/sh

set e

echo "Running migrations"
python -m alembic upgrade head

celery -A app.celery_config worker --loglevel=info --pool=solo --concurrency=1 &

echo "Start web server"
exec uvicorn app.main:app --host 0.0.0.0 --port 8000