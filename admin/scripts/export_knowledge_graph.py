import os
import json
import sys

MERMAID_MD = '''# Project Knowledge Graph (Mermaid)

Below is a Mermaid diagram representing the architecture, workflows, features, and relationships in this project. You can view this diagram in any Mermaid-compatible Markdown viewer (e.g., GitHub, VS Code with Mermaid plugin, Obsidian, or mermaid.live).

```mermaid
graph TD
  %% Core Components
  mcp_chat_client["mcp_chat_client (project)"]
  backend["backend (FastAPI)"]
  admin_ui["admin-ui (SvelteKit)"]
  database["database (PostgreSQL)"]
  redis["redis (cache)"]
  test_environment["test_environment (Docker Compose)"]

  %% Workflows
  test_workflow["test_workflow"]
  dev_workflow["dev_workflow"]
  build_workflow["build_workflow"]
  ci_cd["ci_cd"]
  auth_flow["auth_flow"]

  %% Features/APIs
  admin_endpoints["admin_endpoints"]
  rate_limiting["rate_limiting"]
  metrics_dashboard["metrics_dashboard"]
  user_management["user_management"]
  audit_log["audit_log"]
  websocket_support["websocket_support"]

  %% Cross-Cutting Concerns
  security["security"]
  observability["observability"]
  error_handling["error_handling"]
  performance["performance"]

  %% Documentation
  docs["docs"]

  %% Core Relationships
  backend -->|uses| database
  backend -->|uses| redis
  admin_ui -->|calls| admin_endpoints
  admin_ui -->|displays| metrics_dashboard
  admin_ui -->|manages| user_management
  admin_ui -->|shows| audit_log
  backend -->|exposes| websocket_support

  %% Workflow Relationships
  test_workflow -->|runs on| test_environment
  dev_workflow -->|runs on| backend
  dev_workflow -->|runs on| admin_ui
  dev_workflow -->|runs on| database
  dev_workflow -->|runs on| redis
  build_workflow -->|builds| backend
  build_workflow -->|builds| admin_ui
  ci_cd -->|deploys| backend
  ci_cd -->|deploys| admin_ui

  %% Feature/API Relationships
  admin_endpoints -->|implement| rate_limiting
  admin_endpoints -->|implement| metrics_dashboard
  admin_endpoints -->|implement| user_management
  admin_endpoints -->|implement| audit_log
  admin_endpoints -->|support| websocket_support

  %% Cross-Cutting Concerns
  backend -->|enforces| security
  backend -->|provides| observability
  backend -->|handles| error_handling
  backend -->|optimizes| performance
  admin_ui -->|enforces| security
  admin_ui -->|handles| error_handling

  %% Documentation
  docs -->|documents| backend
  docs -->|documents| admin_ui
  docs -->|documents| admin_endpoints
  docs -->|documents| test_workflow
  docs -->|documents| dev_workflow

  %% Auth Relationships
  auth_flow -->|protects| admin_endpoints
  auth_flow -->|protects| admin_ui

  %% Testing Relationships
  test_workflow -->|tests| backend
  test_workflow -->|tests| admin_endpoints
  test_workflow -->|tests| admin_ui
  test_workflow -->|tests| websocket_support

  %% Feature-to-Concern
  rate_limiting -->|improves| security
  metrics_dashboard -->|improves| observability
  audit_log -->|improves| security
  audit_log -->|improves| observability
```
'''

# JSON graph structure
NODES = [
    {"id": "mcp_chat_client", "label": "mcp_chat_client (project)", "type": "project"},
    {"id": "backend", "label": "backend (FastAPI)", "type": "service"},
    {"id": "admin_ui", "label": "admin-ui (SvelteKit)", "type": "service"},
    {"id": "database", "label": "database (PostgreSQL)", "type": "database"},
    {"id": "redis", "label": "redis (cache)", "type": "cache"},
    {"id": "test_environment", "label": "test_environment (Docker Compose)", "type": "infra"},
    {"id": "test_workflow", "label": "test_workflow", "type": "workflow"},
    {"id": "dev_workflow", "label": "dev_workflow", "type": "workflow"},
    {"id": "build_workflow", "label": "build_workflow", "type": "workflow"},
    {"id": "ci_cd", "label": "ci_cd", "type": "workflow"},
    {"id": "auth_flow", "label": "auth_flow", "type": "workflow"},
    {"id": "admin_endpoints", "label": "admin_endpoints", "type": "api"},
    {"id": "rate_limiting", "label": "rate_limiting", "type": "feature"},
    {"id": "metrics_dashboard", "label": "metrics_dashboard", "type": "feature"},
    {"id": "user_management", "label": "user_management", "type": "feature"},
    {"id": "audit_log", "label": "audit_log", "type": "feature"},
    {"id": "websocket_support", "label": "websocket_support", "type": "feature"},
    {"id": "security", "label": "security", "type": "concern"},
    {"id": "observability", "label": "observability", "type": "concern"},
    {"id": "error_handling", "label": "error_handling", "type": "concern"},
    {"id": "performance", "label": "performance", "type": "concern"},
    {"id": "docs", "label": "docs", "type": "docs"},
]

