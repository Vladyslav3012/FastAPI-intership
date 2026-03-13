#!/bin/sh

set e

echo "Running migrations"
python -m alembic upgrade head

if [ "$RENDER" = "true" ]; then
     celery -A app.celery_config.c_app worker --loglevel=info --pool=solo --concurrency=1 &

     celery -A app.celery_config.c_app beat -l info &
fi

echo "Start web server"
exec uvicorn app.main:app --host 0.0.0.0 --port 8000