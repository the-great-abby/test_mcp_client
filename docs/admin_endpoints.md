# Admin API Endpoints Guide

This guide documents all admin-only API endpoints for the MCP Chat Backend. All endpoints require an **admin JWT token** in the `Authorization: Bearer <token>` header.

## Usage Tips
- Use a tool like `curl`, `httpie`, or Postman to interact with these endpoints.
- All endpoints are under the `/api/v1/admin/` prefix.
- You must authenticate as an admin user to access these endpoints.
- Example curl usage:
  ```bash
  curl -H "Authorization: Bearer <your_admin_token>" http://localhost:8000/api/v1/admin/metrics
  ```

---

## GET `/api/v1/admin/rate-limits`
- **Description:** Get current rate limit configuration and status.
- **Permissions:** Admin only
- **Request:** None
- **Response:**
  ```json
  { "message": "Only admins can see this. Current rate limit config and status (stub)" }
  ```

---

## GET `/api/v1/admin/metrics`
- **Description:** Get a snapshot of key metrics for admin UI.
- **Permissions:** Admin only
- **Request:** None
- **Response:**
  ```json
  { "user_count": 42, "message_count": 1234 }
  ```

---

## GET `/api/v1/admin/rate-limit-violations`
- **Description:** List recent rate limit violations (WebSocket).
- **Permissions:** Admin only
- **Request:** None
- **Response:**
  ```json
  { "violations": [ { "identifier": "user123", "count": 3, "ttl": 57 } ] }
  ```

---

## POST `/api/v1/admin/rate-limits/reset`
- **Description:** Reset rate limit counters for a user or globally.
- **Permissions:** Admin only
- **Request:**
  - Optional query param: `user_id=<user_id>`
- **Response:**
  ```json
  { "message": "Rate limits reset for user user123" }
  ```

---

## GET `/api/v1/admin/users`
- **Description:** List all users.
- **Permissions:** Admin only
- **Request:** None
- **Response:**
  ```json
  { "users": [ { "id": "...", "username": "...", "email": "...", "is_active": true, "is_admin": false } ] }
  ```

---

## POST `/api/v1/admin/users/{user_id}/promote`
- **Description:** Promote a user to admin.
- **Permissions:** Admin only
- **Request:** None
- **Response:**
  ```json
  { "message": "User {user_id} promoted to admin" }
  ```

---

## POST `/api/v1/admin/users/{user_id}/deactivate`
- **Description:** Deactivate a user account.
- **Permissions:** Admin only
- **Request:** None
- **Response:**
  ```json
  { "message": "User {user_id} deactivated" }
  ```

---

## GET `/api/v1/admin/system-status`
- **Description:** Get system resource usage (CPU, memory, disk).
- **Permissions:** Admin only
- **Request:** None
- **Response:**
  ```json
  { "cpu": 12.3, "memory": 45.6, "disk": 78.9 }
  ```

---

## GET `/api/v1/admin/service-status`
- **Description:** Get status of dependent services (DB, Redis).
- **Permissions:** Admin only
- **Request:** None
- **Response:**
  ```json
  { "db": "ok", "redis": "ok" }
  ```

---

## GET `/api/v1/admin/audit-log`
- **Description:** Get recent admin actions and security events.
- **Permissions:** Admin only
- **Request:** None
- **Response:**
  ```json
  { "audit_log": [ { "timestamp": "...", "admin_id": "...", "action": "...", ... } ] }
  ``` 