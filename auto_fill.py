#!/usr/bin/env python3
# -*- coding:utf-8 -*-

import json
import time
import random
import logging
import shutil
import os
import subprocess
import re
import requests

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

# ---------- Logger ----------
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

# ---------- Config ----------
FIXED_JSON      = "voc.json"  # 最初合併後但未填值的檔案
STATE_JSON      = "voc_merged_state.json"  # 唯一使用的狀態檔
BASE_URL        = "https://dictionary.cambridge.org/dictionary/english-chinese-traditional/"
MAX_ERROR_SAVE  = 5
ERROR_KEY_PHRASE= "PdhAddEnglishCounter failed for '\\Processor(_Total)\\% Processor Time'"

# 偵測本機安裝的 Chrome 瀏覽器版本
def get_chrome_version():
    result = subprocess.run(
        r'reg query "HKEY_CURRENT_USER\Software\Google\Chrome\BLBeacon" /v version',
        capture_output=True, text=True, shell=True
    )
    match = re.search(r"(\d+\.\d+\.\d+\.\d+)", result.stdout)
    return match.group(1) if match else None

# 根據 chrome 主版本（如 138），找對應的 ChromeDriver 完整版本號
def find_matching_driver_version(chrome_version):
    major_version = chrome_version.split('.')[0]
    url = f"https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions-with-downloads.json"
    response = requests.get(url)
    if response.status_code != 200:
        raise RuntimeError("無法從 Google 查詢對應的 ChromeDriver 版本。")
    data = response.json()
    versions = data["channels"]["Stable"]
    if versions["version"].startswith(major_version + "."):
        return versions["version"]
    raise RuntimeError(f"找不到對應 Chrome {major_version} 的 chromedriver")


# ---------- Helper ----------
def save_progress(data):
    with open(STATE_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    logger.info(f"[Checkpoint] 進度已存到 {STATE_JSON}")

def fetch_from_cambridge(driver, voc):
    url = BASE_URL + voc
    
    # 對 driver.get() 加 try-except
    try:
        driver.get(url)
    except Exception as e:
        logger.warning(f"[TimeoutError] driver.get({url}) 失敗：{e}")
        return None, None, "timeout"

    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".entry-body__el"))
        )
    except:
        logger.warning(f"[Timeout] 頁面載入逾時：{voc}")
        return None, None, "timeout"

    # 檢查是否被封鎖 (ban) 或出現 CAPTCHA
    if "Are you a human?" in driver.page_source or "verify you are a human" in driver.page_source.lower():
        logger.warning(f"[Blocked] 被懷疑為機器人：{voc}")
        return None, None, "blocked"

    # 擷取 console log，過濾無關錯誤
    logs = driver.get_log("browser")
    severe_logs = [
        entry for entry in logs
        if entry["level"] == "SEVERE" and "PdhAddEnglishCounter" not in entry["message"]
    ]
    err_count = len(severe_logs)

    soup = BeautifulSoup(driver.page_source, "html.parser")

    # 取詞頭
    head = soup.select_one("span.hw.dhw")
    if not head:
        logger.warning(f"[NotFound] 找不到詞頭標籤 span.hw.dhw：{voc}")
        return None, None, "not_found"

    page_head = head.text.strip().lower()
    input_head = voc.strip().lower()
    if page_head != input_head:
        logger.warning(f"[Mismatch] 詞頭不符：{page_head} ≠ {input_head}")
        return None, None, "mismatch"

    # 取中文翻譯
    trans_el = soup.select_one("span.dtrans")
    translation = trans_el.get_text(strip=True) if trans_el else None

    # 取例句
    ex_el = soup.select_one("span.eg.deg")
    sentence = None
    if ex_el:
        full = ex_el.get_text(" ", strip=True)
        if "。" in full:
            sentence = full.split("。")[0].strip() + "。"
        elif "." in full:
            sentence = full.split(".")[0].strip() + "."
        else:
            sentence = full.strip()

    return translation, sentence, err_count

# ---------- Main ----------
def fill_cambridge():
    # 1. 如果 STATE_JSON 不在，先從 FIXED_JSON 複製一份
    if not os.path.exists(STATE_JSON):
        shutil.copy(FIXED_JSON, STATE_JSON)
        logger.info(f"首次執行，從 {FIXED_JSON} 建立狀態檔 {STATE_JSON}")

    # 2. 啟動 Chrome
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-extensions")
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-software-rasterizer")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option('excludeSwitches', ['enable-automation'])
    options.add_experimental_option('useAutomationExtension', False)
    options.set_capability("goog:loggingPrefs", {"browser": "ALL"})

    # 使用 webdriver-manager 自動安裝相容 ChromeDriver
    # 自動偵測 Chrome 版本與下載對應的 driver
    chrome_version = get_chrome_version()
    if not chrome_version:
        raise RuntimeError("找不到本機已安裝的 Chrome。請確認已正確安裝 Chrome。")
    logger.info(f"偵測到 Chrome 版本：{chrome_version}")

    driver_version = find_matching_driver_version(chrome_version)
    logger.info(f"自動對應 ChromeDriver 版本：{driver_version}")

    service = Service(ChromeDriverManager(driver_version).install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.set_page_load_timeout(15)  # 頁面加載最多等 15 秒
    logger.info("Chrome 啟動完畢，開始處理...")

    # 3. 讀取並續接
    with open(STATE_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    consecutive_errors = 0
    total = len(data)

    for idx, entry in enumerate(data, start=1):
        voc = entry.get("Voc")
        if not voc or not isinstance(voc, str) or not voc.strip():
            logger.warning(f"[Skip] 缺少或無效 Voc 欄位：{entry}")
            continue
        voc = voc.strip()
        needs = [f for f in ("translation","Sentence") if not entry.get(f)]
        if not needs:
            continue

        t, s, err = fetch_from_cambridge(driver, voc)
        logger.info(f"{idx}/{total} {voc} → t:{t!r}, s:{s!r}, err:{err}")

        filled = False
        if "translation" in needs and t:
            entry["translation"] = t; filled = True
        if "Sentence"    in needs and s:
            entry["Sentence"]     = s; filled = True

        # ban-like 錯誤偵測改為根據錯誤字串而非 err 數值
        is_error = isinstance(err, str) and err in ("timeout", "blocked", "not_found", "mismatch")

        if is_error and not filled:
            consecutive_errors += 1
            logger.warning(f"[ConsecErr {consecutive_errors}/{MAX_ERROR_SAVE}]")
        else:
            consecutive_errors = 0

        if consecutive_errors >= MAX_ERROR_SAVE:
            save_progress(data)
            consecutive_errors = 0

        # 增加等待時間（建議 2～4 秒以防 ban）
        time.sleep(random.uniform(2, 4))

    # 4. 最後存檔、關瀏覽器
    save_progress(data)
    driver.quit()
    logger.info("所有單字處理完成。")

if __name__ == "__main__":
    fill_cambridge()
