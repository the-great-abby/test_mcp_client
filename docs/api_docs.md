# API Documentation

This document provides an overview of the MCP Chat Client backend API, including how to access interactive docs, example requests, and authentication details.

---

## 📖 Interactive API Docs

- **Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Redoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)

These endpoints are available when running the backend locally. They provide a live, interactive view of all available API endpoints, request/response schemas, and example payloads.

---

## 🔐 Authentication

Most admin endpoints require JWT authentication.

- Obtain a JWT by logging in via the `/auth/login` endpoint.
- Include the token in the `Authorization: Bearer <token>` header for protected requests.

### Example: Get a JWT Token
```bash
curl -X POST http://localhost:8000/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email": "admin@example.com", "password": "yourpassword"}'
```

### Example: Call a Protected Admin Endpoint
```bash
curl -X GET http://localhost:8000/admin/some-endpoint \
  -H 'Authorization: Bearer <your-jwt-token>'
```

---

## 📝 Endpoint Reference

- See the [Swagger UI](http://localhost:8000/docs) or [Redoc](http://localhost:8000/redoc) for a full, auto-generated list of endpoints, parameters, and schemas.
- You can also generate static API docs using tools like `redoc-cli` or `openapi-generator` if needed.

---

## 🚧 Contributing to API Docs

- If you add or change endpoints, please update this file and ensure the OpenAPI schema is up to date.
- Suggestions for examples, usage tips, or troubleshooting are welcome! 