from flask import Blueprint

facebook_bp = Blueprint('facebook', __name__, template_folder='../templates')

from . import routes