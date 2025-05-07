import os
import subprocess
import requests
from pathlib import Path

PROJECT_ROOT = Path(os.environ.get('PROJECT_ROOT', '/mnt/actual_code'))
CODE_DIRS = [PROJECT_ROOT / 'backend', PROJECT_ROOT / 'app']
DOCS_DIR = PROJECT_ROOT / 'docs'
OUTPUT_FILE = DOCS_DIR / 'request_lifecycle_story.md'
# OLLAMA_URL can be set via environment variable, defaults to Docker host-friendly URL
OLLAMA_URL = os.environ.get('OLLAMA_URL', 'http://host.docker.internal:11434/api/generate')
OLLAMA_MODEL = 'llama2'  # Change to your preferred local model

CTAGS_CMD = [
    'ctags',
    '-R',
    '--fields=+n',  # Include line numbers
    '--languages=Python',
    '--output-format=json',
]

PROMPT_TEMPLATE = '''
You are a creative technical storyteller. Here is a map of how a request travels through our system, based on the code structure:
{chapters}
Write a fun, engaging, and insightful story about the journey of a request, describing each chapter and the possible adventures (success, error, async, etc). Make it accessible to both developers and non-developers.
'''

def ensure_docs_dir():
    if not DOCS_DIR.exists():
        DOCS_DIR.mkdir()
        print(f"Created docs/ directory.")

def run_ctags():
    tags = []
    for code_dir in CODE_DIRS:
        if code_dir.exists():
            cmd = CTAGS_CMD + [str(code_dir)]
            print(f"Running ctags on {code_dir}...")
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"ctags error: {result.stderr}")
                continue
            # ctags outputs one JSON object per line
            for line in result.stdout.splitlines():
                try:
                    tag = eval(line)  # ctags json is not always strict, so use eval
                    tags.append(tag)
                except Exception:
                    continue
    return tags

def build_lifecycle_chapters(tags):
    # Find likely entrypoints (FastAPI endpoints, main functions)
    chapters = []
    endpoints = [t for t in tags if t.get('name', '').startswith('api_') or 'endpoint' in t.get('name', '').lower()]
    mains = [t for t in tags if t.get('name') == 'main' or t.get('name', '').startswith('start_')]
    if endpoints:
        for ep in endpoints:
            chapters.append(f"Chapter: Entry at {ep['name']} (file: {ep['path']}, line: {ep['line']})")
    if mains:
        for m in mains:
            chapters.append(f"Chapter: Main entrypoint {m['name']} (file: {m['path']}, line: {m['line']})")
    # Add some classes/functions as possible chapters
    for t in tags:
        if t['kind'] == 'class':
            chapters.append(f"Chapter: Class {t['name']} (file: {t['path']}, line: {t['line']})")
        elif t['kind'] == 'function' and t['name'] not in [ep['name'] for ep in endpoints + mains]:
            chapters.append(f"Chapter: Function {t['name']} (file: {t['path']}, line: {t['line']})")
    return '\n'.join(chapters)

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

def main():
    ensure_docs_dir()
    tags = run_ctags()
    if not tags:
        print("No tags found. Is ctags installed and code present?")
        return
    chapters = build_lifecycle_chapters(tags)
    prompt = PROMPT_TEMPLATE.format(chapters=chapters)
    print("Generating request lifecycle story with Ollama...")
    story = call_ollama(prompt)
    OUTPUT_FILE.write_text(story, encoding='utf-8')
    print(f"Generated {OUTPUT_FILE} with the request lifecycle story.")
    print("\nTo use a different model, edit OLLAMA_MODEL in generate_request_lifecycle_story.py.")
    print("Ensure Ollama is running locally and the model is pulled (e.g., 'ollama pull llama2').")

if __name__ == '__main__':
    main() 