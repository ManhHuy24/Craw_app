# scraper/profile_scraper.py
import pandas as pd
import time
from playwright.sync_api import sync_playwright

def scrape_profiles(input_file, output_file):
    df = pd.read_csv(input_file)
    updated_rows = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        for index, row in df.iterrows():
            url = row.get("Profile URL")
            if not url:
                continue
            try:
                page.goto(url, timeout=60000)
                time.sleep(5)

                # Lấy số followers, following, likes
                followers = page.locator('[data-e2e="followers-count"]').text_content() or ""
                following = page.locator('[data-e2e="following-count"]').text_content() or ""
                likes = page.locator('[data-e2e="likes-count"]').text_content() or ""

                # Lấy bio nếu có
                try:
                    bio = page.locator('[data-e2e="user-bio"]').text_content() or ""
                except:
                    bio = ""

                row['Followers'] = followers.strip()
                row['Following'] = following.strip()
                row['Likes'] = likes.strip()
                row['Bio'] = bio.strip()

            except Exception as e:
                print(f"Lỗi với {url}: {e}")
                row['Followers'] = row['Following'] = row['Likes'] = row['Bio'] = ''

            updated_rows.append(row)

        browser.close()

    pd.DataFrame(updated_rows).to_csv(output_file, index=False, encoding='utf-8-sig')
