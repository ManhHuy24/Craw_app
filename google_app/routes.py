from flask import Blueprint, render_template, request, send_from_directory
import os, time, re
import pandas as pd
import httpx, requests
from bs4 import BeautifulSoup

google_blueprint = Blueprint('google', __name__,
                             template_folder='templates',
                             static_folder='static')

API_KEY = os.getenv("API_KEY")
SEARCH_ENGINE_ID = os.getenv("SEARCH_ENGINE_ID")

def clean_phone(phone):
    try:
        phone = str(int(phone)) if isinstance(phone, (int, float)) else str(phone)
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
    record_count = 0
    generated_files = []

    if request.method == 'POST':
        start_time = time.time()
        keywords = []

        # Từ input text
        query = request.form.get('query')
        if query:
            keywords.append(query.strip())

        # Từ file upload
        if 'file' in request.files:
            uploaded_file = request.files['file']
            if uploaded_file.filename != '':
                try:
                    ext = os.path.splitext(uploaded_file.filename)[-1].lower()
                    # Đọc từ khóa từ file CSV hoặc Excel
                    if ext == '.csv':
                        df_file = pd.read_csv(uploaded_file, header=None)
                    elif ext in ['.xls', '.xlsx']:
                        df_file = pd.read_excel(uploaded_file, header=None)
                    else:
                        return render_template('index.html', error='Chỉ hỗ trợ file .csv, .xls, .xlsx')

                    # Làm sạch dữ liệu: loại bỏ dòng trống và khoảng trắng
                    file_keywords = df_file.iloc[:, 0].dropna().astype(str).apply(str.strip)
                    keywords += [kw for kw in file_keywords if kw]

                    print("✅ Từ khóa được đọc từ file:", keywords)
                except Exception as e:
                    return render_template('google.html', error=f'Lỗi đọc file: {e}')

        if not keywords:
            return render_template('google.html', error='Không có từ khóa nào để tìm kiếm.')

        os.makedirs('static/downloads', exist_ok=True)

        for keyword in keywords:
            safe_keyword = keyword.replace(" ", "_")
            filename = f'google_{safe_keyword}.csv'
            filepath = os.path.join('static/downloads', filename)

            search_results = []
            start_index = 1
            MAX_RESULTS = 30

            if os.path.exists(filepath):
                old_df = pd.read_csv(filepath)
                already_titles = set(old_df['Tiêu đề'].dropna().unique())
                start_index = len(old_df) + 1
            else:
                old_df = pd.DataFrame()
                already_titles = set()

            # Gọi Google API
            try:
                for i in range(start_index, start_index + MAX_RESULTS, 10):
                    params = {'key': API_KEY, 'cx': SEARCH_ENGINE_ID, 'q': keyword, 'start': i}
                    r = httpx.get('https://www.googleapis.com/customsearch/v1', params=params, timeout=10).json()
                    search_results.extend(r.get('items', []))
            except Exception as e:
                continue

            if not search_results:
                continue

            df_new = pd.json_normalize(search_results)
            if not all(col in df_new.columns for col in ['title', 'displayLink', 'snippet']):
                continue

            df_new = df_new[['title', 'displayLink', 'snippet']]
            df_new.rename(columns={'title': 'Tiêu đề', 'displayLink': 'Đường dẫn', 'snippet': 'Mô tả'}, inplace=True)
            df_new.drop_duplicates(subset='Tiêu đề', inplace=True)
            df_new = df_new[~df_new['Tiêu đề'].isin(already_titles)]

            df = pd.concat([old_df, df_new], ignore_index=True)

            for col in ['Địa chỉ', 'Điện thoại', 'Email']:
                if col not in df.columns:
                    df[col] = ''

            for i, row in df[df['Điện thoại'] == ''].iterrows():
                try:
                    url = 'https://' + row['Đường dẫn']
                    headers = {'User-Agent': 'Mozilla/5.0'}
                    response = requests.get(url, headers=headers, timeout=10)
                    soup = BeautifulSoup(response.text, 'html.parser')

                    text = soup.get_text(separator=' ', strip=True)
                    attributes = ' '.join([str(tag) for tag in soup.find_all()])
                    all_content = text + ' ' + attributes

                    email_matches = re.findall(r'\b\S+@\S+\b', text)

                    phone_keywords = ['hotline', 'sđt', 'sdt', 'số điện thoại', 'liên hệ', 'tel']
                    phone_lines = [line for line in soup.stripped_strings if any(k in line.lower() for k in phone_keywords)]
                    phone_related_text = ' '.join(phone_lines)
                    phone_matches = re.findall(r'(?:(?:\+84|0|0084)?(?:[\s\-.]?\d){8,10})', phone_related_text)
                    if not phone_matches:
                        phone_matches = re.findall(r'(?:(?:\+84|0|0084)?(?:[\s\-.]?\d){8,10})', all_content)
                    tel_links = re.findall(r'tel:(\+?\d{9,15})', all_content)
                    phone_matches += tel_links

                    cleaned_phones = list(dict.fromkeys([clean_phone(p) for p in phone_matches if clean_phone(p)]))

                    address = ''
                    for line in soup.stripped_strings:
                        if any(k in line.lower() for k in ['địa chỉ', 'address']):
                            address = line
                            break

                    df.at[i, 'Email'] = email_matches[0] if email_matches else ''
                    df.at[i, 'Điện thoại'] = cleaned_phones[0] if cleaned_phones else ''
                    df.at[i, 'Địa chỉ'] = address

                except Exception as e:
                    print(f"⚠️ Lỗi khi xử lý {row['Đường dẫn']}: {e}")
                    continue

            df.to_csv(filepath, index=False, encoding='utf-8-sig')
            record_count += len(df)
            generated_files.append(filename)

        elapsed_time = round(time.time() - start_time, 2)

    return render_template('google.html',
                           elapsed_time=elapsed_time,
                           record_count=record_count,
                           generated_files=generated_files)

@google_blueprint.route('/downloads/<filename>')
def download_file(filename):
    return send_from_directory('static/downloads', filename, as_attachment=True)
