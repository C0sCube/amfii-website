import os, re, json, string, shutil, json5, random
import fitz #type:ignore
from datetime import datetime, timedelta
from collections import defaultdict
import pandas as pd #type:ignore
from typing import List
from uuid import uuid4
from zoneinfo import ZoneInfo


class Helper:
    def __init__(self):
        self.TZ = ZoneInfo("Asia/Kolkata")
        pass
    

    @staticmethod
    def generate_uid():
        return uuid4().hex

    def generate_dates(self,date_format, minus_days=1):
        today = datetime.now(tz=self.TZ)
        to_str = today.strftime(date_format)
        yesterday = today - timedelta(days=minus_days)
        from_str = yesterday.strftime(date_format)
        return from_str, to_str
        # return "20-01-2026","21-01-2026"
    
    
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
    
    def _normalize_ascii(self, text: str) -> str:
        if not isinstance(text, str):
            return text
        text = re.sub(r"[^\x20-\x7E]+", " ", text)
        return re.sub(r"\s+", " ", text).strip()

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
    
    
    # def write_df_safe(self, writer, df, sheet_name, note_if_empty=None):
    #     if isinstance(df, pd.DataFrame) and not df.empty:
    #         df.to_excel(writer, sheet_name=sheet_name, index=False)
    #     else:
    #         placeholder = pd.DataFrame({
    #             "Info": [note_if_empty or "No data available"]
    #         })
    #         placeholder.to_excel(writer, sheet_name=sheet_name, index=False)
    def write_df_safe(self, writer, df, sheet_name, note_if_empty=None):
        if isinstance(df, pd.DataFrame):
            if df.empty:
                # write empty df WITH columns
                df.to_excel(writer, sheet_name=sheet_name, index=False)
            else:
                df.to_excel(writer, sheet_name=sheet_name, index=False)
    
    
