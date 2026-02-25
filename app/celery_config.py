from celery.schedules import crontab
from celery import Celery


c_app = Celery(
    "celery_bot",
    include=[
        "app.crypto.tasks",
        "app.parsing.tasks",
        "app.mail.tasks"
    ]
)

c_app.config_from_object('app.config')

c_app.conf.beat_schedule = {
    'update_coin_price': {
        'task': 'app.crypto.tasks..update_coin_price',
        'schedule': 10.0
    },
    'cleanup_scraped_files': {
        'task': 'app.parsing.tasks.cleanup_old_files',
        'schedule': crontab(hour=3, minute=0)
    }
}
