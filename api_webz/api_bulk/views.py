# api_bulk/views.py
import json
import os
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from .models import DownloadTask

# request
# │
# ├── request.method
# ├── request.GET
# ├── request.POST
# ├── request.FILES
# ├── request.user
# ├── request.headers
# └── request.path


def index(request):

    tasks = DownloadTask.objects.all()

    return render(
        request,
        "api_bulk/index.html",
        {"username": request.session.get("username"), "tasks": tasks},
    )


def create_task(request):

    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    data = json.loads(request.body)

    print(data)

    return JsonResponse({"success": True})

def get_task_detail(request, task_id):
    print("DEBUG: task_id =", task_id)
    task = get_object_or_404(DownloadTask, pk=task_id)
    

    # Load logs from filesystem
    log_path = os.path.join(task.task_dir, "task.log")
    logs = []
    if os.path.exists(log_path):
        print(f"THE PATH EXISTS")
        with open(log_path, "r") as f:
            logs = f.readlines()
    else:
        print("THE TASK DOESN'T EXIST")
    # Attach logs to task object
    task.logs = [line.strip() for line in logs]

    return render(request, "api_bulk/task.html", {"task": task})