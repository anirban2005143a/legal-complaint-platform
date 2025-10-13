# myproject/celery.py
import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'website.settings')  # replace with your project name

app = Celery('website')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
