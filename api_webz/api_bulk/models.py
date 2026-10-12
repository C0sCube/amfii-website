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
    api_url = models.CharField(max_length=300, default="")
    site_url = models.CharField(max_length=300,default="") 
    headers = models.JSONField(default=dict)
    paginationStirng = models.CharField(max_length=100, default="")
    expectedData = models.JSONField(default=dict)
    throttle = models.IntegerField(default=0)
    verify_request = models.BooleanField(default=False)
    request_type = models.CharField(max_length=10, default="GET")
    file_type = models.CharField(
        max_length=20,
        default="",
        blank=True
    )
        # Filesystem
    task_dir = models.CharField(max_length=500)
