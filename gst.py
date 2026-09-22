import os, re, json, base64, time, warnings
from pathlib import Path
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from transformers import pipeline
import pandas as pd
from utils import Helper
from logger import setup_logger

warnings.filterwarnings("ignore")

pipe = pipeline(
    "automatic-speech-recognition", model=r"D:\Developers\Kaustubh\whisper-medium"
)
utils = Helper()
logger = setup_logger(name="gstn_log")

BASE_SITE = "https://services.gst.gov.in/services/searchtp"

headers = {
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json;charset=UTF-8",
    "Origin": "https://services.gst.gov.in",
    "Referer": BASE_SITE,
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

year_dict = {
    "2017": "2017-2018",
    "2018": "2018-2019",
    "2019": "2019-2020",
    "2020": "2020-2021",
    "2021": "2021-2022",
    "2022": "2022-2023",
    "2023": "2023-2024",
    "2024": "2024-2025",
    "2025": "2025-2026",
    "2026": "2026-2027",
}


def normalize_digits(text: str) -> str:
    tokens = re.findall(r"\w+", text.lower())
    digits = []
    for tok in tokens:
        if tok.isdigit():
            digits.append(tok)
        elif tok in WORD_TO_DIGIT:
            digits.append(WORD_TO_DIGIT[tok])
    return "".join(digits)


def solve_captcha(driver, gstin, audio_dir):

    WebDriverWait(driver, 20).until(
        EC.invisibility_of_element_located((By.CSS_SELECTOR, ".dimmer-holder"))
    )

    textbox = WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.ID, "for_gstin"))
    )
    textbox.clear()
    textbox.send_keys(gstin)

    audio_button = WebDriverWait(driver, 20).until(
        EC.element_to_be_clickable(
            (By.XPATH, "//button[i[contains(@class,'fa-volume-up')]]")
        )
    )
    audio_button.click()
    logger.info("Audio button clicked...")

    time.sleep(5)
    logs = driver.get_log("performance")
    request_id = None
    for entry in logs:
        try:
            msg = json.loads(entry["message"])["message"]
            if msg["method"] == "Network.responseReceived":
                url = msg["params"]["response"]["url"]
                if "audiocaptcha" in url:  # keep the same filter
                    request_id = msg["params"]["requestId"]
                    break
        except Exception:
            pass

    if not request_id:
        raise Exception("Could not find audiocaptcha request in network logs.")

    body = driver.execute_cdp_cmd("Network.getResponseBody", {"requestId": request_id})
    audio_bytes = (
        base64.b64decode(body["body"])
        if body.get("base64Encoded")
        else body["body"].encode()
    )

    audio_path = Path(audio_dir) / f"captcha_audio_{gstin}.wav"
    with open(audio_path, "wb") as f:
        f.write(audio_bytes)

    result = pipe(str(audio_path))
    captcha_digits = normalize_digits(result["text"])
    captcha = re.sub(r"[^0-9]", "", captcha_digits)
    logger.info(f"Captcha solved: {captcha}")
    return captcha


def init_session(driver):
    session = requests.Session()
    for cookie in driver.get_cookies():
        session.cookies.set(cookie["name"], cookie["value"])
    return session


def fetch_and_save(session, gstin, captcha, output_dir):
    apis = {
        "taxpayerDetails": "https://services.gst.gov.in/services/api/search/taxpayerDetails",
        "taxpayerReturnDetails": "https://services.gst.gov.in/services/api/search/taxpayerReturnDetails",
        "goodservice": f"https://services.gst.gov.in/services/api/search/goodservice?gstin={gstin}",
        "dropdownfinyear": f"https://services.gst.gov.in/services/api/dropdownfinyear?gstin={gstin}",
    }

    gstin_dir = Path(output_dir) / gstin
    gstin_dir.mkdir(parents=True, exist_ok=True)

    for api_name, url in apis.items():
        try:
            if "?" in url:  # GET
                resp = session.get(url, headers=headers, verify=False)
                data = (
                    resp.json()
                    if resp.ok
                    else {"status": "Failed", "code": resp.status_code}
                )
            elif "taxpayerReturnDetails" in api_name:
                all_data = []
                for year, val in year_dict.items():
                    payload = {"gstin": gstin, "fy": year}
                    resp = session.post(
                        url, json=payload, headers=headers, verify=False
                    )
                    data = (
                        resp.json()
                        if resp.ok
                        else {"status": "Failed", "code": resp.status_code}
                    )

                    if "filingStatus" not in data:
                        all_data.extend(
                            [
                                {
                                    "fy": val,
                                    "taxp": "NA",
                                    "mof": "NA",
                                    "dof": "NA",
                                    "rtntype": "NA",
                                    "arn": "NA",
                                    "status": "Data not Found !!",
                                    "gstin": gstin,
                                }
                            ]
                        )
                    else:

                        temp = data.get("filingStatus", [])[0]
                        for t in temp:
                            t["gstin"] = gstin

                        all_data.extend(temp)
                data = all_data
            else:  # POST
                payload = {"gstin": gstin, "captcha": captcha}
                resp = session.post(url, json=payload, headers=headers, verify=False)
                data = (
                    resp.json()
                    if resp.ok
                    else {"status": "Failed", "code": resp.status_code}
                )
            filename = gstin_dir / f"{api_name}.json"
            utils.save_json(data, filename)
            logger.info(f"Saved {api_name} for {gstin} -> {filename}")
        except Exception as e:
            logger.exception(f"Error fetching {api_name} for {gstin}: {e}")


def main(gstins):
    options = webdriver.ChromeOptions()
    options.set_capability("goog:loggingPrefs", {"performance": "ALL"})
    driver = webdriver.Chrome(options=options)
    driver.execute_cdp_cmd("Network.enable", {})

    audio_dir = Path("output/gstn_audio")
    audio_dir.mkdir(parents=True, exist_ok=True)
    output_dir = Path("output/gstin_json2")
    output_dir.mkdir(parents=True, exist_ok=True)
    total_gstins = len(gstins)

    try:
        driver.get(BASE_SITE)

        WebDriverWait(driver, 20).until(
            EC.invisibility_of_element_located((By.CSS_SELECTOR, ".dimmer-holder"))
        )

        for idx, gstin in enumerate(gstins, start=1):
            logger.info(f"FETCHING: {idx} /{total_gstins} :: {gstin}")
            captcha = solve_captcha(driver, gstin, audio_dir)
            session = init_session(driver)
            fetch_and_save(session, gstin, captcha, output_dir)

            # refresh captcha UI for next GSTIN
            search_button = WebDriverWait(driver, 20).until(
                EC.element_to_be_clickable((By.ID, "lotsearch"))
            )
            search_button.click()
            refresh_button = WebDriverWait(driver, 20).until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//button[i[contains(@class,'fa-refresh')]]")
                )
            )
            refresh_button.click()

            # After every 50 GSTINs, reload the whole site
            if idx % 50 == 0:
                logger.info("Reloading site after 50 GSTINs...")
                driver.get(BASE_SITE)
                WebDriverWait(driver, 20).until(
                    EC.invisibility_of_element_located(
                        (By.CSS_SELECTOR, ".dimmer-holder")
                    )
                )

    except Exception as e:
        logger.exception(e)
    finally:
        driver.quit()


if __name__ == "__main__":
    csv_path = r"FETCH.csv"
    df = pd.read_csv(csv_path)
    gstins = df["gstin"].to_list()[200:]
    main(gstins)
