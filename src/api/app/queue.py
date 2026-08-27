"""
Thin Celery client used only to enqueue work - the API process never imports
worker code directly (they're separate containers/images). Calling by task
name via send_task keeps the two services decoupled.
"""
import os
from celery import Celery

CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")

celery_client = Celery("floodrescue-client", broker=CELERY_BROKER_URL)


def enqueue_incident(incident_id: str):
    celery_client.send_task("worker.tasks.process_incident", args=[incident_id])