EDGES = [
    # Core Relationships
    {"from": "backend", "to": "database", "label": "uses"},
    {"from": "backend", "to": "redis", "label": "uses"},
    {"from": "admin_ui", "to": "admin_endpoints", "label": "calls"},
    {"from": "admin_ui", "to": "metrics_dashboard", "label": "displays"},
    {"from": "admin_ui", "to": "user_management", "label": "manages"},
    {"from": "admin_ui", "to": "audit_log", "label": "shows"},
    {"from": "backend", "to": "websocket_support", "label": "exposes"},
    # Workflow Relationships
    {"from": "test_workflow", "to": "test_environment", "label": "runs on"},
    {"from": "dev_workflow", "to": "backend", "label": "runs on"},
    {"from": "dev_workflow", "to": "admin_ui", "label": "runs on"},
    {"from": "dev_workflow", "to": "database", "label": "runs on"},
    {"from": "dev_workflow", "to": "redis", "label": "runs on"},
    {"from": "build_workflow", "to": "backend", "label": "builds"},
    {"from": "build_workflow", "to": "admin_ui", "label": "builds"},
    {"from": "ci_cd", "to": "backend", "label": "deploys"},
    {"from": "ci_cd", "to": "admin_ui", "label": "deploys"},
    # Feature/API Relationships
    {"from": "admin_endpoints", "to": "rate_limiting", "label": "implement"},
    {"from": "admin_endpoints", "to": "metrics_dashboard", "label": "implement"},
    {"from": "admin_endpoints", "to": "user_management", "label": "implement"},
    {"from": "admin_endpoints", "to": "audit_log", "label": "implement"},
    {"from": "admin_endpoints", "to": "websocket_support", "label": "support"},
    # Cross-Cutting Concerns
    {"from": "backend", "to": "security", "label": "enforces"},
    {"from": "backend", "to": "observability", "label": "provides"},
    {"from": "backend", "to": "error_handling", "label": "handles"},
    {"from": "backend", "to": "performance", "label": "optimizes"},
    {"from": "admin_ui", "to": "security", "label": "enforces"},
    {"from": "admin_ui", "to": "error_handling", "label": "handles"},
    # Documentation
    {"from": "docs", "to": "backend", "label": "documents"},
    {"from": "docs", "to": "admin_ui", "label": "documents"},
    {"from": "docs", "to": "admin_endpoints", "label": "documents"},
    {"from": "docs", "to": "test_workflow", "label": "documents"},
    {"from": "docs", "to": "dev_workflow", "label": "documents"},
    # Auth Relationships
    {"from": "auth_flow", "to": "admin_endpoints", "label": "protects"},
    {"from": "auth_flow", "to": "admin_ui", "label": "protects"},
    # Testing Relationships
    {"from": "test_workflow", "to": "backend", "label": "tests"},
    {"from": "test_workflow", "to": "admin_endpoints", "label": "tests"},
    {"from": "test_workflow", "to": "admin_ui", "label": "tests"},
    {"from": "test_workflow", "to": "websocket_support", "label": "tests"},
    # Feature-to-Concern
    {"from": "rate_limiting", "to": "security", "label": "improves"},
    {"from": "metrics_dashboard", "to": "observability", "label": "improves"},
    {"from": "audit_log", "to": "security", "label": "improves"},
    {"from": "audit_log", "to": "observability", "label": "improves"},
]

MERMAID_OUTPUT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../docs/cursor_knowledge_graph.md'))
JSON_OUTPUT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../docs/cursor_knowledge_graph.json'))

def export_mermaid():
    os.makedirs(os.path.dirname(MERMAID_OUTPUT_PATH), exist_ok=True)
    with open(MERMAID_OUTPUT_PATH, 'w') as f:
        f.write(MERMAID_MD)
    print(f"Mermaid knowledge graph exported to {MERMAID_OUTPUT_PATH}")

def export_json():
    os.makedirs(os.path.dirname(JSON_OUTPUT_PATH), exist_ok=True)
    graph = {"nodes": NODES, "edges": EDGES}
    with open(JSON_OUTPUT_PATH, 'w') as f:
        json.dump(graph, f, indent=2)
    print(f"JSON knowledge graph exported to {JSON_OUTPUT_PATH}")

def main():
    formats = set()
    if len(sys.argv) == 1:
        formats = {"mermaid", "json"}
    else:
        for arg in sys.argv[1:]:
            if arg.lower() in {"mermaid", "json"}:
                formats.add(arg.lower())
    if not formats:
        print("Usage: python export_knowledge_graph.py [mermaid] [json]")
        return
    if "mermaid" in formats:
        export_mermaid()
    if "json" in formats:
        export_json()

if __name__ == "__main__":
    main() 