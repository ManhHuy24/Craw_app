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
from tiktok_captcha_solver import make_undetected_chromedriver_solver
import chromedriver_autoinstaller

def scrape_single_batch(batch_data, batch_num, total_batch, output_dir):
    chromedriver_autoinstaller.install()
    # api_key = "5fe871299e9a4e80267ba952e4b8df24"
    # options = uc.ChromeOptions()
    # service = Service("chromedriver.exe")
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-infobars")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--log-level=3")
    # driver = make_undetected_chromedriver_solver(api_key, options=options)
    
    driver = webdriver.Chrome(options=options)
    # driver = webdriver.Chrome(service=service, options=options)
    results = []

    for i, (index, row) in enumerate(batch_data.iterrows(), start=1):
        url = row['Profile URL']
        try:
            driver.get(url)
            time.sleep(5)
            stats = {
                'Following': driver.find_element(By.CSS_SELECTOR, 'strong[data-e2e="following-count"]').text,
                'Followers': driver.find_element(By.CSS_SELECTOR, 'strong[data-e2e="followers-count"]').text,
                'Likes': driver.find_element(By.CSS_SELECTOR, 'strong[data-e2e="likes-count"]').text,
                'Bio': driver.find_element(By.CSS_SELECTOR, 'h2[data-e2e="user-bio"]').text,
            }
            results.append({**row.to_dict(), **stats})
        except NoSuchElementException:
            print(f"[Batch {batch_num}] ⚠️ Không tìm thấy thông tin.")
        time.sleep(4)

    driver.quit()
    batch_file = os.path.join(output_dir, f"batch_{batch_num}.csv")
    pd.DataFrame(results).to_csv(batch_file, index=False, encoding='utf-8-sig')

def scrape_profiles(input_file, output_file, batch_size=50, delay_between_batches=15):
    df = pd.read_csv(input_file)
    total = len(df)
    batch_count = (total + batch_size - 1) // batch_size
    output_dir = os.path.dirname(output_file)
    os.makedirs(output_dir, exist_ok=True)

    processes = []

    for i in range(batch_count):
        batch_data = df.iloc[i * batch_size : (i + 1) * batch_size]
        batch_num = i + 1
        p = Process(target=scrape_single_batch, args=(batch_data, batch_num, batch_count, output_dir))
        p.start()
        processes.append(p)
        if i < batch_count - 1:
            time.sleep(delay_between_batches)

    # Đợi tất cả batch hoàn thành
    for p in processes:
        p.join()

    # Gộp tất cả các file batch
    all_results = []
    for i in range(1, batch_count + 1):
        batch_file = os.path.join(output_dir, f"batch_{i}.csv")
        if os.path.exists(batch_file):
            df_batch = pd.read_csv(batch_file)
            all_results.append(df_batch)
            os.remove(batch_file)  # Xoá file batch sau khi gộp

    if all_results:
        final_df = pd.concat(all_results, ignore_index=True)
        final_df.to_csv(output_file, index=False, encoding='utf-8-sig')
    else:
        print("❌ Không có dữ liệu nào được thu thập.")