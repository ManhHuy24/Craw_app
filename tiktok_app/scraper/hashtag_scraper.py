# scraper/hashtag_scraper.py
from playwright.sync_api import sync_playwright, TimeoutError
from tiktok_captcha_solver import make_playwright_solver_context
from playwright_stealth import stealth_sync, StealthConfig
import time, os

def scrape_hashtag(hashtag, max_videos=20, scroll_limit=15):
    data = []
    seen = set()
    url = f"https://www.tiktok.com/tag/{hashtag}"

    API_KEY_TIKTOK = os.getenv("API_KEY_TIKTOK")
    launch_args = [
        "--disable-blink-features=AutomationControlled",
        "--no-sandbox",
        "--disable-setuid-sandbox",
        "--disable-dev-shm-usage",
    ]

    with sync_playwright() as p:
        context = make_playwright_solver_context(p, API_KEY_TIKTOK, headless=False, args=launch_args)
        page = context.new_page()

        # Apply stealth mode
        stealth_config = StealthConfig(
            navigator_languages=False,
            navigator_vendor=False,
            navigator_user_agent=False
        )
        stealth_sync(page, stealth_config)

        try:
            print(f"Đang truy cập: {url}")
            page.goto(url, timeout=60000)
            time.sleep(10)

            try:
                refresh_btn = page.query_selector('//button[contains(text(), "Refresh")]')
                if refresh_btn:
                    print("➡️ Phát hiện nút Refresh, đang click...")
                    refresh_btn.click()
                    time.sleep(20)  # Đợi sau khi xử lý captcha

                else:
                    print("✅ Không phát hiện nút Refresh – tiếp tục...")
            except Exception as e:
                print(f"⚠️ Lỗi khi xử lý nút Refresh: {e}")

            # 🔁 Cuộn trang và thu thập dữ liệu
            for _ in range(scroll_limit):
                page.mouse.wheel(0, 10000)
                time.sleep(10)

                elements = page.query_selector_all('p[data-e2e="challenge-item-username"].user-name')
                for el in elements:
                    username = el.inner_text().strip()
                    if username and username not in seen:
                        seen.add(username)
                        data.append({
                            'Username': username,
                            'Profile URL': f"https://www.tiktok.com/@{username}"
                        })
                        if len(data) >= max_videos:
                            context.close()
                            return data

        except TimeoutError:
            print("❌ Timeout khi truy cập TikTok.")
        except Exception as e:
            print(f"❌ Lỗi khác khi cào dữ liệu: {e}")

        context.close()
    return data
