import os, re, json, string, shutil, json5
from datetime import datetime
from collections import defaultdict
from typing import List
import time
from datetime import timedelta, datetime

class Helper:
    def __init__(self):
        pass
    
    @staticmethod
    def delete_all_files(folder_path):
        for filename in os.listdir(folder_path):
            file_path = os.path.join(folder_path, filename)
            if os.path.isfile(file_path):
                try:
                    os.remove(file_path)
                except Exception as e:
                    print(f"Failed to delete {file_path}: {e}")


    
    @staticmethod
    def clear_folder(folder_path):
        """Delete all files (not subfolders) inside the given folder."""

        deleted = 0
        for filename in os.listdir(folder_path):
            file_path = os.path.join(folder_path, filename)
            if os.path.isfile(file_path):
                try:
                    os.remove(file_path)
                    deleted += 1
                except Exception:
                    raise 
        print(f"Deleted {deleted} files from {folder_path}")
        
    @staticmethod
    def delete_files(data):
        """Delete all files (not subfolders) inside the given folder."""
    
        if isinstance(data, dict):
            file_paths = list(data.values())
        elif isinstance(data, list):
            file_paths = data
        elif isinstance(data, str):
            file_paths = [data]
        else:
            return

        for filepath in file_paths:
            if os.path.isfile(filepath):
                try:
                    os.remove(filepath)
                except Exception:
                    raise

    @staticmethod
    def archive_files(dest_folder: str, file_paths:list):
        """Copy one or more files to a destination folder (e.g., processed/ or failed/)."""

        if not os.path.exists(dest_folder):
            os.makedirs(dest_folder, exist_ok=True)

        copied = 0
        for path in file_paths:
            if not os.path.isfile(path):
                continue
            try:
                file_name = os.path.basename(path)
                dest_path = os.path.join(dest_folder, file_name)
                shutil.copy2(path, dest_path)
                copied += 1
            except Exception:
                raise
        print(f"Archived {copied} file(s) to {dest_folder}")


    @staticmethod
    def archive_and_delete_files(dest_folder: str, file_paths:list):
        """Move one or more files to a destination folder."""

        if not os.path.exists(dest_folder):
            os.makedirs(dest_folder, exist_ok=True)

        moved = 0
        for path in file_paths:
            if not os.path.isfile(path):
                continue
            try:
                file_name = os.path.basename(path)
                dest_path = os.path.join(dest_folder, file_name)
                shutil.move(path, dest_path)  # atomic move
                moved += 1
            except Exception:
                raise
        print(f"Archived {moved} file(s) to {dest_folder}")


    #JSON UN/LOAD
    @staticmethod
    def create_dir(base_path, *folders):
        dir_path = os.path.join(base_path, *folders)
        os.makedirs(dir_path, exist_ok=True)
        return dir_path
    
    @staticmethod
    def save_json(data: dict, path: str, indent: int = 2):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=indent)

    @staticmethod
    def load_json(file_path: str):
        if not os.path.exists(file_path):
            return
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
        
    @staticmethod
    def save_json5(data: dict, path: str, indent: int = 2):
        with open(path, "w", encoding="utf-8") as f:
            json5.dump(data, f, indent=indent)

    @staticmethod
    def load_json5(file_path: str):
        if not os.path.exists(file_path):
            return
        with open(file_path, "r", encoding="utf-8") as f:
            return json5.load(f)
        
    @staticmethod
    def load_json_as_string(path: str, indent: int = None) -> str:
        with open(path, "r", encoding="utf-8") as f:
            return json.dumps(json.load(f), indent=indent, ensure_ascii=False)

    @staticmethod
    def load_json5_as_string(path: str, indent: int = None) -> str:
        with open(path, "r", encoding="utf-8") as f:
            return json5.dumps(json5.load(f), indent=indent)

    
    #WRITE TEXT
    @staticmethod
    def save_text(data,path:str):
        if not data:
            print("Empty Data")
            return
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'a', encoding='utf-8') as f:
            if isinstance(data,dict):
                f.writelines(f"{k}:{v}\n" for k,v in data.items())
            elif isinstance(data,list):
                f.writelines(f"{k}\n" for k in data)
            elif isinstance(data,str):
                f.writelines(data)
            else: print("Invalid type")
           
    def debug_save(pdf_bytes: bytes, filename="debug.pdf"):
        """Save in-memory PDF bytes to disk for debugging purposes."""
        with open(filename, "wb") as f:
            f.write(pdf_bytes)
        print(f"[debug] PDF saved to {filename}")
    
    def _clean_leading_noise(self,text: str) -> str:
        if not isinstance(text,str):
            return text
        return re.sub(r'^[\s\n\r\t\\:;\-–—•|]+', '', text).strip()
    
    def _normalize_key(self,text: str) -> str:
        if not isinstance(text,str):
            return text
        text = re.sub(r"[^\w\s\.]", "", text)
        text = re.sub(r"\s+", "_", text)
        return text.strip().lower()
    
    def _normalize_key_to_alnum_underscore(self, text: str) -> str:
        if not isinstance(text, str):
            return text
        text = text.strip().lower()
        text = re.sub(r"[^\w]", "_", text)
        text = re.sub(r"__+", "_", text)
        return text.strip("_")

    def _remove_duplicates(self,text):
        if not text:
            return text
        seen = []
        text = text.split(" ")
        for word in text:
            word = word.lower().strip()
            if word not in seen:
                seen.append(word)
        return " ".join(seen)

    #match type
    def is_numeric(self,text):
        return bool(re.fullmatch(r'[+-]?(\d+(\.\d*)?|\.\d+)', text))

    def is_alphanumeric(self,text):
        return bool(re.fullmatch(r'[A-Za-z0-9]+', text))

    def is_alpha(self,text):
        return bool(re.fullmatch(r'[A-Za-z]+', text))
        
    def _remove_non_word_space_chars(self,text:str)->str:
        if not isinstance(text,str):
            return text
        text = re.sub("[^\\w\\s]", "", text).strip()
        return text
    
    def _normalize_whitespace(self,text:str)->str:
        if not isinstance(text,str):
            return text
        return re.sub(r"\s+", " ", text).strip()
    
    def _normalize_date(self,text:str)->str:
        if not isinstance(text,str):
            return text
        text = re.sub(r"[^A-Za-z0-9\s\.\/\,\-\\]+"," ",text).strip()
        return self._normalize_whitespace(text)
    
    def _normalize_alphanumeric(self, text: str) -> str:
        if not isinstance(text,str):
            return text
        text = re.sub(r"[^a-zA-Z0-9]+", " ", str(text))
        return re.sub(r"\s+", " ", text).strip().lower()
    
    def _normalize_alpha(self, text: str) -> str:
        if not isinstance(text,str):
            return text
        text = re.sub(r"[^a-zA-Z]+", " ", str(text))
        return re.sub(r"\s+", " ", text).strip().lower()

    def _normalize_numeric(self, text: str) -> str:
        if not isinstance(text,str):
            return text
        text = re.sub(r"[^0-9\.]+", " ", str(text))
        return re.sub(r"\s+", " ", text).strip().lower()
    
    
    def scheduler_loop(self,logger, run_fn, sch_days:list, sch_time:list):
        """
        Wraps the main() scraper function to run at specific times (HHMM format)
        and only on specified weekdays. 
        times = ["0800", "1240", "1530"] run_days = ["mon", "tue", "wed", "thu", "fri"]
        
        """
        while True:
            now = datetime.now()
            weekday_str = now.strftime("%a").lower()

            # Skip non-run days (like weekends)
            if weekday_str not in sch_days:
                logger.info(f"Skipping today ({weekday_str.upper()}) — not in run days.")
                tomorrow = datetime.combine(now.date() + timedelta(days=1), datetime.min.time())
                wait_seconds = (tomorrow - now).total_seconds()
                time.sleep(wait_seconds)
                continue  # restart loop

            # --- Determine next scheduled run time ---
            today_times = [datetime.strptime(t, "%H%M").time() for t in sch_time]
            future_runs = [datetime.combine(now.date(), t) for t in today_times if datetime.combine(now.date(), t) > now]

            if future_runs:
                next_run = future_runs[0]
            else:
                # All times passed — find next valid run day
                next_day = now.date() + timedelta(days=1)
                while next_day.strftime("%a").lower() not in sch_days:
                    next_day += timedelta(days=1)
                next_run = datetime.combine(next_day, today_times[0])

            wait_seconds = (next_run - now).total_seconds()
            logger.info(f"Next Schdeuled Run @ {next_run.strftime('%d-%m-%y %H:%M')}. Waiting {int(wait_seconds)} seconds...")
            time.sleep(wait_seconds)

            # --- Execute scheduled run ---
            weekday_str = datetime.now().strftime("%a").lower()
            if weekday_str in sch_days:
                try:
                    logger.save("=" * 60)
                    logger.notice(f"Running Schduled Program @ {datetime.now().strftime('%H:%M')} ({weekday_str.upper()})")

                    run_fn() #< -- function runs here
                    
                    logger.info(f"Completed Scheduled Run @ {datetime.now().strftime('%H:%M')}")
                except Exception as e:
                    logger.critical(f"Run failed: {type(e).__name__}: {e}")
                    
            else:
                logger.info(f"Skipped run because today ({weekday_str.upper()}) is not in run days.")
