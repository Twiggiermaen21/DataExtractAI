from app.routes.auth import auth_bp
from app.routes.excel_export import excel_export_bp

from app.routes.ocr import ocr_bp
from app.routes.pages import pages_bp
from app.routes.settings import settings_bp
from app.routes.templates import templates_bp

WEB_BLUEPRINTS = (
    pages_bp,
    auth_bp,
)

API_BLUEPRINTS = (
    ocr_bp,

    templates_bp,
    excel_export_bp,
    settings_bp,
)


def register_blueprints(app):
    """Register all Flask blueprints in a single, explicit place."""
    for blueprint in WEB_BLUEPRINTS + API_BLUEPRINTS:
        app.register_blueprint(blueprint)
