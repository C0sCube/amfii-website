# api_bulk/urls.py

from django.urls import path
from .views import index, create_task

urlpatterns = [
    path("", index, name="bulk_home"),
    path("create/", create_task, name="create_task"),
]
