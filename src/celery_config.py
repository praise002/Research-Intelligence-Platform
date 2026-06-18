from config import settings
from celery import Celery
# from celery.schedules import crontab

celery_app = Celery(
    "tasks",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    broker_connection_retry_on_startup=True,
    broker_connection_max_retries=10,
    result_backend_max_retries=10,
)

celery_app.conf.beat_schedule = {
#    "run-retention-job-daily": {
#         "task": "src.tasks.retention_task",
#         # Runs at midnight UTC every day
#         "schedule": crontab(hour=0, minute=0),
#     },
}