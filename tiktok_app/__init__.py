from flask import Blueprint

tiktok_bp = Blueprint('tiktok', __name__, template_folder='../templates')

from . import routes
