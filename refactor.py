import os
import shutil

app_dir = r"d:\antygravity\ocr+dokumenty\DataExtractAI\app"
base_dir = r"d:\antygravity\ocr+dokumenty\DataExtractAI"

os.makedirs(os.path.join(app_dir, "api"), exist_ok=True)
os.makedirs(os.path.join(app_dir, "core"), exist_ok=True)

moves = {
    r"app\routes\iusfully.py": r"app\api\endpoints.py",
    r"app\auth.py": r"app\api\auth.py",
    r"app\services\iusfully_template_service.py": r"app\services\template_service.py",
    r"app\services\ocr_llm_service.py": r"app\services\ocr_service.py",
    r"app\utils\logging_helper.py": r"app\core\logging.py",
}

for src, dst in moves.items():
    src_path = os.path.join(base_dir, src)
    dst_path = os.path.join(base_dir, dst)
    if os.path.exists(src_path):
        shutil.move(src_path, dst_path)

deletions = [
    r"app\services\llm_service.py",
    r"app\services\wezwania_service.py",
    r"app\utils\helpers.py",
    r"app\routes",
]
for d in deletions:
    p = os.path.join(base_dir, d)
    if os.path.exists(p):
        if os.path.isdir(p):
            shutil.rmtree(p)
        else:
            os.remove(p)

def update_imports(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    replacements = {
        "app.routes.iusfully": "app.api.endpoints",
        "app.auth": "app.api.auth",
        "app.services.iusfully_template_service": "app.services.template_service",
        "app.services.ocr_llm_service": "app.services.ocr_service",
        "app.utils.logging_helper": "app.core.logging",
        "iusfully_bp": "api_bp",
        "Blueprint('iusfully'": "Blueprint('api'",
    }
    
    new_content = content
    for k, v in replacements.items():
        new_content = new_content.replace(k, v)
        
    if new_content != content:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)

for root, _, files in os.walk(app_dir):
    for f in files:
        if f.endswith(".py"):
            update_imports(os.path.join(root, f))
            
update_imports(os.path.join(base_dir, "run.py"))

