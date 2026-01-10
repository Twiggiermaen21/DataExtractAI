import os

class Config:
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "input")
    OUTPUT_FOLDER = os.path.join(BASE_DIR, "output")
    TEMPLATES_FOLDER = os.path.join(BASE_DIR, "docs")
    PROCESSED_TEMPLATES_FOLDER = os.path.join(BASE_DIR, "templates_db")

    @staticmethod
    def init_dirs():
        """Tworzy wymagane foldery, jeśli nie istnieją."""
        os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
        os.makedirs(Config.OUTPUT_FOLDER, exist_ok=True)
        os.makedirs(Config.TEMPLATES_FOLDER, exist_ok=True)
        os.makedirs(Config.PROCESSED_TEMPLATES_FOLDER, exist_ok=True)