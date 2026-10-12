import csv
import json
import logging
import os
import time
import zipfile

import requests
from django.utils import timezone
from utils import Helper


class DownloadWorker:
    def __init__(self, task, out_dir):

        self.task = task
        self.utils = Helper()

        self.session = requests.Session()
        self.session.headers.update(task.headers or {})

        self.throttle = task.throttle or 0.4

        self.failed_requests = []

        self.task_dir = os.path.join(out_dir, task.task_dir)
        self.files_dir = os.path.join(self.task_dir, "files")
        self.zip_dir = os.path.join(self.task_dir, "zip")
        os.makedirs(self.files_dir, exist_ok=True)
        os.makedirs(self.zip_dir, exist_ok=True)

        self.log_path = os.path.join(self.task_dir, "task.log")
        self.logger = self.setup_logger(self.log_path, task)
        meta_path = os.path.join(self.task_dir, "meta.json")
        self.meta = self.utils.load_json(meta_path)

        self.csv_file = self.meta.get("csv_file", [])
        self.logger.info("Worker initialized.")

        referer_url = (task.headers or {}).get("Referer")
        if referer_url:
            try:

                resp = self.session.get(referer_url, timeout=15, verify=False)
                self.session.cookies.update(resp.cookies)
                self.logger.info(f"Cookies initialized from {referer_url}")

            except Exception as e:
                self.logger.error(f"Cookie initialization failed : {e}")

    # LOGGER

    @staticmethod
    def setup_logger(log_path, task):

        logger = logging.getLogger(f"task_{task.id}")
        logger.setLevel(logging.INFO)
        if not logger.handlers:
            handler = logging.FileHandler(log_path)
            formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        logger.propagate = False

        return logger

    # ROUTER

    def process_row(self, row):
        if self.task.api_url:
            return self.process_api(row)
        return self.process_download(row)

    # DIRECT DOWNLOAD

    def process_download(self, row):

        url = row["url"]
        fname = row["file_name"]

        try:

            resp = self.session.get(url, timeout=30, verify=self.task.verify_request)

            resp.raise_for_status()

            ext = self.detect_extension(resp)

            filepath = os.path.join(self.files_dir, f"{fname}.{ext}")

            with open(filepath, "wb") as f:
                f.write(resp.content)

            self.task.downloaded_files += 1
            self.task.save(update_fields=["downloaded_files"])
            self.logger.info(f"Downloaded {url}")
            self.check_zip_cap()

            return True

        except Exception as e:

            self.record_failure(row, e)

            return False

    # API MODE
    def process_api(self, row):
        fname = row["file_name"]
        payload = {k: v for k, v in row.items() if k != "file_name"}

        try:

            resp = self.make_api_request(payload)
            resp.raise_for_status()
            filepath = os.path.join(self.files_dir, f"{fname}.json")

            try:

                data = resp.json()
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)

            except Exception:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(resp.text)

            self.task.downloaded_files += 1
            self.task.save(update_fields=["downloaded_files"])
            self.logger.info(f"API success {fname}")
            self.check_zip_cap()
            return True

        except Exception as e:
            self.record_failure(row, e)
            return False

    # API REQUEST
    def make_api_request(self, payload):
        method = (self.task.request_type or "POST").upper()
        kwargs = {
            "timeout": 30,
            "verify": self.task.verify_request,
        }
        if method == "GET":
            return self.session.get(self.task.api_url, params=payload, **kwargs)
        kwargs["json"] = payload
        if method == "PUT":
            return self.session.put(self.task.api_url, **kwargs)
        return self.session.post(self.task.api_url, **kwargs)

    # FAILURE TRACKING
    def record_failure(self, row, error):
        self.task.failed_files += 1
        self.task.save(update_fields=["failed_files"])
        item = {"timestamp": timezone.now().isoformat(), "error": str(error), **row}
        self.failed_requests.append(item)
        self.logger.error(json.dumps(item))

    # SAVE FAILED REQUESTS
    def save_failures(self):
        if not self.failed_requests:
            return

        output = os.path.join(self.task_dir, "failed_requests.json")
        with open(output, "w", encoding="utf-8") as f:
            json.dump(self.failed_requests, f, indent=2, ensure_ascii=False)
        self.logger.info(f"Saved {len(self.failed_requests)} failed requests")

    # FILE TYPE DETECTION
    def detect_extension(self, resp):

        ctype = resp.headers.get("Content-Type", "").lower()
        if "pdf" in ctype:
            return "pdf"
        if "json" in ctype:
            return "json"
        if "jpeg" in ctype:
            return "jpg"
        if "png" in ctype:
            return "png"
        if "zip" in ctype:
            return "zip"
        if "csv" in ctype:
            return "csv"
        return "dat"

    def check_zip_cap(self, cap_mb=500):

        total_size = sum(
            os.path.getsize(os.path.join(self.files_dir, f))
            for f in os.listdir(self.files_dir)
            if os.path.isfile(os.path.join(self.files_dir, f))
        )

        if total_size < cap_mb * 1024 * 1024:
            return

        timestamp = timezone.now().strftime("%Y%m%d%H%M%S")

        zip_path = os.path.join(self.zip_dir, f"{self.task.id}_{timestamp}.zip")

        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:

            for file_name in os.listdir(self.files_dir):
                file_path = os.path.join(self.files_dir, file_name)
                if os.path.isfile(file_path):
                    zf.write(file_path, arcname=file_name)

        self.logger.info(f"Created archive: {zip_path}")

        # Optional:
        # Delete files after archiving
        # otherwise next download will
        # immediately exceed cap again

        for file_name in os.listdir(self.files_dir):
            file_path = os.path.join(self.files_dir, file_name)
            if os.path.isfile(file_path):
                os.remove(file_path)
        self.logger.info(f"Cleared files directory after archive creation")

    def run(self):
        self.logger.info("Starting worker")

        self.task.status = "TESTING"
        self.task.save(update_fields=["status"])

        if not self.run_test_batch():
            self.save_failures()

            self.task.status = "FAILED"
            self.task.save(update_fields=["status"])

            self.logger.error("Test batch failed, aborting")
            return

        self.task.downloaded_files = 0
        self.task.failed_files = 0
        self.task.status = "RUNNING"
        self.task.save(
            update_fields=[
                "downloaded_files",
                "failed_files",
                "status",
            ]
        )

        success = self.run_full_batch()

        self.save_failures()

        self.task.status = "COMPLETED" if success else "FAILED"
        self.task.save(update_fields=["status"])

        self.logger.info(
            f"Finished. Downloaded={self.task.downloaded_files}, "
            f"Failed={self.task.failed_files}"
        )

    def run_test_batch(self, sample_size=5):
        sample = self.csv_file[:sample_size]

        self.logger.info(f"Running test batch with {len(sample)} records")

        failures = 0

        for row in sample:
            if not self.process_row(row):
                failures += 1
            time.sleep(self.throttle)

        if failures:
            self.logger.error(f"Test batch failed with {failures} failures")
            return False

        self.logger.info("Test batch passed")
        return True

    def run_full_batch(self):
        total = len(self.csv_file)
        failures = 0

        self.logger.info(f"Running full batch with {total} records")
        for idx, row in enumerate(self.csv_file, start=1):

            if not self.process_row(row):
                failures += 1

            time.sleep(self.throttle)

            if idx % 10 == 0 or idx == total:
                self.logger.info(f"Progress {idx}/{total}")

        self.logger.info("Full batch completed")
        return True
