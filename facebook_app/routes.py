from flask import Blueprint, render_template, request, send_from_directory
import pandas as pd
import os
import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from datetime import datetime, timedelta
from time import sleep, time
from unidecode import unidecode
import chromedriver_autoinstaller

facebook_blueprint = Blueprint('facebook', __name__,
                             template_folder='templates',
                             static_folder='static')

@facebook_blueprint.route('/', methods=['GET', 'POST'])
def index():
    elapsed_time = None
    file_path = None

    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        group_url = request.form['group_url']

        match = re.search(r'/groups/([^/?#]+)', group_url)
        group_id = match.group(1) if match else "unknown"

        start_time = time()

        chromedriver_autoinstaller.install()
        # service = Service("chromedriver.exe")
        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--start-maximized")
        options.add_argument("--disable-infobars")
        options.add_argument("--log-level=3")
        browser = webdriver.Chrome(options=options)

        # browser = webdriver.Chrome(service=service)
        browser.get("http://facebook.com")
        sleep(3)
        browser.find_element(By.ID, "email").send_keys(email)
        browser.find_element(By.ID, "pass").send_keys(password + Keys.ENTER)
        sleep(120)

        browser.get(group_url)
        sleep(5)

        user_data = []
        MAX_POSTS = 200

        for _ in range(20):
            browser.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            sleep(3)
            post_divs = browser.find_elements(By.CLASS_NAME, "x1yztbdb")

            for div in post_divs:
                try:
                    a_tag = div.find_element(By.TAG_NAME, "a")
                    href = a_tag.get_attribute("href")
                    match = re.search(r'/groups/\d+/user/(\d+)/', href)
                    if match:
                        uid = match.group(1)
                        try:
                            name = div.find_element(By.CSS_SELECTOR, 'span.html-span').text.strip()
                        except:
                            name = ""
                        full_href = "https://www.facebook.com" + match.group(0)

                        try:
                            time_tag = div.find_element(By.XPATH, ".//a[contains(@aria-label, 'phút') or contains(@aria-label, 'giờ') or contains(@aria-label, 'ngày')]")
                            time_text = time_tag.get_attribute("aria-label")
                        except:
                            time_text = ""

                        now = datetime.now()
                        post_time = ""
                        try:
                            if "phút" in time_text:
                                post_time = now - timedelta(minutes=int(re.search(r'(\d+)', time_text).group(1)))
                            elif "giờ" in time_text:
                                post_time = now - timedelta(hours=int(re.search(r'(\d+)', time_text).group(1)))
                            elif "ngày" in time_text:
                                post_time = now - timedelta(days=int(re.search(r'(\d+)', time_text).group(1)))
                            if post_time:
                                post_time = post_time.strftime('%Y-%m-%d %H:%M:%S')
                        except:
                            post_time = ""

                        try:
                            try:
                                see_more = div.find_element(By.XPATH, './/div[text()="Xem thêm"]')
                                browser.execute_script("arguments[0].click();", see_more)
                                sleep(0.5)
                            except:
                                pass
                            content_divs = div.find_elements(By.XPATH, '''
                            .//div[
                                (@tabindex="-1" and contains(@class,"x1lziwak") and contains(@class,"xexx8yu") and not(contains(@class,"x1a2a7pz")))
                                or
                                (contains(@class,"x1lziwak") and contains(@class,"x1vvkbs"))
                            ]
                            ''')
                            if content_divs:
                                full_text = content_divs[0].text.strip()
                                post_text = '\n'.join(full_text.split('\n')[:3])
                            else:
                                post_text = ""
                        except:
                            post_text = ""
                        user_data.append({
                            "UID": uid,
                            "Tên người dùng": name,
                            "Đường dẫn": full_href,
                            "Thời gian đăng bài": post_time,
                            "Nội dung bài viết": post_text
                        })

                        if len(user_data) >= MAX_POSTS:
                            break
                except:
                    continue
            if len(user_data) >= MAX_POSTS:
                break

        browser.quit()

        output_dir = "static/downloads"
        os.makedirs(output_dir, exist_ok=True)
        csv_file = os.path.join(output_dir, f"facebook_group_{group_id}.csv")

        new_df = pd.DataFrame(user_data)
        new_df.drop_duplicates(subset=["UID", "Nội dung bài viết"], inplace=True)

        if os.path.exists(csv_file):
            old_df = pd.read_csv(csv_file)
            combined_df = pd.concat([new_df, old_df], ignore_index=True)
            combined_df.drop_duplicates(subset=["UID", "Nội dung bài viết"], inplace=True)
        else:
            combined_df = new_df

        combined_df['Nội dung bài viết'] = combined_df['Nội dung bài viết'].apply(unidecode)
        combined_df.to_csv(csv_file, index=False, encoding="utf-8-sig")
        elapsed_time = round(time() - start_time, 2)
        file_path = f"facebook_group_{group_id}.csv"

    return render_template('facebook.html', elapsed_time=elapsed_time, file_path=file_path)

@facebook_blueprint.route('/downloads/<filename>')
def download_file(filename):
    return send_from_directory('static/downloads', filename, as_attachment=True)
