# api_bulk/views.py
import json
import os
import uuid
import shutil
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, FileResponse, Http404, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.utils import timezone
from .models import DownloadTask
from .utils import Helper
from .tasks import run_download_task
utils = Helper()
root_dir = os.path.abspath(os.path.join(os.getcwd(), "..", ".."))
path_dir = os.path.abspath(os.path.join(os.getcwd(), "..", "..", "paths.json5"))

config = utils.load_json5(path_dir)
out_dir = r"C:/Users/kaustubh.keny/Projects/OFFICE PROJECTS/api-admin/output/tasks"

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



def get_task_detail(request, task_id):
    print("DEBUG: task_id =", task_id)
    task = get_object_or_404(DownloadTask, pk=task_id)
    

    # Load logs from filesystem
    log_path = os.path.join(out_dir, task.task_dir, "task.log")
    logs = []
    if os.path.exists(log_path):
        with open(log_path, "r") as f:
            logs = f.readlines()

    # Attach logs to task object
    task.logs = [line.strip() for line in logs]

    return render(request, "api_bulk/task.html", {"task": task})

def get_task_status(request, task_id):
    
    
    print("WE ARE IN STATUS")
    try:
        task = DownloadTask.objects.get(pk=task_id)
    except DownloadTask.DoesNotExist:
        return JsonResponse({"error": "Task not found"}, status=404)

    log_path = os.path.join(out_dir, task.task_dir, "task.log")
    logs = []
    if os.path.exists(log_path):
        with open(log_path, "r") as f:
            logs = f.readlines()

    return JsonResponse({
        "id": task.id,
        "name": task.name,
        "status": task.status,
        "downloaded_files": task.downloaded_files,
        "failed_files": task.failed_files,
        "total_files": task.total_files,
        "progress_percent":(task.downloaded_files / task.total_files * 100) if task.total_files else 0,
        "logs": [line.strip() for line in logs[-100:]]
    })



@csrf_exempt
@require_POST
def bulk_create(request):
    try:
        data = json.loads(request.body)

        # Generate a short unique ID
        task_id = str(uuid.uuid4())[:5]

        task = DownloadTask.objects.create(
            id=task_id,
            name=data.get("task_name"),
            owner=data.get("owner", [request.user.username]),
            created_by=request.user.username if request.user.is_authenticated else "system",
            modified_by=request.user.username if request.user.is_authenticated else "system",
            status="QUEUED",
            total_files=len(data.get("csv_file", [])),
            headers=data.get("headers", {}),
            throttle=data.get("throttle", 0),
            task_dir=f"{task_id}"
        )

        
        task_dir = os.path.join(out_dir, task.task_dir)
        os.makedirs(task_dir, exist_ok=True)
        os.makedirs(os.path.join(task_dir, "files"), exist_ok=True)
        os.makedirs(os.path.join(task_dir, "zip"), exist_ok=True)

        print(f"TASK CREATED AT: {task_dir}")
        
        # Write meta.json
        meta_path = os.path.join(task_dir, "meta.json")
        with open(meta_path, "w") as f:
            json.dump(data, f, indent=2)

        # Write initial log
        log_path = os.path.join(task_dir, "task.log")
        with open(log_path, "a") as log:
            log.write(f"[{timezone.now()}] Task created with {task.total_files} files\n")
            
         #celery   
        run_download_task.delay(task.id, out_dir)
        
        from .worker import DownloadWorker
        
        DownloadWorker(task, out_dir).run()
        
        return JsonResponse({"id": task.id, "status": task.status})

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)
    

def delete_bulk_task(request, task_id):
    
    task = get_object_or_404(DownloadTask, pk=task_id)
    task_dir = os.path.join(out_dir, task.task_dir)
    try:
        
        if not task_dir.startswith(out_dir):
            return JsonResponse({"error": "Invalid task directory"}, status=400)
        if os.path.exists(task_dir):
            shutil.rmtree(task_dir)

        print(f"Folder '{task_dir}' deleted successfully.")
    except OSError as e:
        print(f"Error: {task_dir} : {e.strerror}")
        
    task.delete()
    
    return JsonResponse({"message": f"Task {task_id} deleted successfully"})

    
    
    
    

@csrf_exempt
def browse_files(request, task_id):
    task_path = os.path.join(out_dir, task_id, "files")
    if not os.path.exists(task_path):
        raise Http404("Files not found")

    files = os.listdir(task_path)

    # Build a simple HTML response with links
    html = "<h2>Files for task {}</h2><ul>".format(task_id)
    for fname in files:
        html += f'<li><a href="/bulk/{task_id}/files/{fname}">{fname}</a></li>'
    html += "</ul>"

    return HttpResponse(html)

@csrf_exempt
def download_file(request, task_id, filename):
    file_path = os.path.join(out_dir, task_id, "files", filename)
    if not os.path.exists(file_path):
        raise Http404("File not found")
    return FileResponse(open(file_path, "rb"), as_attachment=True)

@csrf_exempt
def view_meta(request, task_id):
    meta_path = os.path.join(out_dir, task_id, "meta.json")
    if not os.path.exists(meta_path):
        raise Http404("Meta not found")
    with open(meta_path) as f:
        meta = json.load(f)
    return JsonResponse(meta)

@csrf_exempt
def browse_zip(request, task_id):
    zip_path = os.path.join(out_dir, task_id, "zip")
    if not os.path.exists(zip_path):
        raise Http404("Files not found")
    files = os.listdir(zip_path)
    html = "<h2>Zips for task {}</h2><ul>".format(task_id)
    for fname in files:
        html += f'<li><a href="/bulk/{task_id}/files/{fname}">{fname}</a></li>'
    html += "</ul>"

    return HttpResponse(html)

@csrf_exempt
def download_zip(request, task_id, zip_name):
    file_path = os.path.join(out_dir, task_id, "zip", zip_name)
    if not os.path.exists(file_path):
        raise Http404("File not found")
    return FileResponse(open(file_path, "rb"), as_attachment=True)



@csrf_exempt
def download_log(request, task_id):
    log_path = os.path.join(out_dir, task_id, "task.log")
    if not os.path.exists(log_path):
        raise Http404("Log not found")
    return FileResponse(open(log_path, "rb"), as_attachment=True)