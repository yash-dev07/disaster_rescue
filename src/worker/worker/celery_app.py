import os
from celery import Celery

CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/1")

celery_app = Celery("floodrescue", broker=CELERY_BROKER_URL, backend=CELERY_RESULT_BACKEND)
celery_app.conf.task_routes = {"worker.tasks.*": {"queue": "floodrescue"}}

# Section 5: "a synchronous worker queue (Celery/RQ + Redis) processing SOS
# events one at a time is enough" for Tier 1 - no autoscaling / GPU pool config here.
celery_app.conf.worker_concurrency = int(os.getenv("CELERY_CONCURRENCY", "2"))

import worker.tasks  # noqa: E402,F401  (registers the task with this app)
