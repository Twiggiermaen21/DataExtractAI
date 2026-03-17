import os
from flask import Flask


def create_app():
    app = Flask(__name__, template_folder='../templates', static_folder='../static')

    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    app.config['UPLOAD_FOLDER'] = os.path.join(BASE_DIR, "input")
    app.config['OUTPUT_FOLDER'] = os.path.join(BASE_DIR, "output")
    app.config['SAVED_FOLDER'] = os.path.join(BASE_DIR, "saved")
    app.config['TEMPLATES_FOLDER'] = os.path.join(BASE_DIR, "templates", "documents")

    for folder in [app.config['UPLOAD_FOLDER'], app.config['OUTPUT_FOLDER'], app.config['SAVED_FOLDER']]:
        os.makedirs(folder, exist_ok=True)

    from app.routes.main import main_bp
    from app.routes.ocr import ocr_bp
    from app.routes.llm import llm_bp
    from app.routes.wezwania import wezwania_bp
    from app.routes.pozew import pozew_bp
    from app.routes.templates import templates_bp
    from app.routes.invoices import invoices_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(ocr_bp)
    app.register_blueprint(llm_bp)
    app.register_blueprint(wezwania_bp)
    app.register_blueprint(pozew_bp)
    app.register_blueprint(templates_bp)
    app.register_blueprint(invoices_bp)

    return app
