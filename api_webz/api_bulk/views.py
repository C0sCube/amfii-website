# api_bulk/views.py
import json

from django.shortcuts import render
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

    return render(request, "api_bulk/index.html", {"tasks": tasks})


def create_task(request):

    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    data = json.loads(request.body)

    print(data)

    return JsonResponse({"success": True})
