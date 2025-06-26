# scraper/hashtag_scraper.py
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import pandas as pd
import time
from tiktok_captcha_solver import make_undetected_chromedriver_solver
from selenium_stealth import stealth
import undetected_chromedriver as uc
import chromedriver_autoinstaller

def scrape_hashtag(hashtag, output_file, max_videos=200, scroll_limit=15):
    chromedriver_autoinstaller.install()
    # service = Service("chromedriver.exe")
    # api_key = "898d7d384e9c8b514aaf2cd8bb5933c1"
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--start-maximized")
    options.add_argument("--disable-infobars")
    options.add_argument("--log-level=3")

    # driver = make_undetected_chromedriver_solver(api_key, options=options)

    driver = webdriver.Chrome(options=options)
    # driver = webdriver.Chrome(service=service, options=options)
    url = f"https://www.tiktok.com/tag/{hashtag}"
    driver.get(url)
    time.sleep(5)

    # try:
    #     refresh_btn = driver.find_element(By.XPATH, '//button[contains(text(), "Refresh")]')
    #     print("➡️ Phát hiện nút Refresh, đang click...")
    #     refresh_btn.click()
    #     time.sleep(5)  # Cho trang chuyển sang captcha
    # except NoSuchElementException:
    #     print("✅ Không phát hiện nút Refresh – tiếp tục...")

    data = []
    seen = set()

    for _ in range(scroll_limit):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(5)
        try:
            video_container = driver.find_element(By.CSS_SELECTOR, "div.css-1qb12g8-DivThreeColumnContainer.eegew6e2")
            videos = video_container.find_elements(By.CSS_SELECTOR, "div.css-x6y88p-DivItemContainerV2.e19c29qe7")
            for v in videos:
                try:
                    username_element = v.find_element(By.CSS_SELECTOR, 'p[data-e2e="challenge-item-username"].user-name')
                    username = username_element.text.strip()
                    if username not in seen:
                        seen.add(username)
                        data.append({
                            'Username': username,
                            'Profile URL': f"https://www.tiktok.com/@{username}"
                        })

                        print(f"Đã thu thập {len(data)} kênh.")

                        if len(data) >= max_videos:
                            break
                except:
                    continue
            if len(data) >= max_videos:
                break
        except:
            continue

    driver.quit()
    pd.DataFrame(data).to_csv(output_file, index=False, encoding='utf-8-sig')
