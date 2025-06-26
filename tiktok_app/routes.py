from flask import Blueprint, render_template, request, send_file, url_for, send_from_directory
import os
from .scraper.hashtag_scraper import scrape_hashtag
from .scraper.profile_scraper import scrape_profiles

tiktok_blueprint = Blueprint('tiktok', __name__,
                             template_folder='templates',
                             static_folder='static')

UPLOAD_FOLDER = 'static/downloads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@tiktok_blueprint.route('/')
def index():
    return render_template('tiktok.html')

@tiktok_blueprint.route('/scrape', methods=['POST'])
def scrape():
    hashtag = request.form['hashtag'].strip().lstrip('#')
    base_filename = f"tiktok_{hashtag}"
    profile_file = os.path.join(UPLOAD_FOLDER, f"{base_filename}_profiles.csv")
    result_file = os.path.join(UPLOAD_FOLDER, f"{base_filename}_stats.csv")

    scrape_hashtag(hashtag, profile_file)
    scrape_profiles(profile_file, result_file)

    download_link = url_for('tiktok.download_file', filename=os.path.basename(result_file))
    return render_template('tiktok.html', download_link=download_link)

@tiktok_blueprint.route('/static/downloads/<filename>')
def download_file(filename):
    path = os.path.join(UPLOAD_FOLDER, filename)
    return send_file(path, as_attachment=True)  
