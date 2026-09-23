import re, json, base64, time, warnings
from pathlib import Path

import requests
import pandas as pd

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from transformers import pipeline
from utils import Helper
from logger import setup_logger

warnings.filterwarnings("ignore")

pipe = pipeline(
    "automatic-speech-recognition",
    model=r"E:\AI_Models\whisper-medium"
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
    "zero": "0", "oh": "0", "one": "1", "two": "2",
    "three": "3", "four": "4", "five": "5",
    "six": "6", "seven": "7", "eight": "8", "nine": "9"
}

year_dict = {
    str(y): f"{y}-{y + 1}" for y in range(2017, 2027)
}


# ============================================================
# HELPERS
# ============================================================

def wait_site(driver):
    WebDriverWait(driver, 20).until(
        EC.invisibility_of_element_located(
            (By.CSS_SELECTOR, ".dimmer-holder")
        )
    )


def request(session, method, url, payload=None, retries=3):
    last_error = None

    for attempt in range(1, retries + 1):
        try:
            r = session.request(
                method,
                url,
                json=payload,
                headers=headers,
                verify=False,
                timeout=30
            )

            if not r.ok:
                raise requests.HTTPError(
                    f"HTTP {r.status_code}: {r.text[:200]}"
                )

            return r.json()

        except Exception as e:
            last_error = e
            logger.warning(
                f"{method} {url} failed "
                f"({attempt}/{retries}): {e}"
            )

            if attempt < retries:
                time.sleep(attempt * 2)

    raise last_error


def normalize_digits(text):
    result = []

    for token in re.findall(r"\w+", text.lower()):
        if token.isdigit():
            result.append(token)
        elif token in WORD_TO_DIGIT:
            result.append(WORD_TO_DIGIT[token])

    return "".join(result)


# ============================================================
# CAPTCHA
# ============================================================

def solve_captcha(driver, gstin, audio_dir, retries=3):

    last_error = None

    for attempt in range(1, retries + 1):
        try:
            wait_site(driver)

            box = WebDriverWait(driver, 20).until(
                EC.presence_of_element_located(
                    (By.ID, "for_gstin")
                )
            )

            box.clear()
            box.send_keys(gstin)

            WebDriverWait(driver, 20).until(
                EC.element_to_be_clickable(
                    (
                        By.XPATH,
                        "//button[i[contains(@class,'fa-volume-up')]]"
                    )
                )
            ).click()

            logger.info(
                f"[{gstin}] CAPTCHA attempt "
                f"{attempt}/{retries}"
            )

            # Poll network logs instead of blindly waiting 5 sec
            request_id = None

            for _ in range(20):
                time.sleep(0.5)

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

                if request_id:
                    break

            if not request_id:
                raise RuntimeError(
                    "audiocaptcha request not found"
                )

            body = driver.execute_cdp_cmd(
                "Network.getResponseBody",
                {"requestId": request_id}
            )

            audio = (
                base64.b64decode(body["body"])
                if body.get("base64Encoded")
                else body["body"].encode()
            )

            audio_path = (
                Path(audio_dir)
                / f"captcha_audio_{gstin}.wav"
            )

            audio_path.write_bytes(audio)

            text = pipe(str(audio_path))["text"]
            captcha = re.sub(
                r"\D",
                "",
                normalize_digits(text)
            )

            if not captcha:
                raise ValueError(
                    f"Could not decode CAPTCHA: {text!r}"
                )

            logger.info(
                f"[{gstin}] CAPTCHA solved: {captcha}"
            )

            return captcha

        except Exception as e:
            last_error = e

            logger.warning(
                f"[{gstin}] CAPTCHA failed: {e}"
            )

            if attempt < retries:
                try:
                    refresh_captcha(driver)
                except Exception:
                    pass

    raise RuntimeError(
        f"CAPTCHA failed after {retries} attempts"
    ) from last_error


# ============================================================
# SESSION
# ============================================================

def init_session(driver):
    session = requests.Session()

    for cookie in driver.get_cookies():
        session.cookies.set(
            cookie["name"],
            cookie["value"]
        )

    return session


# ============================================================
# API FETCH
# ============================================================

