# myapp/tasks.py

from celery import shared_task
import time

@shared_task
def long_running_task():
    # Simulate long task
    time.sleep(60)
    return "Finished long task"
