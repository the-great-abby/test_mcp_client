import os
import ast
import json
import requests
from pathlib import Path

CODE_DIRS = [Path('backend'), Path('app')]
DOCS_DIR = Path('docs')
OUTPUT_FILE = DOCS_DIR / 'code_story.md'
# OLLAMA_URL can be set via environment variable, defaults to Docker host-friendly URL
OLLAMA_URL = os.environ.get('OLLAMA_URL', 'http://host.docker.internal:11434/api/generate')
OLLAMA_MODEL = 'llama2'  # Change to your preferred local model

PROMPT_TEMPLATE = '''
You are a creative technical storyteller. Here is a list of classes and functions from the file {filename}, with their docstrings:
{items}
Write a fun, engaging, and insightful story about how and why these components were created, as if you are narrating the evolution of this part of the codebase. Make it exciting and accessible to both developers and non-developers.
'''

def ensure_docs_dir():
    if not DOCS_DIR.exists():
        DOCS_DIR.mkdir()
        print(f"Created docs/ directory.")

def extract_code_summary(py_file):
    with open(py_file, 'r', encoding='utf-8') as f:
        source = f.read()
    try:
        tree = ast.parse(source)
    except Exception as e:
        return [], f"Parse error: {e}"
    items = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            doc = ast.get_docstring(node)
            items.append(f'- class {node.name}: "{doc or "No docstring"}"')
        elif isinstance(node, ast.FunctionDef):
            doc = ast.get_docstring(node)
            items.append(f'- def {node.name}(): "{doc or "No docstring"}"')
    return items, None

def call_ollama(prompt, model=OLLAMA_MODEL):
    print(f"Calling Ollama at {OLLAMA_URL}")
    data = {
        'model': model,
        'prompt': prompt,
        'stream': False
    }
    try:
        response = requests.post(OLLAMA_URL, json=data)
        response.raise_for_status()
        result = response.json()
        return result.get('response', '').strip()
    except Exception as e:
        return f"[Error calling Ollama: {e}]"

def scan_codebase():
    py_files = []
    for code_dir in CODE_DIRS:
        if code_dir.exists():
            for path, _, files in os.walk(code_dir):
                for file in files:
                    if file.endswith('.py'):
                        py_files.append(Path(path) / file)
    return py_files

def main():
    ensure_docs_dir()
    py_files = scan_codebase()
    stories = []
    for py_file in py_files:
        rel_path = py_file.relative_to(Path('.'))
        items, error = extract_code_summary(py_file)
        if error:
            stories.append(f'## {rel_path}\n> Error: {error}\n---')
            continue
        if not items:
            continue
        prompt = PROMPT_TEMPLATE.format(filename=rel_path, items='\n'.join(items))
        print(f"Generating story for {rel_path}...")
        story = call_ollama(prompt)
        stories.append(f'## {rel_path}\n{story}\n---')
    OUTPUT_FILE.write_text('\n'.join(stories), encoding='utf-8')
    print(f"Generated {OUTPUT_FILE} with stories for {len(stories)} Python files.")
    print("\nTo use a different model, edit OLLAMA_MODEL in generate_code_story.py.")
    print("Ensure Ollama is running locally and the model is pulled (e.g., 'ollama pull llama2').")

if __name__ == '__main__':
    main() 