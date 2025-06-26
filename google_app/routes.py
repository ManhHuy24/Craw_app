from flask import Blueprint, render_template, request, send_from_directory
import os, time
import pandas as pd
import httpx, requests, re
from bs4 import BeautifulSoup

google_blueprint = Blueprint('google', __name__,
                             template_folder='templates',
                             static_folder='static')

API_KEY = "AIzaSyDBKegSqdzSfGZcfaucon7j-9CHnLDaoKg"
SEARCH_ENGINE_ID = "211161663500d4946"

def clean_phone(phone):
    try:
        if isinstance(phone, float) or isinstance(phone, int):
            phone = str(int(phone))
        else:
            phone = str(phone)

        digits = ''.join(re.findall(r'\d+', phone))

        if len(digits) < 9 or len(digits) > 15:
            return ''
        
        if digits.startswith('0084'):
            digits = '0' + digits[4:]
        elif digits.startswith('84'):
            digits = '0' + digits[2:]

        return "'" + digits
    except:
        return ''

@google_blueprint.route('/', methods=['GET', 'POST'])
def index():
    elapsed_time = None
    file_path = None

    if request.method == 'POST':
        query = request.form['query']
        start_time = time.time()

        search_results = []
        for i in range(1, 100, 10):
            params = {'key': API_KEY, 'cx': SEARCH_ENGINE_ID, 'q': query, 'start': i}
            r = httpx.get('https://www.googleapis.com/customsearch/v1', params=params).json()
            search_results.extend(r.get('items', []))

        df = pd.json_normalize(search_results)[['title', 'displayLink', 'snippet']]
        df.rename(columns={'title': 'Tiêu đề', 'displayLink': 'Đường dẫn', 'snippet': 'Mô tả'}, inplace=True)
        df.drop_duplicates(subset='Tiêu đề', inplace=True)

        df['Địa chỉ'] = ''
        df['Điện thoại'] = ''
        df['Email'] = ''

        for i, row in df.iterrows():
            try:
                url = 'https://' + row['Đường dẫn']
                headers = {'User-Agent': 'Mozilla/5.0'}
                response = requests.get(url, headers=headers, timeout=10)
                soup = BeautifulSoup(response.text, 'html.parser')

                text = soup.get_text(separator=' ', strip=True)
                attributes = ' '.join([str(tag) for tag in soup.find_all()])
                all_content = text + ' ' + attributes

                # Email
                email_matches = re.findall(r'\b\S+@\S+\b', text)

                # Số điện thoại (ưu tiên các dòng chứa từ khóa)
                phone_keywords = ['hotline', 'sđt', 'sdt', 'số điện thoại', 'liên hệ', 'tel']
                phone_lines = [line for line in soup.stripped_strings if any(k in line.lower() for k in phone_keywords)]
                phone_related_text = ' '.join(phone_lines)

                phone_matches = re.findall(r'(?:(?:\+84|0|0084)?(?:[\s\-.]?\d){8,10})', phone_related_text)
                if not phone_matches:
                    phone_matches = re.findall(r'(?:(?:\+84|0|0084)?(?:[\s\-.]?\d){8,10})', all_content)

                tel_links = re.findall(r'tel:(\+?\d{9,15})', all_content)
                phone_matches += tel_links

                cleaned_phones = []
                for p in phone_matches:
                    cleaned = clean_phone(p)
                    if cleaned:
                        cleaned_phones.append(cleaned)

                cleaned_phones = list(dict.fromkeys(cleaned_phones))  # remove duplicates

                # Địa chỉ
                address = ''
                for line in soup.stripped_strings:
                    if any(keyword in line.lower() for keyword in ['địa chỉ', 'address']):
                        address = line
                        break

                # Gán vào DataFrame
                df.at[i, 'Email'] = email_matches[0] if email_matches else ''
                df.at[i, 'Điện thoại'] = cleaned_phones[0] if cleaned_phones else ''
                df.at[i, 'Địa chỉ'] = address

            except Exception as e:
                continue

        safe_query = query.replace(" ", "_")
        filename = f'google_{safe_query}.csv'
        filepath = os.path.join('static/downloads', filename)
        df.to_csv(filepath, index=False, encoding='utf-8-sig')

        elapsed_time = round(time.time() - start_time, 2)
        file_path = filename

    return render_template('google.html', elapsed_time=elapsed_time, file_path=file_path)

@google_blueprint.route('/downloads/<filename>')
def download_file(filename):
    return send_from_directory('static/downloads', filename, as_attachment=True)
