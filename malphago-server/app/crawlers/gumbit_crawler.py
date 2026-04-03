"""검빛(Gumbit) 크롤러 - Selenium 기반

크롤링 대상:
1. 기수별 전적 기록 (statv40/jockeys.html)

기존 hracing/gumvit_crawler.py 기반 이식
"""

import logging
import time
from dataclasses import dataclass, field

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

logger = logging.getLogger(__name__)

GUMBIT_BASE = "http://www.gumvit.com"
LOC_CODES = {"S": "S", "B": "B", "J": "J"}


@dataclass
class JockeyRecord:
    """기수 전적 데이터"""
    jockey_name: str = ""
    race_date: str = ""
    horse_name: str = ""
    ranking: str = ""
    popularity: str = ""
    race_level: str = ""
    distance: str = ""
    race_type: str = ""
    trainer_name: str = ""
    owner_name: str = ""


def _create_driver() -> webdriver.Chrome:
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    driver = webdriver.Chrome(options=options)
    driver.implicitly_wait(10)
    return driver


def crawl_jockey_records(track_code: str = "S") -> list[JockeyRecord]:
    """특정 경마장의 모든 기수 전적 크롤링

    Args:
        track_code: 경마장 코드 (S/B/J)

    Returns:
        list of JockeyRecord
    """
    loc = LOC_CODES.get(track_code.upper(), "S")
    url = f"{GUMBIT_BASE}/statv40/jockeys.html?loc={loc}"
    all_records = []

    driver = _create_driver()
    try:
        driver.get(url)
        time.sleep(2)

        name_elements = driver.find_elements(By.CLASS_NAME, "name")
        jockey_count = len(name_elements)
        logger.info(f"Found {jockey_count} jockeys at {track_code}")

        for i in range(jockey_count):
            try:
                driver.get(url)
                time.sleep(1)
                name_elements = driver.find_elements(By.CLASS_NAME, "name")
                if i >= len(name_elements):
                    break

                name_el = name_elements[i]
                jockey_name = name_el.text.strip()
                logger.info(f"  Crawling jockey: {jockey_name} ({i + 1}/{jockey_count})")

                name_el.click()
                time.sleep(1)

                try:
                    WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.TAG_NAME, "input"))
                    ).click()
                except Exception:
                    logger.warning(f"  Skip {jockey_name} - button not clickable")
                    continue

                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located(
                        (By.XPATH, "//table[@width='800'][@bgcolor='#d8d8d8']//tr")
                    )
                )

                rows = driver.find_elements(
                    By.XPATH, "//table[@width='800'][@bgcolor='#d8d8d8']//tr"
                )[1:]

                for row in rows:
                    cols = row.find_elements(By.TAG_NAME, "td")
                    values = [col.text.strip() for col in cols]
                    if len(values) < 9:
                        continue

                    record = JockeyRecord(
                        jockey_name=jockey_name,
                        race_date=values[0],
                        horse_name=values[1],
                        ranking=values[2],
                        popularity=values[3],
                        race_level=values[4],
                        distance=values[5],
                        race_type=values[6],
                        trainer_name=values[7],
                        owner_name=values[8],
                    )
                    all_records.append(record)

                logger.info(f"  {jockey_name}: {len(rows)} records")

            except Exception as e:
                logger.error(f"  Error crawling jockey {i}: {e}")
                continue

    finally:
        driver.quit()

    logger.info(f"Total: {len(all_records)} jockey records from {track_code}")
    return all_records
