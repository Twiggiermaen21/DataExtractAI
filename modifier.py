import ast
import os

def process_file(filepath):
    print(f"Modifying {filepath}")
    with open(filepath, 'r', encoding='utf-8') as f:
        source = f.read()

    try:
        tree = ast.parse(source)
    except Exception as e:
        print(f"Syntax error in {filepath}: {e}")
        return

    funcs = [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    
    # Find all Expr nodes that are calls to print
    print_exprs = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Expr):
            if isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name) and node.value.func.id == 'print':
                print_exprs.append(node)

    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    modifications = {}

    for expr in print_exprs:
        indent = len(lines[expr.lineno - 1]) - len(lines[expr.lineno - 1].lstrip())
        modifications[expr.lineno - 1] = " " * indent + "pass  # usuniety print\n"
        for i in range(expr.lineno, expr.end_lineno):
            modifications[i] = ""

    insertions = {}
    for f in funcs:
        body = f.body
        if not body: continue
        
        first_stmt = body[0]
        if isinstance(first_stmt, ast.Expr) and isinstance(first_stmt.value, ast.Constant) and isinstance(first_stmt.value.value, str):
            insert_lineno = first_stmt.end_lineno
            if len(body) > 1:
                next_stmt = body[1]
                indent = len(lines[next_stmt.lineno - 1]) - len(lines[next_stmt.lineno - 1].lstrip())
            else:
                indent = len(lines[first_stmt.lineno - 1]) - len(lines[first_stmt.lineno - 1].lstrip())
        else:
            insert_lineno = first_stmt.lineno - 1
            indent = len(lines[first_stmt.lineno - 1]) - len(lines[first_stmt.lineno - 1].lstrip())
            
        indent_str = " " * indent
        insertions.setdefault(insert_lineno, []).append(f'{indent_str}print("Wywołano funkcję: {f.name}")\n')
        
    new_lines = []
    for i, line in enumerate(lines):
        if i in insertions:
            for ins in insertions[i]:
                new_lines.append(ins)
            
        if i in modifications:
            new_lines.append(modifications[i])
        else:
            new_lines.append(line)
            
    # Also append if insertion is at the very end (unlikely but possible)
    if len(lines) in insertions:
        for ins in insertions[len(lines)]:
            new_lines.append(ins)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)

# Process files
search_dirs = [
    r"d:\visualstudio\ocr2\app\routes",
    r"d:\visualstudio\ocr2\app\services",
    r"d:\visualstudio\ocr2\app\utils"
]

for d in search_dirs:
    for root, _, files in os.walk(d):
        for file in files:
            if file.endswith('.py'):
                process_file(os.path.join(root, file))

process_file(r"d:\visualstudio\ocr2\app\__init__.py")
# We will not process run.py to keep the startup message
