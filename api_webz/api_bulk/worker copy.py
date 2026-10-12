import os, time, requests, zipfile
import logging
from django.utils import timezone
from utils import Helper

class DownloadWorker:
    def __init__(self, task, out_dir:str):
        self.task = task
        self.utils = Helper()
        self.session = requests.Session()
        self.session.headers.update(task.headers or {})
        self.throttle = task.throttle or 0
        self.log_path = os.path.join(out_dir,task.task_dir, "task.log")
        self.logger = DownloadWorker.setup_logger(self.log_path, task)
        self.task_dir = os.path.join(out_dir,task.task_dir)
        self.files_dir = os.path.join(self.task_dir, "files")
        self.zip_dir = os.path.join(self.task_dir, "zip")
        os.makedirs(self.files_dir, exist_ok=True)
        os.makedirs(self.zip_dir, exist_ok=True)
        
        self.meta_dir = os.path.join(self.task_dir, "meta.json")
        self.meta = self.utils.load_json(self.meta_dir)
        self.csv_file = self.meta.get("csv_file",[])
        self.logger.info("Folder - files & zip created.")
        
        # Initialize cookies using Referer header if present
        referer_url = task.headers.get("Referer")
        if referer_url:
            try:
                resp = self.session.get(referer_url, timeout=15, verify=False)
                resp.raise_for_status()
                self.session.cookies.update(resp.cookies)
                self.logger.info(f"Initialized with cookies from {referer_url}")
            except Exception as e:
                self.logger.error(f"Failed to initialize from {referer_url}: {e}")
        else:
            self.logger.info("No Referer header provided, session initialized without cookies.")


    @staticmethod
    def setup_logger(log_dir, task):
        logger = logging.getLogger(task.id)
        logger.setLevel(logging.INFO)

        # Avoid duplicate handlers
        if not logger.handlers:
            fh = logging.FileHandler(log_dir)
            formatter = logging.Formatter(
                "%(asctime)s [%(levelname)s] %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            )
            fh.setFormatter(formatter)
            logger.addHandler(fh)

        # Prevent logs from propagating to root logger
        logger.propagate = False

        return logger

    
    def download_file(self, row):
        url = row["url"]
        fname = row["file_name"]
        try:
            resp = self.session.get(url, timeout=30, verify=False)
            resp.raise_for_status()
            ext = self.detect_extension(resp)
            filepath = os.path.join(self.files_dir, f"{fname}.{ext}")
            with open(filepath, "wb") as f:
                f.write(resp.content)
            self.task.downloaded_files += 1
            self.task.save(update_fields=["downloaded_files"])
            self.logger.info(f"Downloaded {url} -> {filepath}")
            self.check_zip_cap()
            return True
        except Exception as e:
            self.task.failed_files += 1
            self.task.save(update_fields=["failed_files"])
            self.logger.error(f"Failed {url}: {e}")
            return False


    def detect_extension(self, resp):
        ctype = resp.headers.get("Content-Type","")
        if "pdf" in ctype: return "pdf"
        if "json" in ctype: return "json"
        return "dat"

    def check_zip_cap(self, cap_mb=500):
        total_size = sum(os.path.getsize(os.path.join(self.files_dir,f))
                         for f in os.listdir(self.files_dir))
        if total_size > cap_mb*1024*1024:
            zipname = os.path.join(self.zip_dir,
                                   f"{self.task.id}_{timezone.now().strftime('%Y%m%d%H%M%S')}.zip")
            with zipfile.ZipFile(zipname, "w") as zf:
                for f in os.listdir(self.files_dir):
                    zf.write(os.path.join(self.files_dir,f), arcname=f)
            self.log(f"Created zip archive {zipname}")
            
    def run(self):
        """Main handler: initialize, run test, then full if test passes."""
        self.logger.info("Starting handler")

        # Run test batch
        test_success = self.run_test_batch()

        self.task.downloaded_files = 0
        self.task.status = "RUNNING"
        self.task.save(update_fields=["status","downloaded_files"])

        if not test_success:
            self.logger.error("Test batch failed — aborting full batch.")
            self.task.status = "FAILED"
            self.task.save(update_fields=["status"])
            return

        # Run full batch only if test passed
        self.logger.info("Test batch passed — proceeding to full batch.")
        self.run_full_batch()
        self.task.status = "COMPLETED"
        self.task.save(update_fields=["status"])
        self.logger.info("Handler finished successfully")

    def run_test_batch(self, sample_size=5):
        sample = self.csv_file[:sample_size]
        self.logger.info(f"Running test batch with {len(sample)} files")

        failures = 0
        for row in sample:
            ok = self.download_file(row)
            if not ok:
                failures += 1
            time.sleep(self.throttle)

        if failures > 0:
            self.logger.error(f"Test batch had {failures} failures")
            return False
        self.logger.info("Test batch succeeded")
        return True

    def run_full_batch(self, fail_threshold=10):
        """
        Run the full batch of downloads after test batch passes.
        fail_threshold: maximum allowed failures before aborting.
        """
        self.logger.info("Running full batch")

        failures = 0
        total = len(self.csv_file)

        for idx, row in enumerate(self.csv_file, start=1):
            ok = self.download_file(row)
            if not ok:
                failures += 1
                if failures >= fail_threshold:
                    self.logger.error(
                        f"Aborting full batch: {failures} failures reached (threshold {fail_threshold})"
                    )
                    self.task.status = "FAILED"
                    self.task.save(update_fields=["status"])
                    return False

            # Throttle between requests
            time.sleep(self.throttle)

            # Progress logging
            if idx % 10 == 0 or idx == total:
                self.logger.info(f"Progress: {idx}/{total} files processed")

        self.logger.info("Full batch completed successfully")
        return True


