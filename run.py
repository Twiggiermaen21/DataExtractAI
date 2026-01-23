from app import create_app

app = create_app()

if __name__ == '__main__':
    # use_reloader=False to prevent restarts when PaddleOCR modifies files in .venv
    app.run(debug=True, port=5000, use_reloader=False)