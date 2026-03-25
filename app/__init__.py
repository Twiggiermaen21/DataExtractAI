import os
from flask import Flask


def create_app():
    app = Flask(__name__, template_folder='../templates', static_folder='../static')

    # ── Konfiguracja bezpieczeństwa i bazy danych ──────────────────────
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'zmien-mnie-na-losowy-klucz-w-produkcji')
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'instance', 'app.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    app.config['UPLOAD_FOLDER'] = os.path.join(BASE_DIR, "input")
    app.config['OUTPUT_FOLDER'] = os.path.join(BASE_DIR, "output")
    app.config['SAVED_FOLDER'] = os.path.join(BASE_DIR, "saved")
    app.config['TEMPLATES_FOLDER'] = os.path.join(BASE_DIR, "templates", "documents")

    for folder in [app.config['UPLOAD_FOLDER'], app.config['OUTPUT_FOLDER'],
                   app.config['SAVED_FOLDER'], os.path.join(BASE_DIR, 'instance')]:
        os.makedirs(folder, exist_ok=True)

    # ── Inicjalizacja rozszerzeń ───────────────────────────────────────
    from app.extensions import db, login_manager, limiter
    db.init_app(app)
    login_manager.init_app(app)
    limiter.init_app(app)

    # Import modeli, aby SQLAlchemy znało tabele
    from app import models  # noqa: F401

    with app.app_context():
        db.create_all()

    # ── Rejestracja blueprintów ────────────────────────────────────────
    from app.routes.main import main_bp
    from app.routes.ocr import ocr_bp
    from app.routes.llm import llm_bp
    from app.routes.wezwania import wezwania_bp
    from app.routes.pozew import pozew_bp
    from app.routes.templates import templates_bp
    from app.routes.invoices import invoices_bp
    from app.routes.excel_export import excel_export_bp
    from app.routes.auth import auth_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(ocr_bp)
    app.register_blueprint(llm_bp)
    app.register_blueprint(wezwania_bp)
    app.register_blueprint(pozew_bp)
    app.register_blueprint(templates_bp)
    app.register_blueprint(invoices_bp)
    app.register_blueprint(excel_export_bp)
    app.register_blueprint(auth_bp)

    return app