def fetch_and_save(session, gstin, captcha, output_dir):

    urls = {
        "taxpayerDetails":
            "https://services.gst.gov.in/services/api/search/taxpayerDetails",

        "taxpayerReturnDetails":
            "https://services.gst.gov.in/services/api/search/taxpayerReturnDetails",

        "goodservice":
            f"https://services.gst.gov.in/services/api/search/"
            f"goodservice?gstin={gstin}",

        "dropdownfinyear":
            f"https://services.gst.gov.in/services/api/"
            f"dropdownfinyear?gstin={gstin}",
    }

    gstin_dir = Path(output_dir) / gstin
    gstin_dir.mkdir(parents=True, exist_ok=True)

    failed = []

    for name, url in urls.items():

        try:

            # GET
            if "?" in url:
                data = request(session, "GET", url)

            # RETURN DETAILS
            elif name == "taxpayerReturnDetails":

                data = []

                for year, fy in year_dict.items():

                    try:
                        result = request(
                            session,
                            "POST",
                            url,
                            {"gstin": gstin, "fy": year}
                        )

                        if "filingStatus" in result:
                            rows = result["filingStatus"][0]

                            for row in rows:
                                row["gstin"] = gstin

                            data.extend(rows)

                        else:
                            data.append({
                                "fy": fy,
                                "taxp": "NA",
                                "mof": "NA",
                                "dof": "NA",
                                "rtntype": "NA",
                                "arn": "NA",
                                "status": "Data not Found !!",
                                "gstin": gstin
                            })

                    except Exception as e:
                        logger.warning(
                            f"[{gstin}] FY {year} failed: {e}"
                        )

                        data.append({
                            "fy": fy,
                            "status": "Request Failed",
                            "gstin": gstin,
                            "error": str(e)
                        })

            # POST
            else:
                data = request(
                    session,
                    "POST",
                    url,
                    {
                        "gstin": gstin,
                        "captcha": captcha
                    }
                )

            filename = gstin_dir / f"{name}.json"
            utils.save_json(data, filename)

            logger.info(
                f"[{gstin}] Saved {name}"
            )

        except Exception as e:

            failed.append(name)

            logger.exception(
                f"[{gstin}] {name} failed: {e}"
            )

    return failed


# ============================================================
# CAPTCHA REFRESH / SITE RESET
# ============================================================

def refresh_captcha(driver):

    wait_site(driver)

    WebDriverWait(driver, 20).until(
        EC.element_to_be_clickable(
            (By.ID, "lotsearch")
        )
    ).click()

    WebDriverWait(driver, 20).until(
        EC.element_to_be_clickable(
            (
                By.XPATH,
                "//button[i[contains(@class,'fa-refresh')]]"
            )
        )
    ).click()


def reload_site(driver):
    logger.info("Reloading GSTN site...")
    driver.get(BASE_SITE)
    wait_site(driver)


# ============================================================
# MAIN
# ============================================================

def main(gstins):

    options = webdriver.ChromeOptions()
    options.set_capability(
        "goog:loggingPrefs",
        {"performance": "ALL"}
    )

    driver = webdriver.Chrome(options=options)

    driver.execute_cdp_cmd(
        "Network.enable",
        {}
    )

    audio_dir = Path("output/gstn_audio")
    output_dir = Path("output/gstin_json2")
    failed_file = Path("output/gstin_failed.json")

    audio_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    failed_gstins = []

    try:

        reload_site(driver)

        for idx, gstin in enumerate(gstins, 1):

            logger.info(
                f"{'=' * 60}\n"
                f"GSTIN {idx}/{len(gstins)} :: {gstin}"
            )

            try:

                captcha = solve_captcha(
                    driver,
                    gstin,
                    audio_dir
                )

                session = init_session(driver)

                failed_apis = fetch_and_save(
                    session,
                    gstin,
                    captcha,
                    output_dir
                )

                if failed_apis:
                    failed_gstins.append({
                        "gstin": gstin,
                        "failed_apis": failed_apis
                    })

                refresh_captcha(driver)

            except Exception as e:

                logger.exception(
                    f"[{gstin}] FAILED: {e}"
                )

                failed_gstins.append({
                    "gstin": gstin,
                    "error": str(e)
                })

                # Recover browser before next GSTIN
                try:
                    reload_site(driver)
                except Exception:
                    logger.exception(
                        "Browser recovery failed"
                    )
                    break

            if idx % 50 == 0:
                reload_site(driver)

        failed_file.write_text(
            json.dumps(
                failed_gstins,
                indent=2
            ),
            encoding="utf-8"
        )

        logger.info(
            f"Finished. "
            f"Failed GSTINs: {len(failed_gstins)}"
        )

    finally:
        driver.quit()


# ============================================================
# ENTRY
# ============================================================

if __name__ == "__main__":

    df = pd.read_csv("FETCH.csv")

    gstins = (
        df["gstin"]
        .dropna()
        .astype(str)
        .str.strip()
        .tolist()[1000:]
    )

    main(gstins)
