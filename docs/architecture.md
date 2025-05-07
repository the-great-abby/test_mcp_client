# System Architecture Diagram

This diagram shows the high-level architecture of the MCP Chat Client project, including user interfaces, backend services, data stores, AI providers, and automation components.

```mermaid
flowchart TD
    subgraph User["User Environment"]
        A["Admin UI (SvelteKit/TypeScript)"]
        B["Developer CLI / API Client"]
    end

    subgraph Backend["Backend & Services"]
        C["FastAPI Backend"]
        D["PostgreSQL DB"]
        E["Redis"]
        F["Prometheus / Grafana"]
        G["OpenAI / Anthropic / LLM Provider"]
        H["Admin API Endpoints"]
    end

    subgraph Automation["Automation & CI"]
        I["Makefile / Makefile.ai"]
        J["Task Master / Docs Generator"]
    end

    %% User interactions
    A -- "REST & WebSocket" --> C
    B -- "REST & WebSocket" --> C

    %% Backend connections
    C -- "SQLAlchemy" --> D
    C -- "Redis Client" --> E
    C -- "Prometheus Exporter" --> F
    C -- "AI Provider API" --> G
    C -- "Admin Endpoints" --> H
    H -- "JWT Auth" --> C

    %% Automation
    I --> C
    I --> A
    J --> C
    J --> A
``` 