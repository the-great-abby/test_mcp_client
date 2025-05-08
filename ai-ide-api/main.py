from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
import os
import yaml
import json
import datetime

app = FastAPI(title="AI-IDE Onboarding API")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(BASE_DIR, '..'))

@app.get("/metadata")
def get_metadata():
    yaml_path = os.path.join(ROOT_DIR, "onboarding.yaml")
    json_path = os.path.join(ROOT_DIR, ".ai-ide-config.json")
    data = {}
    if os.path.exists(yaml_path):
        with open(yaml_path) as f:
            data["onboarding_yaml"] = yaml.safe_load(f)
    if os.path.exists(json_path):
        with open(json_path) as f:
            data["ai_ide_config_json"] = json.load(f)
    return JSONResponse(data)

@app.get("/rules")
def list_rules():
    rules_index = os.path.join(ROOT_DIR, "docs/rules_index.md")
    rules = []
    if os.path.exists(rules_index):
        with open(rules_index) as f:
            for line in f:
                if line.startswith("| ["):
                    parts = line.split("|")
                    if len(parts) > 2:
                        rule_file = parts[1].split(']')[0].split('[')[-1]
                        title = parts[2].strip()
                        desc = parts[3].strip() if len(parts) > 3 else ''
                        rules.append({"file": rule_file, "title": title, "description": desc})
    return {"rules": rules}

@app.get("/rules/{rule_name}")
def get_rule(rule_name: str):
    rule_path = os.path.join(ROOT_DIR, ".cursor/rules", rule_name)
    if not os.path.exists(rule_path):
        raise HTTPException(status_code=404, detail="Rule not found")
    with open(rule_path) as f:
        content = f.read()
    return {"file": rule_name, "content": content}

@app.get("/knowledge-graph")
def get_knowledge_graph():
    kg_path = os.path.join(ROOT_DIR, "docs/cursor_knowledge_graph.json")
    if not os.path.exists(kg_path):
        raise HTTPException(status_code=404, detail="Knowledge graph not found")
    with open(kg_path) as f:
        data = json.load(f)
    return data

@app.get("/docs/{doc_name}")
def get_doc(doc_name: str):
    doc_path = os.path.join(ROOT_DIR, "docs", doc_name)
    if not os.path.exists(doc_path):
        raise HTTPException(status_code=404, detail="Doc not found")
    return FileResponse(doc_path)

@app.get("/onboarding-quiz")
def get_onboarding_quiz():
    quiz_path = os.path.join(ROOT_DIR, "onboarding_quiz.md")
    if not os.path.exists(quiz_path):
        raise HTTPException(status_code=404, detail="Onboarding quiz not found")
    with open(quiz_path, "r") as f:
        content = f.read()
    return PlainTextResponse(content, media_type="text/markdown")

@app.post("/onboarding-quiz/check")
async def check_onboarding_quiz(request: Request):
    data = await request.json()
    answers = data.get("answers", {})
    answer_key_path = os.path.join(ROOT_DIR, "onboarding_quiz_answers.json")
    if not os.path.exists(answer_key_path):
        raise HTTPException(status_code=500, detail="Answer key not found")
    with open(answer_key_path) as f:
        answer_key = json.load(f)
    # Optional: explanations or doc links for each question
    explanations = {
        "1": "See pytest execution rules in WELCOME.md and Makefile.ai.",
        "2": "All required environment variables are listed in .env.example.",
        "3": "Project rules are indexed in docs/rules_index.md.",
        "4": "Use bash validate_env.sh to check your .env file.",
        "5": "Tests must use Docker service names and internal ports, not localhost.",
        "6": "System architecture is documented in docs/architecture.md.",
        "7": "Contribute by editing docs or opening a PR. See CONTRIBUTING.md.",
        "8": "ai_onboarding_checklist.sh checks for missing onboarding/config files.",
        "9": "Troubleshooting tips are in KNOWN_ISSUES.md and docs/env_troubleshooting.md.",
        "10": "Feedback can be submitted with submit_onboarding_feedback.sh or by opening an issue."
    }
    results = {}
    for q, user_answer in answers.items():
        correct = answer_key.get(q, "").strip().lower()
        user = user_answer.strip().lower()
        results[q] = {
            "correct": user == correct,
            "expected": answer_key.get(q, ""),
            "explanation": explanations.get(q, "")
        }
    return results

@app.get("/ai-ide-self-test")
def ai_ide_self_test():
    config_path = os.path.join(ROOT_DIR, ".ai-ide-config.json")
    if not os.path.exists(config_path):
        raise HTTPException(status_code=500, detail=".ai-ide-config.json not found")
    with open(config_path) as f:
        config = json.load(f)
    # Gather all unique file paths from config
    files = set()
    for key, value in config.items():
        if isinstance(value, str) and value.endswith(('.md', '.sh', '.json', '.yaml', '.yml', '.ai', '.toml')):
            files.add(value)
        elif isinstance(value, list):
            for v in value:
                if isinstance(v, str) and v.endswith(('.md', '.sh', '.json', '.yaml', '.yml', '.ai', '.toml')):
                    files.add(v)
    # Check presence and last modified date
    checklist = []
    for fpath in sorted(files):
        abs_path = os.path.join(ROOT_DIR, fpath)
        present = os.path.exists(abs_path)
        last_modified = None
        if present:
            ts = os.path.getmtime(abs_path)
            last_modified = datetime.datetime.fromtimestamp(ts).isoformat()
        checklist.append({
            "file": fpath,
            "present": present,
            "last_modified": last_modified
        })
    return {"checklist": checklist, "config_version": config.get("version")}

@app.get("/ai-ide-suggestions")
def ai_ide_suggestions():
    log_path = os.path.join(ROOT_DIR, "ai_ide_analytics.log")
    suggestions = []
    events = set()
    if os.path.exists(log_path):
        with open(log_path) as f:
            for line in f:
                parts = line.strip().split(',')
                if len(parts) > 1:
                    events.add(parts[1])
    # Suggest onboarding checklist if not completed
    if "onboarding_completed" not in events:
        suggestions.append("You haven't completed onboarding yet. Run 'bash onboarding_checklist.sh' to get started.")
    # Suggest .env validation
    if "validated_env" not in events:
        suggestions.append("You haven't validated your .env. Run 'bash validate_env.sh' to check for missing variables.")
    # Suggest running tests
    if "ran_tests" not in events and "ai-test" not in events:
        suggestions.append("You haven't run the test suite. Use 'make -f Makefile.ai ai-test PYTEST_ARGS=\"-x\"'.")
    # Suggest troubleshooting wizard if test failures or issues
    if "test_failed" in events or "troubleshooting_needed" in events:
        suggestions.append("You may want to run 'bash onboarding_wizard.sh' for troubleshooting tips.")
    # Suggest submitting feedback
    if "feedback_submitted" not in events:
        suggestions.append("Help us improve onboarding by running 'bash submit_onboarding_feedback.sh'.")
    # Suggest reading rules index
    if "read_rules" not in events:
        suggestions.append("Check out the project rules in 'docs/rules_index.md' for best practices.")
    # Suggest running analytics script
    if "onboarding_started" not in events:
        suggestions.append("Log your onboarding progress with 'bash ai_ide_analytics.sh onboarding_started <user_type>'.")
    if not suggestions:
        suggestions.append("🎉 All key onboarding steps detected! You're ready to contribute.")
    return {"suggestions": suggestions} 