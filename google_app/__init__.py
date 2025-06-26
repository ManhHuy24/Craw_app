from flask import Blueprint

google_bp = Blueprint('google', __name__, template_folder='../templates')

from . import routes
