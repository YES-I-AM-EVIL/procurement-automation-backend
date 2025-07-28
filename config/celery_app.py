import os
import celery

Celery = celery.Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
app = Celery('procurement_automation')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()