# api_bulk/urls.py

from django.urls import path
from .views import index, create_task, get_task_detail

urlpatterns = [
    path("", index, name="bulk_home"),
    path("create/", create_task, name="create_task"),
    path("<str:task_id>/", get_task_detail, name="task_detail"),
]
