# api_bulk/urls.py

from django.urls import path
from .views import *

urlpatterns = [
    path("", index, name="bulk_home"),
    path('bulk/', index, name="bulk"),
    path("create/", bulk_create, name="create_task"),
    path("<str:task_id>/", get_task_detail, name="task_detail"),
    path("<str:task_id>/status/", get_task_status, name="task_status"),
    path("<str:task_id>/files/", browse_files, name="browse_files"),
    path("<str:task_id>/files/<str:filename>", download_file, name="download_file"),
    path("<str:task_id>/meta.json", view_meta, name="view_meta"),
    path("<str:task_id>/zip/", browse_zip, name="browse_zip"),
    path("<str:task_id>/zip/<str:zip_name>", download_zip, name="download_zip"),
    path("<str:task_id>/task.log", download_log, name="download_log"),
    path("<str:task_id>/delete/", delete_bulk_task, name="delete_task")
]
