from celery import shared_task
from .models import DownloadTask
from .worker import DownloadWorker  # if you put your class in worker.py
import logging

logger = logging.getLogger(__name__)

@shared_task
def run_download_task(task_id, out_dir):
    try:
        print(f"DEBUG: run_download_task called with {task_id}, {out_dir}")
        task = DownloadTask.objects.get(id=task_id)
        # worker = DownloadWorker(task,out_dir)
        # worker.run()
        return DownloadWorker(task, out_dir).run()
    except Exception as e:
        import traceback
        # Log the error with task context
        logger.error(f"Task {task_id} failed: {e}", exc_info=True)
        print(f"Task {task_id} failed: {e}")
        traceback.print_exc()
        # Optionally update task status in DB
        try:
            task.status = "FAILED"
            task.save(update_fields=["status"])
        except Exception:
            pass
        # Return error info so you can inspect it later
        return {"error": str(e)}
