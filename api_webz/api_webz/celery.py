import os
from celery import Celery

# Set default Django settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "api_webz.settings")

# Create Celery app
app = Celery("api_webz")

# Load settings with CELERY_ prefix from Django
app.config_from_object("django.conf:settings", namespace="CELERY")

# Auto-discover tasks.py in all apps
app.autodiscover_tasks()
