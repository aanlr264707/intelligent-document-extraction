from celery import Celery
import os
from dotenv import load_dotenv

load_dotenv()

def make_celery(app_name=__name__):
    redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    
    celery = Celery(
        app_name,
        broker=redis_url,
        backend=redis_url,
        include=['app.tasks']
    )
    
    celery.conf.update(
        task_serializer='json',
        accept_content=['json'],
        result_serializer='json',
        timezone='UTC',
        enable_utc=True,
        task_track_started=True,
        task_time_limit=30 * 60,
        task_soft_time_limit=25 * 60,
        worker_prefetch_multiplier=1,
        worker_max_tasks_per_child=1000,
    )
    
    return celery

celery = make_celery()
