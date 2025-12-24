from celery import Celery
from app.core.config import settings


celery = Celery(
    "postika",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

# Ensure tasks are discovered correctly under app/
celery.autodiscover_tasks(["app.tasks"])

# Optional but recommended defaults
celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

