# Data Flow Diagrams

This document provides sequence diagrams for key workflows in the MCP Chat Client system.

---

## 1. User Message Flow (Chat)

This diagram shows the flow of a user message from the client through authentication, rate limiting, persistence, and AI/LLM processing.

```mermaid
sequenceDiagram
    participant U as "User (Admin UI / API Client)"
    participant BE as "FastAPI Backend"
    participant Auth as "JWT Auth"
    participant RL as "Rate Limiter (Redis)"
    participant DB as "PostgreSQL"
    participant AI as "LLM Provider (OpenAI/Anthropic)"
    participant Redis as "Redis (Cache/State)"
    participant Metrics as "Prometheus"

    U->>BE: Send message (REST or WebSocket)
    BE->>Auth: Validate JWT
    Auth-->>BE: Auth result (success/fail)
    BE->>RL: Check rate limits (Redis)
    RL-->>BE: Allow/Block
    alt Allowed
        BE->>DB: Store message
        BE->>Redis: Update state/session
        BE->>AI: Forward message to LLM provider
        AI-->>BE: LLM response
        BE->>DB: Store AI response
        BE->>Redis: Update state/session
        BE->>Metrics: Increment counters (Prometheus)
        BE-->>U: Return response (streamed or full)
    else Blocked
        BE->>Metrics: Increment rate limit violation
        BE-->>U: Return rate limit error
    end
```

---

## 2. Authentication Flow (Login & JWT)

This diagram shows the process of user login, JWT issuance, and validation for protected endpoints.

```mermaid
sequenceDiagram
    participant U as "User (Admin UI / API Client)"
    participant BE as "FastAPI Backend"
    participant DB as "PostgreSQL"
    participant JWT as "JWT Issuer/Validator"

    U->>BE: Submit login credentials
    BE->>DB: Verify user credentials
    DB-->>BE: User record (valid/invalid)
    alt Valid
        BE->>JWT: Issue JWT token
        JWT-->>BE: JWT token
        BE-->>U: Return JWT token
    else Invalid
        BE-->>U: Return auth error
    end

    Note over U,BE: For subsequent requests...
    U->>BE: Make request with JWT token
    BE->>JWT: Validate JWT
    JWT-->>BE: Auth result
    BE-->>U: Return protected resource or error
```

---

## 3. Admin Action Flow (Admin Endpoint, Audit Log)

This diagram shows an admin performing a privileged action, with authentication, effect, and audit logging.

```mermaid
sequenceDiagram
    participant Admin as "Admin User (UI/API)"
    participant BE as "FastAPI Backend"
    participant Auth as "JWT Auth (Admin)"
    participant DB as "PostgreSQL"
    participant Redis as "Redis"
    participant Audit as "Audit Log (Redis/DB)"

    Admin->>BE: Call admin endpoint (e.g., reset rate limits)
    BE->>Auth: Validate admin JWT
    Auth-->>BE: Auth result
    alt Authorized
        BE->>Redis: Perform admin action (e.g., reset keys)
        BE->>Audit: Record action in audit log
        BE-->>Admin: Return success
    else Unauthorized
        BE-->>Admin: Return error
    end
``` 