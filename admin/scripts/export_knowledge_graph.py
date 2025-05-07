import os

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

OUTPUT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../docs/cursor_knowledge_graph.md'))

def main():
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, 'w') as f:
        f.write(MERMAID_MD)
    print(f"Knowledge graph exported to {OUTPUT_PATH}")

if __name__ == "__main__":
    main() 