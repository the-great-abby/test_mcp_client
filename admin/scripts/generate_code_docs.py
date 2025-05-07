import os
import ast
from pathlib import Path

PROJECT_ROOT = Path(os.environ.get('PROJECT_ROOT', '/mnt/actual_code'))
CODE_DIRS = [PROJECT_ROOT / 'backend', PROJECT_ROOT / 'app']
DOCS_DIR = PROJECT_ROOT / 'docs'
OUTPUT_FILE = DOCS_DIR / 'code_index.md'


def ensure_docs_dir():
    if not DOCS_DIR.exists():
        DOCS_DIR.mkdir()
        print(f"Created docs/ directory.")

def extract_docstrings_from_file(py_file):
    with open(py_file, 'r', encoding='utf-8') as f:
        source = f.read()
    try:
        tree = ast.parse(source)
    except Exception as e:
        return None, [], [], f"Parse error: {e}"
    module_doc = ast.get_docstring(tree)
    classes = []
    functions = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            doc = ast.get_docstring(node)
            classes.append((node.name, doc))
        elif isinstance(node, ast.FunctionDef):
            doc = ast.get_docstring(node)
            functions.append((node.name, doc))
    return module_doc, classes, functions, None

def scan_codebase():
    py_files = []
    for code_dir in CODE_DIRS:
        if code_dir.exists():
            for path, _, files in os.walk(code_dir):
                for file in files:
                    if file.endswith('.py'):
                        py_files.append(Path(path) / file)
    return py_files

def generate_markdown(docs):
    lines = ['# Code Documentation Index\n']
    for py_file, (module_doc, classes, functions, error) in docs.items():
        lines.append(f'## {py_file}')
        if error:
            lines.append(f'> Error parsing file: {error}\n')
            continue
        if module_doc:
            lines.append('### Module Docstring')
            lines.append(module_doc + '\n')
        if classes:
            lines.append('### Classes')
            for cname, cdoc in classes:
                lines.append(f'#### class {cname}')
                lines.append((cdoc or '_No docstring_') + '\n')
        if functions:
            lines.append('### Functions')
            for fname, fdoc in functions:
                lines.append(f'#### def {fname}()')
                lines.append((fdoc or '_No docstring_') + '\n')
        lines.append('---')
    return '\n'.join(lines)

def main():
    ensure_docs_dir()
    py_files = scan_codebase()
    docs = {}
    for py_file in py_files:
        rel_path = py_file.relative_to(PROJECT_ROOT)
        docs[str(rel_path)] = extract_docstrings_from_file(py_file)
    md = generate_markdown(docs)
    OUTPUT_FILE.write_text(md, encoding='utf-8')
    print(f"Generated {OUTPUT_FILE} with documentation for {len(py_files)} Python files.")

if __name__ == '__main__':
    main() 