from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import requests
from pathlib import Path
from transformers import pipeline  # type: ignore
import warnings
import time
import json
import base64
import re
import os

from logger import setup_logger
from utils import Helper

warnings.filterwarnings("ignore")

logger = setup_logger("pan_log")
utils = Helper()
pipe = pipeline(
    "automatic-speech-recognition", model=r"D:\Developers\Kaustubh\whisper-medium"
)

options = webdriver.ChromeOptions()
options.set_capability("goog:loggingPrefs", {"performance": "ALL"})

headers = {
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json;charset=UTF-8",
    "Origin": "https://services.gst.gov.in",
    "Referer": "https://services.gst.gov.in/services/searchtpbypan",
}

WORD_TO_DIGIT = {
    "zero": "0",
    "oh": "0",
    "one": "1",
    "two": "2",
    "three": "3",
    "four": "4",
    "five": "5",
    "six": "6",
    "seven": "7",
    "eight": "8",
    "nine": "9",
}

pans = [
    "AAACI4798L",
    "AAACG1653N",
    "AAACH0351E",
    "AAACV7244E",
    "AADCS1718H",
    "AAACI4341M",
    "AAACH1458C",
    "AAACR4849R",
    "AACCT8243P",
    "AACCA1963B",
]


def normalize_digits(text):
    tokens = re.findall(r"\w+", text.lower())
    return "".join(
        WORD_TO_DIGIT.get(t, t) for t in tokens if t.isdigit() or t in WORD_TO_DIGIT
    )


def save_failed_pan(pan):
    with open("failed.txt", "a", encoding="utf-8") as f:
        f.write(f"{pan}\n")


def refresh_captcha(wait):
    try:
        refresh_btn = wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "//button[i[contains(@class,'fa-refresh')]]")
            )
        )
        refresh_btn.click()
        time.sleep(2)
    except Exception:
        logger.exception("Captcha refresh failed")


api_url = "https://services.gst.gov.in/services/api/get/gstndtls"
web_url = "https://services.gst.gov.in/services/searchtpbypan"
pan_json = r"listed.json"


pan_data = utils.load_json(pan_json)

pan_dict = { i["Workstation Name"]:i["PAN No"] for i in pan_data}

audio_dir = Path("output/pan_audio")
audio_dir.mkdir(parents=True, exist_ok=True)

output_dir = Path("output/pan_json")
output_dir.mkdir(parents=True, exist_ok=True)

driver = webdriver.Chrome(options=options)
driver.execute_cdp_cmd("Network.enable", {})

try:
    driver.get(web_url)

    wait = WebDriverWait(driver, 20)

    wait.until(EC.invisibility_of_element_located((By.CSS_SELECTOR, ".dimmer-holder")))

    for c_name,pan in pan_dict.items():

        try:
            logger.info(f"PAN : {pan} -- {c_name}")
            textbox = wait.until(EC.presence_of_element_located((By.ID, "for_gstin")))

            textbox.clear()
            textbox.send_keys(pan)

            wait.until(
                EC.element_to_be_clickable(
                    (
                        By.XPATH,
                        "//button[i[contains(@class,'fa-volume-up')]]",
                    )
                )
            ).click()

            time.sleep(4)

            request_id = None

            for entry in driver.get_log("performance"):
                try:
                    msg = json.loads(entry["message"])["message"]

                    if msg["method"] == "Network.responseReceived":
                        url = msg["params"]["response"]["url"]

                        if "audiocaptcha" in url:
                            request_id = msg["params"]["requestId"]
                            break

                except Exception:
                    pass

            if not request_id:
                raise Exception("Audio request not found")

            body = driver.execute_cdp_cmd(
                "Network.getResponseBody",
                {"requestId": request_id},
            )

            audio_bytes = (
                base64.b64decode(body["body"])
                if body.get("base64Encoded")
                else body["body"].encode()
            )

            audio_path = audio_dir / f"{pan}.wav"

            with open(audio_path, "wb") as f:
                f.write(audio_bytes)

            result = pipe(str(audio_path))
            captcha = re.sub(r"[^0-9]","",normalize_digits(result["text"]))

            logger.info(f"Captcha : {captcha}")

            session = requests.Session()

            for cookie in driver.get_cookies():
                session.cookies.set(cookie["name"], cookie["value"])

            response = session.post(
                api_url,
                json={"panNO": pan, "captcha": captcha},
                headers=headers,
                verify=False,
                timeout=30,
            )

            if not response.ok:
                raise Exception(f"API Failed - {response.status_code}")

            data = response.json()
            utils.save_json(data, output_dir / f"{pan}.json")
            logger.info(f"Saved JSON for {pan}")

            refresh_captcha(wait)

        except Exception as e:

            logger.exception(f"Failed PAN {pan}")
            save_failed_pan(pan)
            utils.save_json(data, output_dir / f"{pan}_failed.json")
            refresh_captcha(wait)

            continue

except Exception:
    logger.exception("Fatal error")

finally:
    driver.quit()
    logger.info("Execution completed")
