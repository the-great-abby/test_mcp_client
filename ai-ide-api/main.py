from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
import os
import yaml
import json

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