import os
from flask import Flask
from flask_cors import CORS


def create_app():
    # Usunięto template_folder i static_folder, ponieważ to teraz tylko API
    app = Flask(__name__)
    CORS(app, origins=['https://iusfully.tojest.dev', 'https://iusfully.tojest.dev/', 'http://localhost:3000', 'http://localhost:5000'])


    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    app.config['UPLOAD_FOLDER'] = os.path.join(BASE_DIR, "input")
    app.config['OUTPUT_FOLDER'] = os.path.join(BASE_DIR, "output")

    for folder in [app.config['UPLOAD_FOLDER'], app.config['OUTPUT_FOLDER']]:
        os.makedirs(folder, exist_ok=True)

    from app.routes.iusfully import iusfully_bp
    from app.auth import auth_bp

    app.register_blueprint(iusfully_bp)
    app.register_blueprint(auth_bp)

    from app.utils.logging_helper import setup_request_logging
    setup_request_logging(app)

    return app
