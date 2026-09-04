import os
from flask import Flask
from flask_cors import CORS


def create_app():
    # Usunięto template_folder i static_folder, ponieważ to teraz tylko API
    app = Flask(__name__)
    CORS(app, origins=['https://iusfully.tojest.dev', 'https://iusfully.tojest.dev/', 'http://localhost:3000', 'http://localhost:5000'])

    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    from app.api.endpoints import api_bp
    from app.api.auth import auth_bp

    app.register_blueprint(api_bp)
    app.register_blueprint(auth_bp)

    from app.core.logging import setup_request_logging
    setup_request_logging(app)

    @app.route('/healthz')
    def healthz():
        return 'OK', 200

    return app
