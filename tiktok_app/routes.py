from flask import Blueprint, render_template, request, send_from_directory
import os, time
import pandas as pd
from .scraper.hashtag_scraper import scrape_hashtag
from .scraper.profile_scraper import scrape_profiles

base_dir = os.path.dirname(os.path.abspath(__file__))

tiktok_blueprint = Blueprint('tiktok', __name__,
    template_folder=os.path.join(base_dir, 'templates'),
    static_folder=os.path.join(base_dir, '..', 'static')
)

DOWNLOAD_FOLDER = os.path.join(base_dir, '..', 'static', 'downloads')
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

@tiktok_blueprint.route('/', methods=['GET', 'POST'])
def index():
    elapsed_time = None
    file_path = None
    record_count = 0
    show_load_more = False
    MAX_TOTAL = 200
    BATCH_SIZE = 20
    hashtag = ''
    offset = 0

    if request.method == 'POST':
        hashtag = request.form.get('hashtag', '').strip().lstrip('#')
        offset = int(request.form.get('offset', 0))

        if not hashtag:
            return render_template('tiktok.html', error='Vui lòng nhập hashtag.', hashtag=hashtag, offset=offset, show_load_more=False)

        start_time = time.time()
        filename = f"tiktok_{hashtag}.csv"
        filepath = os.path.join(DOWNLOAD_FOLDER, filename)

        # Đọc dữ liệu cũ nếu có
        if os.path.exists(filepath):
            old_df = pd.read_csv(filepath)
            old_usernames = set(old_df['Username'].dropna().unique())
        else:
            old_df = pd.DataFrame()
            old_usernames = set()

        current_count = len(old_usernames)
        if current_count >= MAX_TOTAL:
            return render_template('tiktok.html', file_path=filename, record_count=current_count, elapsed_time=0, show_load_more=False, hashtag=hashtag, offset=offset)

        scraped_data = scrape_hashtag(hashtag, max_videos=current_count + BATCH_SIZE)
        new_data = [d for d in scraped_data if d['Username'] not in old_usernames]

        csv_path = os.path.join('downloads', f'{hashtag}.csv')
        csv_exists = os.path.exists(csv_path)

        if not new_data:
            return render_template('tiktok.html', error='Không tìm thấy kênh mới nào.', hashtag=hashtag, offset=offset, show_load_more=False, csv_exists=csv_exists)

        df_new = pd.DataFrame(new_data)

        for col in ['Following', 'Followers', 'Likes', 'Bio']:
            if col not in old_df.columns:
                old_df[col] = ''
            if col not in df_new.columns:
                df_new[col] = ''

        combined_df = pd.concat([old_df, df_new], ignore_index=True)

        # Cào chi tiết profile nếu thiếu thông tin
        # to_scrape = combined_df[combined_df['Followers'] == '']
        # if not to_scrape.empty:
        #     temp_file = os.path.join(DOWNLOAD_FOLDER, f"_temp_{hashtag}.csv")
        #     to_scrape.to_csv(temp_file, index=False, encoding='utf-8-sig')
        #     scrape_profiles(temp_file, temp_file)
        #     scraped_profile_df = pd.read_csv(temp_file)
        #     scraped_profile_df.set_index('Profile URL', inplace=True)
        #     combined_df.set_index('Profile URL', inplace=True)
        #     combined_df.update(scraped_profile_df)
        #     combined_df.reset_index(inplace=True)
        #     os.remove(temp_file)

        # Giới hạn tối đa MAX_TOTAL dòng
        combined_df = combined_df.drop_duplicates(subset='Username').head(MAX_TOTAL)

        combined_df.to_csv(filepath, index=False, encoding='utf-8-sig')
        elapsed_time = round(time.time() - start_time, 2)
        file_path = filename
        record_count = len(combined_df)
        show_load_more = record_count < MAX_TOTAL

    return render_template(
        'tiktok.html',
        elapsed_time=elapsed_time,
        file_path=file_path,
        record_count=record_count,
        show_load_more=show_load_more,
        hashtag=hashtag,
        offset=offset
    )

@tiktok_blueprint.route('/downloads/<filename>')
def download_file(filename):
    return send_from_directory('static/downloads', filename, as_attachment=True)
