from flask import Blueprint

api_bp = Blueprint('api', __name__)

from app.api import ocr_routes, template_routes  # noqa: E402, F401
