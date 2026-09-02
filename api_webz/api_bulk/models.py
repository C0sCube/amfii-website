from django.db import models


class DownloadTask(models.Model):

    # Identity
    id = models.CharField(max_length=10, primary_key=True)
    name = models.CharField(max_length=200)

    # Ownership
    owner = models.JSONField(default=list)
    created_by = models.CharField(max_length=50)
    modified_by = models.CharField(max_length=50)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # Task state
    status = models.CharField(max_length=20, default="QUEUED")

    # Progress
    total_files = models.IntegerField(default=0)
    downloaded_files = models.IntegerField(default=0)
    failed_files = models.IntegerField(default=0)

    # Configuration
    headers = models.JSONField(default=dict)
    throttle = models.IntegerField(default=0)

    # Filesystem
    task_dir = models.CharField(max_length=500)
