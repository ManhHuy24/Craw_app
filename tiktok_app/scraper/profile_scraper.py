# scraper/profile_scraper.py
import pandas as pd
import time
import os
from multiprocessing import Process
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from tiktok_captcha_solver import make_undetected_chromedriver_solver
import chromedriver_autoinstaller

def scrape_profiles(input_file, output_file):
    df = pd.read_csv(input_file)
    # chromedriver_autoinstaller.install()
    service = Service("chromedriver.exe")
    options = Options()
    # options.add_argument("--headless")
    options.add_argument("--disable-infobars")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--log-level=3")

    # driver = webdriver.Chrome(options=options)
    driver = webdriver.Chrome(service=service, options=options)
    updated_rows = []

    for index, row in df.iterrows():
        url = row.get("Profile URL")
        if not url:
            continue

        try:
            driver.get(url)
            time.sleep(5)  # Hoặc dùng WebDriverWait để chờ chính xác hơn

            wait = WebDriverWait(driver, 10)

            followers = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '[data-e2e="followers-count"]'))).text
            following = driver.find_element(By.CSS_SELECTOR, '[data-e2e="following-count"]').text
            likes = driver.find_element(By.CSS_SELECTOR, '[data-e2e="likes-count"]').text

            try:
                bio = driver.find_element(By.CSS_SELECTOR, '[data-e2e="user-bio"]').text
            except:
                bio = ""

            row['Followers'] = followers
            row['Following'] = following
            row['Likes'] = likes
            row['Bio'] = bio

        except Exception as e:
            print(f"Lỗi với {url}: {e}")
            row['Followers'] = row['Following'] = row['Likes'] = row['Bio'] = ''

        updated_rows.append(row)

    driver.quit()
    pd.DataFrame(updated_rows).to_csv(output_file, index=False, encoding='utf-8-sig')