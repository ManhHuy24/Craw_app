from flask import Blueprint, render_template, request, send_from_directory
import os, time
import pandas as pd
import httpx, requests, re
from bs4 import BeautifulSoup

google_blueprint = Blueprint('google', __name__,
                             template_folder='templates',
                             static_folder='static')

API_KEY = os.getenv("API_KEY")
SEARCH_ENGINE_ID = os.getenv("SEARCH_ENGINE_ID")

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
    record_count = None

    if request.method == 'POST':
        query = request.form.get('query')
        if not query:
            return render_template('google.html', error='Vui lòng nhập từ khóa.')

        start_time = time.time()
        search_results = []
        MAX_RESULTS = 30
        start_index = 1

        # Đường dẫn lưu file kết quả
        os.makedirs('static/downloads', exist_ok=True)
        safe_query = query.replace(" ", "_")
        filename = f'google_{safe_query}.csv'
        filepath = os.path.join('static/downloads', filename)

        # Nếu file đã tồn tại, đọc dữ liệu cũ
        if os.path.exists(filepath):
            old_df = pd.read_csv(filepath)
            already_titles = set(old_df['Tiêu đề'].dropna().unique())
            start_index = len(old_df) + 1
        else:
            old_df = pd.DataFrame()
            already_titles = set()

        # Gửi yêu cầu đến Google API (giới hạn 30 dòng mới)
        try:
            for i in range(start_index, start_index + MAX_RESULTS, 10):
                params = {'key': API_KEY, 'cx': SEARCH_ENGINE_ID, 'q': query, 'start': i}
                r = httpx.get('https://www.googleapis.com/customsearch/v1', params=params, timeout=10).json()
                new_items = r.get('items', [])
                search_results.extend(new_items)
        except Exception as e:
            return render_template('google.html', error=f'Lỗi khi gọi Google API: {e}')

        if not search_results:
            return render_template('google.html', error='Không tìm thấy kết quả mới.')

        # Chuyển sang DataFrame
        new_df = pd.json_normalize(search_results)
        expected_cols = ['title', 'displayLink', 'snippet']
        if not all(col in new_df.columns for col in expected_cols):
            return render_template('google.html', error='Dữ liệu trả về không hợp lệ.')

        new_df = new_df[expected_cols]
        new_df.rename(columns={'title': 'Tiêu đề', 'displayLink': 'Đường dẫn', 'snippet': 'Mô tả'}, inplace=True)
        new_df.drop_duplicates(subset='Tiêu đề', inplace=True)

        # Loại bỏ các dòng đã có sẵn
        new_df = new_df[~new_df['Tiêu đề'].isin(already_titles)]

        # Gộp vào dataframe tổng
        df = pd.concat([old_df, new_df], ignore_index=True)

        # Thêm cột nếu chưa có
        for col in ['Địa chỉ', 'Điện thoại', 'Email']:
            if col not in df.columns:
                df[col] = ''

        # Chỉ xử lý những dòng mới thêm chưa có dữ liệu
        for i, row in df[df['Điện thoại'] == ''].iterrows():
            try:
                url = 'https://' + row['Đường dẫn']
                headers = {'User-Agent': 'Mozilla/5.0'}
                response = requests.get(url, headers=headers, timeout=10)
                soup = BeautifulSoup(response.text, 'html.parser')

                text = soup.get_text(separator=' ', strip=True)
                attributes = ' '.join([str(tag) for tag in soup.find_all()])
                all_content = text + ' ' + attributes

                # Tìm email
                email_matches = re.findall(r'\b\S+@\S+\b', text)

                # Tìm số điện thoại
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

                cleaned_phones = list(dict.fromkeys(cleaned_phones))

                # Tìm địa chỉ
                address = ''
                for line in soup.stripped_strings:
                    if any(keyword in line.lower() for keyword in ['địa chỉ', 'address']):
                        address = line
                        break

                df.at[i, 'Email'] = email_matches[0] if email_matches else ''
                df.at[i, 'Điện thoại'] = cleaned_phones[0] if cleaned_phones else ''
                df.at[i, 'Địa chỉ'] = address

            except Exception as e:
                print(f"⚠️ Lỗi khi xử lý {row['Đường dẫn']}: {e}")
                continue

        # Ghi lại file
        df.to_csv(filepath, index=False, encoding='utf-8-sig')

        elapsed_time = round(time.time() - start_time, 2)
        file_path = filename
        record_count = len(df)

    return render_template('google.html', elapsed_time=elapsed_time, file_path=file_path, record_count=record_count)

@google_blueprint.route('/downloads/<filename>')
def download_file(filename):
    return send_from_directory('static/downloads', filename, as_attachment=True)
